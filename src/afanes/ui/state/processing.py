"""Processing Wizard session state."""

import asyncio
import dataclasses
import datetime
import logging
from pathlib import Path

import afanes.core.processing
import afanes.core.vault.processing
import afanes.ui.strings
from afanes.core.errors import AfanesError, VaultError
from afanes.core.processing import AppendStepPlan, ProcessingOutcome, ProcessingPlan
from afanes.models.note import Status
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
    """

    session: VaultSession
    status: UiStatus
    command_lock: CommandLock
    note: Path | None = None
    body: str | None = None
    plan: ProcessingPlan | AppendStepPlan | None = None
    result: Path | None = None

    def reset(self) -> None:
        """Clear the wizard session."""
        self.note = None
        self.body = None
        self.plan = None
        self.result = None

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
                self.status.show_message(afanes.ui.strings.PROCESSING_MISSING)
                return False
            self.status.set_busy(busy=True)
            self.status.clear_message()
            try:
                try:
                    body = await asyncio.to_thread(vault.read_body, path)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Capture could not be read for processing", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PROCESSING_READ_FAILED.format(detail=str(exc)))
                    return False
                self.note = path
                self.body = body
                self.plan = None
                self.result = None
                self.session.selected = path
                self.session.preview_body = body
                return True
            finally:
                self.status.set_busy(busy=False)

    async def build_plan(
        self,
        outcome: ProcessingOutcome,
        *,
        status: Status | None = None,
        due_date: datetime.date | None = None,
        project: str | None = None,
    ) -> ProcessingPlan | AppendStepPlan | None:
        """Build a processing preview for the open capture.

        Parameters
        ----------
        outcome : ProcessingOutcome
            Selected clarification outcome.
        status : Status | None
            Requested target status, when the outcome accepts one.
        due_date : datetime.date | None
            Optional calendar due date for a new project.
        project : str | None
            Target project identity for Append step.

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
            self.status.set_busy(busy=True)
            self.status.clear_message()
            try:
                try:
                    plan = await asyncio.to_thread(
                        afanes.core.vault.processing.VaultProcessing(vault).plan_processing,
                        note,
                        outcome,
                        status=status,
                        due_date=due_date,
                        project=project,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Processing plan failed", exc_info=True)
                    self.plan = None
                    self.status.show_message(afanes.ui.strings.PROCESSING_PLAN_FAILED.format(detail=str(exc)))
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
            self.status.clear_message()
            try:
                try:
                    target = await asyncio.to_thread(
                        afanes.core.vault.processing.VaultProcessing(vault).apply_processing, plan, confirm=True
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Processing apply failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PROCESSING_FAILED.format(detail=str(exc)))
                    return None
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Inbox refresh after processing failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PROCESSING_REFRESH_FAILED.format(detail=str(exc)))
                else:
                    self.session.apply_snapshot(snapshot)
                self.clear()
                self.session.selected = None
                self.session.preview_body = None
                self.result = target
                return target
            finally:
                self.status.set_busy(busy=False)

    def cancel(self) -> None:
        """Close the wizard and discard its unsaved plan."""
        self.clear()
        self.status.clear_message()

    def finish(self) -> None:
        """Close the success state and return to the Inbox."""
        self.clear()
        self.status.clear_message()

    def clear(self) -> None:
        """Clear the Processing Wizard session fields."""
        self.note = None
        self.body = None
        self.plan = None
        self.result = None
