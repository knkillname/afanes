"""Page navigation, link routing, and the bounded history stack."""

import asyncio
import dataclasses
import logging
from pathlib import Path

import afanes.core.links
import afanes.core.names
import afanes.core.vault.pages
import afanes.ui.state.browser
import afanes.ui.strings
from afanes.core.errors import AfanesError, InvalidReferenceError, VaultError
from afanes.core.links import DestinationKind, ReferenceParser
from afanes.core.vault.snapshot import LinkOutcome
from afanes.models.link import NoteReference
from afanes.models.note import CategoryLabel, NoteType
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.pages import PageEditorState
from afanes.ui.state.session import VaultSession
from afanes.ui.state.status import UiStatus

logger = logging.getLogger(__name__)

PAGE_HISTORY_LIMIT = 50


@dataclasses.dataclass(slots=True)
class PageNavigator:
    """Open-page movement, link routing, and the bounded history stack.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the scan snapshot.
    pages : PageEditorState
        Editor that owns the open draft.
    browser : afanes.ui.state.browser.BrowserState
        Browser query cleared after a creation.
    status : UiStatus
        Shared banner and busy flags.
    command_lock : CommandLock
        Shared command lock.
    history : tuple[Path, ...]
        Page paths behind the current page, oldest first.
    ambiguous : tuple[Path, ...]
        Candidate paths waiting for the user to choose one.
    """

    session: VaultSession
    pages: PageEditorState
    browser: afanes.ui.state.browser.BrowserState
    status: UiStatus
    command_lock: CommandLock
    history: tuple[Path, ...] = ()
    ambiguous: tuple[Path, ...] = ()

    def reset(self) -> None:
        """Clear the history and the candidate picker."""
        self.history = ()
        self.ambiguous = ()

    async def open_page(self, path: Path) -> bool:
        """Open a note in the page pane and push the previous page.

        Parameters
        ----------
        path : Path
            Note path, relative or absolute, inside the active vault.

        Returns
        -------
        bool
            ``True`` when the page was read and shown.

        Notes
        -----
        The current draft is committed first. An untouched new draft is
        discarded. A dirty draft is written before the page changes. Blocking
        file I/O runs in a worker thread.
        """
        async with self.command_lock:
            if self.session.vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                if not await self.pages.commit():
                    return False
                previous = self.pages.page.path if self.pages.page is not None else None
                if not await self.pages.load(path):
                    return False
                self.ambiguous = ()
                self._push_history(previous)
                return True
            finally:
                self.status.set_busy(busy=False)

    async def create_reference(
        self,
        name: str,
        category: CategoryLabel,
        scaffold: str | None,
    ) -> bool:
        """Create a reference from the browser and open it for editing.

        Parameters
        ----------
        name : str
            Display name typed by the user. It is sanitized into the identity
            filename without an added suffix.
        category : CategoryLabel
            Reference category, or ``general`` for Empty.
        scaffold : str | None
            Starter body from the chosen card, or ``None`` for Empty.

        Returns
        -------
        bool
            ``True`` when the note was written and opened in edit mode.

        Notes
        -----
        The current draft is committed first, using the same guard as opening a
        page. A blank name or a collision writes nothing. The note is written
        atomically, the scan is refreshed, the browser query is cleared, and the
        new page opens in edit mode. If the scan fails after the write, the note
        remains and the banner reports the refresh failure. Blocking I/O runs in
        a worker thread.
        """
        display_name = name.strip()
        if not display_name:
            self.status.show_message(afanes.ui.strings.BROWSER_NAME_REQUIRED)
            return False
        async with self.command_lock:
            vault = self.session.vault
            if vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                if not await self.pages.commit():
                    return False
                previous = self.pages.page.path if self.pages.page is not None else None
                body = self._reference_body(display_name, scaffold)
                try:
                    path = await asyncio.to_thread(
                        afanes.core.vault.pages.VaultPages(vault).create_page,
                        display_name,
                        NoteType.REFERENCE,
                        category,
                        body=body,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Browser reference could not be created", exc_info=True)
                    self.status.show_message(afanes.ui.strings.BROWSER_CREATE_FAILED.format(detail=str(exc)))
                    return False
                refresh_error: str | None = None
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Snapshot refresh after creating a reference failed", exc_info=True)
                    refresh_error = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
                else:
                    self.session.apply_snapshot(snapshot, focus=path)
                self.browser.query = ""
                if not await self.pages.load(path, editing=True):
                    return False
                self.ambiguous = ()
                self._push_history(previous)
                if refresh_error is not None:
                    self.status.show_message(refresh_error)
                return True
            finally:
                self.status.set_busy(busy=False)

    @staticmethod
    def _reference_body(name: str, scaffold: str | None) -> str:
        """Build the body for a browser-created reference."""
        body = f"# {name}\n"
        starter = (scaffold or "").strip("\r\n")
        if starter:
            return f"{body}\n{starter}\n"
        return body

    async def back(self) -> bool:
        """Return to the previous page in the shared history.

        Returns
        -------
        bool
            ``True`` when the history was consumed; the pane is empty at the
            oldest entry.

        Notes
        -----
        The current draft is committed or discarded before moving. History
        entries whose files disappeared are skipped.
        """
        async with self.command_lock:
            self.status.set_busy(busy=True)
            try:
                if not await self.pages.commit():
                    return False
                while self.history:
                    path = self.history[-1]
                    self.history = self.history[:-1]
                    if await self.pages.load(path):
                        self.ambiguous = ()
                        return True
                self.pages.clear()
                self.ambiguous = ()
                return True
            finally:
                self.status.set_busy(busy=False)

    async def follow_link(self, destination: str) -> None:
        """Route one link destination from the rendered page.

        Parameters
        ----------
        destination : str
            Destination exactly as written in the Markdown link.

        Notes
        -----
        External, attachment, anchor, and unsafe destinations are inert.
        Resolved references open their page, ambiguous references expose the
        candidates, and missing references start a draft.
        """
        kind = DestinationKind.classify(destination)
        if kind is not DestinationKind.INTERNAL:
            return
        try:
            reference = ReferenceParser().parse(destination)
        except InvalidReferenceError as exc:
            self.status.show_message(str(exc))
            return
        snapshot = self.session.snapshot
        if snapshot is None:
            await self._open_new_draft(reference)
            return
        target = snapshot.link_target(reference)
        if target.outcome is LinkOutcome.RESOLVED:
            await self.open_page(target.paths[0])
            return
        if target.outcome is LinkOutcome.AMBIGUOUS:
            async with self.command_lock:
                self.ambiguous = target.paths
                self.status.clear_message()
            return
        if target.outcome is LinkOutcome.BROKEN:
            if len(target.paths) == 1:
                await self.open_page(target.paths[0])
                return
            async with self.command_lock:
                self.ambiguous = target.paths
                self.status.clear_message()
            return
        safe_page = self._existing_safe_page(reference)
        if safe_page is not None:
            await self.open_page(safe_page)
            await self.pages.offer_repair(reference)
            return
        await self._open_new_draft(reference)

    async def choose_candidate(self, path: Path) -> bool:
        """Open one of the candidates offered for an ambiguous reference.

        Parameters
        ----------
        path : Path
            Candidate chosen by the user.

        Returns
        -------
        bool
            ``True`` when the candidate was opened.
        """
        async with self.command_lock:
            self.ambiguous = ()
        return await self.open_page(path)

    async def clear_ambiguous(self) -> None:
        """Close the candidate picker without opening a page."""
        async with self.command_lock:
            self.ambiguous = ()

    async def open_failure(self, path: Path) -> bool:
        """Open an unreadable note in raw rescue mode.

        Parameters
        ----------
        path : Path
            Vault-relative or absolute path reported by the scan.

        Returns
        -------
        bool
            ``True`` when the file was read.
        """
        return await self.open_page(path)

    async def _open_new_draft(self, reference: NoteReference) -> bool:
        """Open an unwritten page for a missing reference."""
        async with self.command_lock:
            if self.session.vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                if not await self.pages.commit():
                    return False
                previous = self.pages.page.path if self.pages.page is not None else None
                self.pages.start_new(reference)
                self.ambiguous = ()
                self._push_history(previous)
                self.status.clear_message()
                return True
            finally:
                self.status.set_busy(busy=False)

    def _existing_safe_page(self, reference: NoteReference) -> Path | None:
        """Return the parsed page whose safe identity matches an unsafe reference."""
        safe_name = afanes.core.names.safe_filename(reference.name)
        if afanes.core.names.normalize_name(safe_name) == afanes.core.names.normalize_name(reference.name):
            return None
        snapshot = self.session.snapshot
        if snapshot is None:
            return None
        candidates = snapshot.catalog.candidates(reference.scheme, safe_name)
        return candidates[0] if len(candidates) == 1 else None

    def _push_history(self, path: Path | None) -> None:
        """Push one page path onto the bounded history."""
        if path is None:
            return
        self.history = (*self.history, path)[-PAGE_HISTORY_LIMIT:]
