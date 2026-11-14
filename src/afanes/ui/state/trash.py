"""Trash restore, overwrite, delete, and empty-trash dialog state."""

import asyncio
import dataclasses
import logging
from pathlib import Path

import afanes.core.vault.trash
import afanes.core.vault.trash_catalog
from afanes.core.errors import AfanesError, NameCollisionError
from afanes.core.vault.trash_catalog import TrashEntry
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.pages import PageEditorState
from afanes.ui.state.session import VaultSession
from afanes.ui.state.status import UiStatus

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class TrashDialogs:
    """Pending Trash decisions and the commands that apply them.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the active snapshot and trash catalog.
    pages : PageEditorState
        Editor that owns the read-only trashed page.
    status : UiStatus
        Shared banner and busy flags.
    command_lock : CommandLock
        Shared command lock.
    overwrite_entry : TrashEntry | None
        Entry whose restore found an occupied birthplace, waiting for the
        overwrite confirmation, or ``None`` when no overwrite is pending.
    delete_entry : TrashEntry | None
        Entry waiting for the permanent-delete confirmation, or ``None``.
    empty_open : bool
        Whether the Empty Trash confirmation is showing.
    """

    session: VaultSession
    pages: PageEditorState
    status: UiStatus
    command_lock: CommandLock
    overwrite_entry: TrashEntry | None = None
    delete_entry: TrashEntry | None = None
    empty_open: bool = False

    @property
    def overwrite_open(self) -> bool:
        """Return whether the overwrite confirmation is showing.

        Returns
        -------
        bool
            ``True`` when a restore found an occupied birthplace.
        """
        return self.overwrite_entry is not None

    @property
    def delete_open(self) -> bool:
        """Return whether the per-note delete confirmation is showing.

        Returns
        -------
        bool
            ``True`` when the open trashed note is waiting for deletion.
        """
        return self.delete_entry is not None

    def reset(self) -> None:
        """Clear every pending Trash decision."""
        self.overwrite_entry = None
        self.delete_entry = None
        self.empty_open = False

    async def restore(self) -> bool:
        """Restore the open trashed note to a free birthplace.

        Returns
        -------
        bool
            ``True`` when the note was restored and opened read-write. A
            collision opens the overwrite confirmation and writes nothing.

        Notes
        -----
        A free birthplace restores immediately. An occupied one is reported
        through :attr:`overwrite_entry`; the caller shows the confirmation and
        calls :meth:`confirm_overwrite` only after the user agrees.
        """
        entry = self.pages.trash_entry
        vault = self.session.vault
        if entry is None or vault is None:
            return False
        async with self.command_lock:
            self.status.set_busy(busy=True)
            try:
                try:
                    target = await asyncio.to_thread(
                        afanes.core.vault.trash.TrashService(vault).restore_entry,
                        entry,
                        confirm=True,
                    )
                except NameCollisionError:
                    self.overwrite_entry = entry
                    self.pages.blocking_message = self.status.copy.TRASH_CONFIRM_LEAVE
                    return False
                except (AfanesError, OSError) as exc:
                    logger.debug("Trash restore failed", exc_info=True)
                    self.status.show_notice(
                        self.status.copy.TRASH_RESTORE_FAILED.format(detail=self.status.copy.render_error(exc))
                    )
                    return False
                await self._finish_restore(target)
                return True
            finally:
                self.status.set_busy(busy=False)

    async def confirm_overwrite(self) -> bool:
        """Restore the waiting entry and permanently replace the occupant.

        Returns
        -------
        bool
            ``True`` when the note was restored and opened read-write.
        """
        entry = self.overwrite_entry
        vault = self.session.vault
        if entry is None or vault is None:
            return False
        async with self.command_lock:
            self.status.set_busy(busy=True)
            try:
                try:
                    target = await asyncio.to_thread(
                        afanes.core.vault.trash.TrashService(vault).restore_entry,
                        entry,
                        confirm=True,
                        overwrite=True,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Trash overwrite restore failed", exc_info=True)
                    self.status.show_notice(
                        self.status.copy.TRASH_RESTORE_FAILED.format(detail=self.status.copy.render_error(exc))
                    )
                    return False
                await self._finish_restore(target)
                return True
            finally:
                self.status.set_busy(busy=False)

    async def cancel_overwrite(self) -> None:
        """Dismiss the overwrite confirmation without writing anything."""
        async with self.command_lock:
            self.overwrite_entry = None
            self.pages.blocking_message = None

    async def begin_delete(self) -> bool:
        """Open the permanent-delete confirmation for the trashed page.

        Returns
        -------
        bool
            ``True`` when a trashed page is open and the confirmation is shown.
        """
        async with self.command_lock:
            entry = self.pages.trash_entry
            if entry is None:
                return False
            self.delete_entry = entry
            self.pages.blocking_message = self.status.copy.TRASH_CONFIRM_LEAVE
            return True

    async def cancel_delete(self) -> None:
        """Dismiss the permanent-delete confirmation without deleting."""
        async with self.command_lock:
            self.delete_entry = None
            self.pages.blocking_message = None

    async def confirm_delete(self) -> bool:
        """Permanently delete the entry waiting for confirmation.

        Returns
        -------
        bool
            ``True`` when the entry was deleted and the page was closed.
        """
        entry = self.delete_entry
        vault = self.session.vault
        if entry is None or vault is None:
            return False
        async with self.command_lock:
            self.status.set_busy(busy=True)
            try:
                try:
                    await asyncio.to_thread(
                        afanes.core.vault.trash.TrashService(vault).delete_entry,
                        entry,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Trash delete failed", exc_info=True)
                    self.status.show_notice(
                        self.status.copy.TRASH_DELETE_FAILED.format(detail=self.status.copy.render_error(exc))
                    )
                    return False
                self.delete_entry = None
                self.pages.blocking_message = None
                self.pages.clear()
                await self.session.refresh_trash()
                self.status.show_notice(self.status.copy.TRASH_DELETED)
                return True
            finally:
                self.status.set_busy(busy=False)

    async def begin_empty(self) -> bool:
        """Open the Empty Trash confirmation.

        Returns
        -------
        bool
            ``True`` when managed entries exist and the confirmation is shown.
        """
        async with self.command_lock:
            if self.session.trash_count == 0:
                return False
            self.empty_open = True
            return True

    async def cancel_empty(self) -> None:
        """Dismiss the Empty Trash confirmation without deleting."""
        async with self.command_lock:
            self.empty_open = False

    async def confirm_empty(self) -> bool:
        """Permanently delete every managed entry after confirmation.

        Returns
        -------
        bool
            ``True`` when every managed entry was removed.
        """
        vault = self.session.vault
        if vault is None:
            return False
        async with self.command_lock:
            self.status.set_busy(busy=True)
            try:
                try:
                    report = await asyncio.to_thread(
                        afanes.core.vault.trash.TrashService(vault).empty,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Empty Trash failed", exc_info=True)
                    self.session.trash_banner = self.status.copy.TRASH_MAINTENANCE_FAILED
                    self.status.show_notice(
                        self.status.copy.TRASH_EMPTY_FAILED.format(detail=self.status.copy.render_error(exc))
                    )
                    return False
                self.empty_open = False
                await self.session.refresh_trash()
                if report.failed:
                    self.session.trash_banner = self.status.copy.TRASH_MAINTENANCE_FAILED
                    self.status.show_notice(self.status.copy.TRASH_EMPTY_FAILED.format(detail=""))
                    return False
                self.session.trash_banner = None
                if self.pages.trash_entry is not None:
                    self.pages.clear()
                self.status.show_notice(self.status.copy.TRASH_EMPTY_DONE)
                return True
            finally:
                self.status.set_busy(busy=False)

    async def _finish_restore(self, target: Path) -> None:
        """Clear decisions, refresh both catalogs, and open the restored note."""
        self.overwrite_entry = None
        self.delete_entry = None
        self.pages.blocking_message = None
        await self.session.refresh_snapshot()
        await self.session.refresh_trash()
        await self.pages.load(target)
        self.status.show_notice(self.status.copy.PAGE_TRASH_RESTORED)
