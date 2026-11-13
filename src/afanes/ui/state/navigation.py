"""Page navigation, link routing, and the bounded history stack."""

import asyncio
import dataclasses
import logging
from enum import StrEnum
from pathlib import Path

import afanes.core.links
import afanes.core.names
import afanes.core.vault.pages
import afanes.ui.state.browser
import afanes.ui.strings
from afanes.core.errors import AfanesError, InvalidReferenceError, VaultError
from afanes.core.links import DestinationKind, ReferenceParser
from afanes.core.vault.snapshot import LinkOutcome, VaultSnapshot
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.pages import PageEditorState
from afanes.ui.state.session import VaultSession
from afanes.ui.state.status import UiStatus

logger = logging.getLogger(__name__)

PAGE_HISTORY_LIMIT = 50


class RoleFollowOutcome(StrEnum):
    """Result of following one project role name.

    Attributes
    ----------
    OPENED : str
        Exactly one note matched and it is now open.
    AMBIGUOUS : str
        More than one note matched; the candidates wait for a choice.
    MISSING : str
        No note matched; the caller may create one.
    """

    OPENED = "opened"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"


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

    async def create_role_reference(self, name: str, category: CategoryLabel | None) -> bool:
        """Create a reference for a missing role name and open it for editing.

        Parameters
        ----------
        name : str
            Written owner, requester, or step owner name. It becomes the note
            identity and its level-1 heading.
        category : CategoryLabel | None
            Chosen reference category, or ``None`` for an uncategorized
            reference.

        Returns
        -------
        bool
            ``True`` when the note was written and opened in edit mode.

        Notes
        -----
        The current draft is committed first. The note is written atomically,
        the scan is refreshed, and the new page opens in edit mode. A blank
        name or a collision writes nothing and reports the failure. If the scan
        fails after the write, the note remains and the banner reports the
        refresh failure. Blocking I/O runs in a worker thread.
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
                body = self._reference_body(display_name, await self._role_scaffold(category))
                try:
                    path = await asyncio.to_thread(
                        afanes.core.vault.pages.VaultPages(vault).create_page,
                        display_name,
                        NoteType.REFERENCE,
                        category,
                        body=body,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Role reference could not be created", exc_info=True)
                    self.status.show_message(afanes.ui.strings.BROWSER_CREATE_FAILED.format(detail=str(exc)))
                    return False
                refresh_error: str | None = None
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Snapshot refresh after creating a role reference failed", exc_info=True)
                    refresh_error = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
                else:
                    self.session.apply_snapshot(snapshot, focus=path)
                if not await self.pages.load(path, editing=True):
                    return False
                self.ambiguous = ()
                self._push_history(previous)
                if refresh_error is not None:
                    self.status.show_message(refresh_error)
                return True
            finally:
                self.status.set_busy(busy=False)

    async def open_or_create_log_entry(
        self,
        date: NoteDate,
        title: str,
        scaffold: str | None = None,
    ) -> bool:
        """Open an existing log entry or create one for a date.

        Parameters
        ----------
        date : NoteDate
            Entry date. Its precision selects the filename and folder.
        title : str
            Display title for a new entry. It is ignored when the date already
            has an entry.
        scaffold : str | None
            Starter body from a log card, or ``None`` for an empty entry.

        Returns
        -------
        bool
            ``True`` when an entry was opened in edit mode.

        Notes
        -----
        The current draft is committed first. An occupied date opens the
        existing entry without writing. A new entry is written atomically, the
        scan is refreshed, the browser query is cleared, and the page opens in
        edit mode. If the scan fails after the write, the entry remains and the
        banner reports the refresh failure. Blocking I/O runs in a worker
        thread.
        """
        async with self.command_lock:
            vault = self.session.vault
            if vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                if not await self.pages.commit():
                    return False
                snapshot = self.session.snapshot
                existing = snapshot.log_entry(date) if snapshot is not None else None
                if existing is not None:
                    self.browser.log_selected = existing.path
                    self.ambiguous = ()
                    return await self.pages.load(existing.path, editing=True)
                previous = self.pages.page.path if self.pages.page is not None else None
                try:
                    path = await asyncio.to_thread(
                        afanes.core.vault.pages.VaultPages(vault).create_log_entry,
                        date,
                        title,
                        scaffold,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Log entry could not be created", exc_info=True)
                    self.status.show_message(afanes.ui.strings.LOG_CREATE_FAILED.format(detail=str(exc)))
                    return False
                refresh_error: str | None = None
                try:
                    refreshed = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Snapshot refresh after creating a log entry failed", exc_info=True)
                    refresh_error = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
                else:
                    self.session.apply_snapshot(refreshed, focus=path)
                self.browser.query = ""
                self.browser.log_selected = path
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

    async def _role_scaffold(self, category: CategoryLabel | None) -> str | None:
        """Return the starter body of the template card for one category.

        Parameters
        ----------
        category : CategoryLabel | None
            Chosen role-reference category, or ``None`` when the user chose no
            category.

        Returns
        -------
        str | None
            The first valid reference card body for the category, or ``None``
            when the category has no card or no category was chosen.

        Notes
        -----
        Multiple cards may share a category. The first card in title order is
        used, matching the order shown by the reference picker. Reading the
        cards runs blocking I/O in a worker thread and never writes.
        """
        if category is None:
            return None
        listing = await self.session.template_cards()
        if listing is None:
            return None
        for card in listing.for_type(NoteType.REFERENCE):
            if card.category == category and card.body.strip():
                return card.body
        return None

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
        await self._follow_reference(reference, snapshot)

    async def _follow_reference(self, reference: NoteReference, snapshot: VaultSnapshot) -> None:
        """Route one parsed reference against the current snapshot."""
        target = snapshot.link_target(reference)
        if target.outcome is LinkOutcome.RESOLVED:
            await self.open_page(target.paths[0])
            return
        if target.outcome is LinkOutcome.AMBIGUOUS or (target.outcome is LinkOutcome.BROKEN and len(target.paths) > 1):
            async with self.command_lock:
                self.ambiguous = target.paths
                self.status.clear_message()
            return
        if target.outcome is LinkOutcome.BROKEN:
            await self.open_page(target.paths[0])
            return
        safe_page = self._existing_safe_page(reference)
        if safe_page is not None:
            await self.open_page(safe_page)
            await self.pages.offer_repair(reference)
            return
        await self._open_new_draft(reference)

    async def follow_role(self, name: str) -> RoleFollowOutcome:
        """Route one project role name from read mode.

        Parameters
        ----------
        name : str
            Written owner or requester name, or one step owner name.

        Returns
        -------
        RoleFollowOutcome
            ``OPENED`` when exactly one note matched, ``AMBIGUOUS`` when the
            candidate picker is showing, or ``MISSING`` when no note matched.

        Notes
        -----
        Role names resolve in the ``note:`` namespace. A resolved name opens
        its page through the normal page command. An ambiguous name exposes the
        existing candidate list and chooses nothing. A missing name writes
        nothing; the caller starts the category dialog.
        """
        reference = NoteReference(scheme=ReferenceScheme.NOTE, name=name)
        snapshot = self.session.snapshot
        if snapshot is None:
            return RoleFollowOutcome.MISSING
        target = snapshot.link_target(reference)
        if target.outcome is LinkOutcome.RESOLVED:
            await self.open_page(target.paths[0])
            return RoleFollowOutcome.OPENED
        if target.outcome is LinkOutcome.AMBIGUOUS:
            async with self.command_lock:
                self.ambiguous = target.paths
                self.status.clear_message()
            return RoleFollowOutcome.AMBIGUOUS
        if target.outcome is LinkOutcome.BROKEN and len(target.paths) == 1:
            await self.open_page(target.paths[0])
            return RoleFollowOutcome.OPENED
        return RoleFollowOutcome.MISSING

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
        safe_name = afanes.core.names.NamePolicy.safe_filename(reference.name)
        if afanes.core.names.NamePolicy.normalize(safe_name) == afanes.core.names.NamePolicy.normalize(reference.name):
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
