"""Page navigation, link routing, and the bounded history stack."""

import dataclasses
import logging
from pathlib import Path

import afanes.core.links
import afanes.core.names
import afanes.ui.strings
from afanes.core.errors import InvalidReferenceError
from afanes.core.links import DestinationKind, ReferenceParser
from afanes.core.vault.snapshot import LinkOutcome
from afanes.models.link import NoteReference
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
