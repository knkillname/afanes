"""Processing Wizard session state."""

import asyncio
import dataclasses
import logging
from pathlib import Path

import afanes.core.processing
import afanes.core.vault.processing
import afanes.core.vault.service
import afanes.ui.strings
from afanes.core.errors import AfanesError, VaultError
from afanes.core.processing import AppendStepPlan, ProcessingPlan
from afanes.core.template_cards import TemplateCard, TemplateCardCatalog, TemplateCardIssue, TemplateCardListing
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.session import VaultSession
from afanes.ui.state.status import UiStatus

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class ProcessingState:
    """Processing Wizard session for one capture.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the active vault and snapshot.
    status : UiStatus
        Shared banner and busy flags.
    command_lock : CommandLock
        Shared command lock.
    note : Path | None
        Capture currently open in the wizard.
    body : str | None
        Markdown body of the processing capture.
    plan : ProcessingPlan | AppendStepPlan | None
        Validated plan waiting for confirmation.
    result : Path | None
        Destination of the last successful processing apply.
    cards : tuple[TemplateCard, ...]
        Valid template cards read when the wizard opened, ordered by title.
    card_issues : tuple[TemplateCardIssue, ...]
        Template card files that could not be read or validated.
    banner : str | None
        Persistent post-apply refresh failure shown after the wizard closes,
        or ``None`` when the last apply refreshed the scan.
    """

    session: VaultSession
    status: UiStatus
    command_lock: CommandLock
    note: Path | None = None
    body: str | None = None
    plan: ProcessingPlan | AppendStepPlan | None = None
    result: Path | None = None
    cards: tuple[TemplateCard, ...] = ()
    card_issues: tuple[TemplateCardIssue, ...] = ()
    banner: str | None = None

    def reset(self) -> None:
        """Clear the wizard session."""
        self.note = None
        self.body = None
        self.plan = None
        self.result = None
        self.cards = ()
        self.card_issues = ()
        self.banner = None

    async def begin(self, path: Path) -> bool:
        """Open the Processing Wizard for an Inbox capture.

        Parameters
        ----------
        path : Path
            Absolute path of a note currently listed in the Inbox.

        Returns
        -------
        bool
            ``True`` when the capture body was read and the wizard can open.

        Notes
        -----
        A capture that disappeared or cannot be read leaves the controller in
        the Inbox with an actionable message. Blocking file I/O runs in a
        worker thread.
        """
        async with self.command_lock:
            vault = self.session.vault
            if vault is None:
                return False
            if all(note.path != path for note in self.session.notes):
                self.status.show_notice(afanes.ui.strings.PROCESSING_MISSING)
                return False
            self.banner = None
            self.status.set_busy(busy=True)
            try:
                try:
                    await self.load(path)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Capture could not be read for processing", exc_info=True)
                    self.status.show_notice(afanes.ui.strings.PROCESSING_READ_FAILED.format(detail=str(exc)))
                    return False
                return True
            finally:
                self.status.set_busy(busy=False)

    async def load(self, path: Path) -> None:
        """Load a capture and its template cards into the wizard.

        Parameters
        ----------
        path : Path
            Absolute path of the capture to read.

        Raises
        ------
        VaultError
            When no vault is open.
        AfanesError, OSError, UnicodeError
            Propagated from reading the capture body or template cards.

        Notes
        -----
        Callers own the command lock, busy flag, and user-facing error
        messages. Blocking reads run in worker threads. The wizard fields are
        updated only after both reads succeed.
        """
        vault = self.session.vault
        if vault is None:
            raise VaultError(afanes.ui.strings.VAULT_MISSING)
        body = await asyncio.to_thread(vault.read_body, path)
        listing = await asyncio.to_thread(self._load_cards, vault)
        self.note = path
        self.body = body
        self.plan = None
        self.result = None
        self.cards = listing.cards
        self.card_issues = listing.issues
        self.session.selected = path
        self.session.preview_body = body

    async def build_plan(
        self,
        request: afanes.core.vault.processing.ProcessingRequest,
    ) -> ProcessingPlan | AppendStepPlan | None:
        """Build a processing preview for the open capture.

        Parameters
        ----------
        request : afanes.core.vault.processing.ProcessingRequest
            Selected outcome and optional metadata. The state fills
            ``note_path`` from the open capture.

        Returns
        -------
        ProcessingPlan | AppendStepPlan | None
            The validated plan, or ``None`` when planning failed.

        Notes
        -----
        Planning never writes. The plan is retained in
        :attr:`processing_plan` for the preview and confirmation step. Blocking
        file I/O runs in a worker thread.
        """
        async with self.command_lock:
            vault = self.session.vault
            note = self.note
            if vault is None or note is None:
                return None
            request = dataclasses.replace(request, note_path=note)
            self.status.set_busy(busy=True)
            try:
                try:
                    plan = await asyncio.to_thread(
                        afanes.core.vault.processing.VaultProcessing(vault).plan_processing,
                        request,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Processing plan failed", exc_info=True)
                    self.plan = None
                    self.status.show_notice(afanes.ui.strings.PROCESSING_PLAN_FAILED.format(detail=str(exc)))
                    return None
                self.plan = plan
                return plan
            finally:
                self.status.set_busy(busy=False)

    async def apply(self) -> Path | None:
        """Apply the current processing plan after confirmation.

        Returns
        -------
        Path | None
            Destination path on success, or ``None`` when the apply failed.

        Notes
        -----
        A successful apply refreshes the scan and leaves the wizard in a success
        state. The review caller records the item separately, so this state
        never depends on the review session. A failed apply keeps the plan so
        the user can retry. Blocking writes and scans run in a worker thread.
        """
        async with self.command_lock:
            vault = self.session.vault
            plan = self.plan
            if vault is None or plan is None:
                return None
            self.status.set_busy(busy=True)
            try:
                try:
                    target = await asyncio.to_thread(
                        afanes.core.vault.processing.VaultProcessing(vault).apply_processing, plan, confirm=True
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Processing apply failed", exc_info=True)
                    self.status.show_notice(afanes.ui.strings.PROCESSING_FAILED.format(detail=str(exc)))
                    return None
                refresh_failure: str | None = None
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Inbox refresh after processing failed", exc_info=True)
                    refresh_failure = afanes.ui.strings.PROCESSING_REFRESH_FAILED.format(detail=str(exc))
                else:
                    self.session.apply_snapshot(snapshot)
                self.clear()
                self.banner = refresh_failure
                self.session.selected = None
                self.session.preview_body = None
                self.result = target
                return target
            finally:
                self.status.set_busy(busy=False)

    def cancel(self) -> None:
        """Close the wizard and discard its unsaved plan."""
        self.clear()

    def finish(self) -> None:
        """Close the success state and return to the Inbox."""
        self.clear()

    def clear(self) -> None:
        """Clear the Processing Wizard session fields."""
        self.note = None
        self.body = None
        self.plan = None
        self.result = None
        self.cards = ()
        self.card_issues = ()
        self.banner = None

    @staticmethod
    def _load_cards(vault: afanes.core.vault.service.Vault) -> TemplateCardListing:
        """Read the vault template card catalog without blocking the UI.

        Parameters
        ----------
        vault : afanes.core.vault.service.Vault
            Active vault whose ``templates/`` folder should be read.

        Returns
        -------
        TemplateCardListing
            Valid cards plus an issue for each refused file. A missing folder
            yields an empty listing.
        """
        catalog = TemplateCardCatalog.from_root(vault.templates_directory())
        return catalog.load()
