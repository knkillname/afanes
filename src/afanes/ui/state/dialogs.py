"""Transient page dialogs: labels, repairs, renames, and trash."""

import asyncio
import dataclasses
import logging
from collections.abc import Callable
from pathlib import Path

import afanes.core.vault.naming
import afanes.ui.strings
from afanes.core.editing import NormalDraft, PageDraftFactory, PageLabels
from afanes.core.errors import AfanesError, ContentChangedError, NoteParseError, VaultError
from afanes.core.vault.naming import CategoryMovePreview, RenamePreview, TrashPreview
from afanes.core.vault.snapshot import ReferenceSite, VaultPath
from afanes.models.note import CategoryLabel, NoteType, Status
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.navigation import PageNavigator
from afanes.ui.state.pages import PageEditorState
from afanes.ui.state.session import VaultSession
from afanes.ui.state.status import UiStatus

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class PageDialogState:
    """Pending page dialogs and the labels they would change.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the scan snapshot.
    pages : PageEditorState
        Editor that owns the open draft.
    navigation : PageNavigator
        Navigation state that owns the history stack.
    status : UiStatus
        Shared banner and busy flags.
    command_lock : CommandLock
        Shared command lock.
    pending_labels : PageLabels | None
        Labels waiting for a scheme-change confirmation.
    type_change_sites : tuple[ReferenceSite, ...]
        Notes whose references would become unresolved by a pending type
        change.
    category_move : CategoryMovePreview | None
        Category move waiting for confirmation.
    rename_preview : RenamePreview | None
        Rename preview waiting for confirmation.
    trash_preview : TrashPreview | None
        Trash preview waiting for confirmation.
    """

    session: VaultSession
    pages: PageEditorState
    navigation: PageNavigator
    status: UiStatus
    command_lock: CommandLock
    pending_labels: PageLabels | None = None
    type_change_sites: tuple[ReferenceSite, ...] = ()
    category_move: CategoryMovePreview | None = None
    rename_preview: RenamePreview | None = None
    trash_preview: TrashPreview | None = None

    def reset(self) -> None:
        """Clear every pending dialog and its leave guard."""
        self.pending_labels = None
        self.type_change_sites = ()
        self.category_move = None
        self.rename_preview = None
        self.trash_preview = None
        self.pages.blocking_message = None

    async def set_page_type(self, note_type: NoteType) -> bool:
        """Change the draft type, previewing stranded references.

        Parameters
        ----------
        note_type : NoteType
            New type.

        Returns
        -------
        bool
            ``True`` when the change was applied immediately. ``False`` means
            a confirmation is pending or the change failed.
        """
        async with self.command_lock:
            return await self._apply_label_change(lambda labels: labels.with_type(note_type))

    async def set_page_category(self, category: CategoryLabel | None) -> bool:
        """Change the draft category, previewing the folder move.

        Parameters
        ----------
        category : CategoryLabel | None
            New category, or ``None`` for an uncategorized reference.

        Returns
        -------
        bool
            ``True`` when the labels changed without a pending move.
            ``False`` means a move is pending or the change failed.
        """
        async with self.command_lock:
            page = self.pages.page
            if not isinstance(page, NormalDraft):
                return False
            proposed = page.labels.with_category(category)
            if proposed == page.labels:
                return True
            if page.path is None:
                self.pages.page = page.with_labels(proposed)
                self.status.clear_message()
                return True
            vault = self.session.vault
            if vault is None:
                return False
            try:
                preview = await asyncio.to_thread(
                    afanes.core.vault.naming.VaultNaming(vault).plan_category_move,
                    page.path,
                    proposed.category,
                    snapshot=self.session.snapshot,
                )
            except (AfanesError, OSError) as exc:
                logger.debug("Category move planning failed", exc_info=True)
                self.status.show_message(afanes.ui.strings.PAGE_CATEGORY_MOVE_FAILED.format(detail=str(exc)))
                return False
            if VaultPath.same(preview.target_path, preview.note_path):
                self.pages.page = page.with_labels(proposed)
                self.status.clear_message()
                return True
            self.category_move = preview
            self.pending_labels = proposed
            self.pages.blocking_message = afanes.ui.strings.PAGE_TYPE_CHANGE_LEAVE
            self.status.clear_message()
            return False

    async def set_page_status(self, status: Status | None) -> None:
        """Change the draft workflow status.

        Parameters
        ----------
        status : Status | None
            New status, or ``None`` to clear it.
        """
        async with self.command_lock:
            await self._mutate_labels(lambda labels: labels.with_status(status))

    async def set_page_due_date(self, text: str) -> None:
        """Change the draft due-date field text.

        Parameters
        ----------
        text : str
            Text exactly as typed. It is validated when the draft is saved.
        """
        async with self.command_lock:
            await self._mutate_labels(lambda labels: labels.with_due_date_text(text))

    async def apply_category_move(self) -> bool:
        """Apply the pending category change and move the file.

        Returns
        -------
        bool
            ``True`` when the category was written and the file moved.
        """
        async with self.command_lock:
            preview = self.category_move
            labels = self.pending_labels
            vault = self.session.vault
            if preview is None or labels is None or vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    target = await asyncio.to_thread(
                        afanes.core.vault.naming.VaultNaming(vault).apply_category_move, preview, confirm=True
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Category move failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_CATEGORY_MOVE_FAILED.format(detail=str(exc)))
                    return False
                self.category_move = None
                self.pending_labels = None
                self.pages.blocking_message = None
                self.navigation.history = tuple(
                    target if path == preview.note_path else path for path in self.navigation.history
                )
                if not await self.pages.load(target):
                    return False
                self.pages.editing = False
                await self.session.refresh_snapshot()
                return True
            finally:
                self.status.set_busy(busy=False)

    async def cancel_category_move(self) -> None:
        """Discard a pending category change and keep the file in place.

        Notes
        -----
        The category and the file location are unchanged.
        """
        async with self.command_lock:
            self.category_move = None
            self.pending_labels = None
            self.pages.blocking_message = None
            self.status.clear_message()

    async def apply_type_change(self) -> bool:
        """Apply a type or category change that was waiting for confirmation.

        Returns
        -------
        bool
            ``True`` when the pending labels were applied.
        """
        async with self.command_lock:
            page = self.pages.page
            labels = self.pending_labels
            if not isinstance(page, NormalDraft) or labels is None:
                return False
            self.pages.page = page.with_labels(labels)
            self.pending_labels = None
            self.type_change_sites = ()
            self.pages.blocking_message = None
            self.status.clear_message()
            return True

    async def cancel_type_change(self) -> None:
        """Discard a pending type or category change."""
        async with self.command_lock:
            self.pending_labels = None
            self.type_change_sites = ()
            self.pages.blocking_message = None
            self.status.clear_message()

    async def apply_repair(self) -> bool:
        """Rewrite references that still use an unsafe link name.

        Returns
        -------
        bool
            ``True`` when the repair was applied.
        """
        async with self.command_lock:
            preview = self.pages.repair_preview
            vault = self.session.vault
            if preview is None or vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    report = await asyncio.to_thread(
                        afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair, preview, confirm=True
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Reference repair failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_REPAIR_FAILED.format(detail=str(exc)))
                    return False
                self.pages.repair_preview = None
                await self.session.refresh_snapshot()
                remaining = len(report.failed) + len(report.skipped)
                if remaining:
                    self.status.show_message(
                        afanes.ui.strings.PAGE_REPAIR_FAILED.format(detail=f"{remaining} notes were not updated")
                    )
                return True
            finally:
                self.status.set_busy(busy=False)

    async def keep_repair(self) -> None:
        """Leave unsafe link names unchanged and close the repair prompt."""
        async with self.command_lock:
            self.pages.repair_preview = None
            self.status.clear_message()

    async def cancel_repair(self) -> bool:
        """Remove the just-created page and restore the draft.

        Returns
        -------
        bool
            ``True`` when the page was moved to trash and the draft restored.
        """
        async with self.command_lock:
            page = self.pages.page
            vault = self.session.vault
            if page is None or page.path is None or vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    await asyncio.to_thread(afanes.core.vault.naming.VaultNaming(vault).trash, page.path, confirm=True)
                except (AfanesError, OSError) as exc:
                    logger.debug("Created page could not be removed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc)))
                    return False
                self.pages.page = page.as_new()
                self.pages.editing = True
                self.pages.repair_preview = None
                await self.session.refresh_snapshot()
                return True
            finally:
                self.status.set_busy(busy=False)

    async def begin_rename(self, new_title: str) -> RenamePreview | None:
        """Plan a rename and retain it for confirmation.

        Parameters
        ----------
        new_title : str
            Requested new identity.

        Returns
        -------
        RenamePreview | None
            Preview to show, or ``None`` when planning failed.
        """
        async with self.command_lock:
            page = self.pages.page
            vault = self.session.vault
            if page is None or page.path is None or vault is None:
                return None
            if not await self.pages.commit():
                return None
            current = self.pages.page
            path = current.path if current is not None else page.path
            if path is None:
                return None
            self.status.set_busy(busy=True)
            try:
                try:
                    preview = await asyncio.to_thread(
                        afanes.core.vault.naming.VaultNaming(vault).plan_rename,
                        path,
                        new_title,
                        snapshot=self.session.snapshot,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Rename planning failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_RENAME_FAILED.format(detail=str(exc)))
                    return None
                self.rename_preview = preview
                self.pages.blocking_message = afanes.ui.strings.PAGE_PENDING_DIALOG
                self.status.clear_message()
                return preview
            finally:
                self.status.set_busy(busy=False)

    async def apply_rename(self) -> bool:
        """Apply the retained rename preview after confirmation.

        Returns
        -------
        bool
            ``True`` when the rename operation was applied.
        """
        async with self.command_lock:
            preview = self.rename_preview
            vault = self.session.vault
            if preview is None or vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    report = await asyncio.to_thread(
                        afanes.core.vault.naming.VaultNaming(vault).apply_rename, preview, confirm=True
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Rename failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_RENAME_FAILED.format(detail=str(exc)))
                    return False
                self.rename_preview = None
                self.pages.blocking_message = None
                self.navigation.history = tuple(
                    preview.target_path if path == preview.note_path else path for path in self.navigation.history
                )
                if not await self.pages.load(preview.target_path):
                    return False
                self.pages.editing = False
                await self.session.refresh_snapshot()
                remaining = len(report.failed) + len(report.skipped)
                if remaining:
                    self.status.show_message(
                        afanes.ui.strings.PAGE_RENAME_FAILED.format(detail=f"{remaining} notes were not updated")
                    )
                return True
            finally:
                self.status.set_busy(busy=False)

    async def cancel_rename(self) -> None:
        """Discard the retained rename preview."""
        async with self.command_lock:
            self.rename_preview = None
            self.pages.blocking_message = None
            self.status.clear_message()

    async def begin_trash(self) -> TrashPreview | None:
        """Plan moving the current page to trash and retain it for confirmation.

        Returns
        -------
        TrashPreview | None
            Preview to show, or ``None`` when planning failed.
        """
        async with self.command_lock:
            page = self.pages.page
            vault = self.session.vault
            if page is None or page.path is None or vault is None:
                return None
            if not await self.pages.commit():
                return None
            current = self.pages.page
            path = current.path if current is not None else page.path
            if path is None:
                return None
            self.status.set_busy(busy=True)
            try:
                try:
                    preview = await asyncio.to_thread(
                        afanes.core.vault.naming.VaultNaming(vault).plan_trash, path, snapshot=self.session.snapshot
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Trash planning failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_TRASH_FAILED.format(detail=str(exc)))
                    return None
                self.trash_preview = preview
                self.pages.blocking_message = afanes.ui.strings.PAGE_PENDING_DIALOG
                self.status.clear_message()
                return preview
            finally:
                self.status.set_busy(busy=False)

    async def apply_trash(self) -> bool:
        """Move the current page to trash and return through history.

        Returns
        -------
        bool
            ``True`` when the page was moved.
        """
        async with self.command_lock:
            preview = self.trash_preview
            vault = self.session.vault
            if preview is None or vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    await asyncio.to_thread(
                        afanes.core.vault.naming.VaultNaming(vault).trash,
                        preview.note_path,
                        confirm=True,
                        snapshot=self.session.snapshot,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Trash failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_TRASH_FAILED.format(detail=str(exc)))
                    return False
                self.trash_preview = None
                self.pages.blocking_message = None
                self.navigation.history = tuple(path for path in self.navigation.history if path != preview.note_path)
                self.pages.clear()
                await self.session.refresh_snapshot()
            finally:
                self.status.set_busy(busy=False)
        return await self.navigation.back()

    async def cancel_trash(self) -> None:
        """Discard the retained trash preview."""
        async with self.command_lock:
            self.trash_preview = None
            self.pages.blocking_message = None
            self.status.clear_message()

    async def _mutate_labels(self, transform: Callable[[PageLabels], PageLabels]) -> bool:
        """Apply a label transformation that cannot change the scheme."""
        page = self.pages.page
        if not isinstance(page, NormalDraft):
            return False
        try:
            labels = transform(page.labels)
        except NoteParseError as exc:
            self.status.show_message(str(exc))
            return False
        self.pages.page = page.with_labels(labels)
        self.status.clear_message()
        return True

    async def _apply_label_change(self, transform: Callable[[PageLabels], PageLabels]) -> bool:
        """Apply a label transformation, previewing a scheme change."""
        page = self.pages.page
        if not isinstance(page, NormalDraft):
            return False
        current = page.labels
        try:
            proposed = transform(current)
        except NoteParseError as exc:
            self.status.show_message(str(exc))
            return False
        if proposed.scheme is current.scheme or page.path is None:
            self.pages.page = page.with_labels(proposed)
            self.status.clear_message()
            return True
        sites = await self._scheme_change_sites(page.path)
        if sites is None:
            return False
        if not sites:
            self.pages.page = page.with_labels(proposed)
            self.status.clear_message()
            return True
        self.pending_labels = proposed
        self.type_change_sites = sites
        self.pages.blocking_message = afanes.ui.strings.PAGE_TYPE_CHANGE_LEAVE
        self.status.clear_message()
        return False

    async def _scheme_change_sites(self, path: Path) -> tuple[ReferenceSite, ...] | None:
        """Refresh the snapshot and return references a scheme change would strand."""
        vault = self.session.vault
        if vault is None:
            return ()
        try:
            snapshot = await asyncio.to_thread(vault.scan)
        except (VaultError, OSError) as exc:
            logger.debug("Snapshot refresh before a type change failed", exc_info=True)
            self.status.show_message(afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc)))
            return None
        self.session.apply_snapshot(snapshot)
        return snapshot.referrers(path)

    def clear(self) -> None:
        """Clear pending page dialogs without changing the current page."""
        self.pending_labels = None
        self.category_move = None
        self.type_change_sites = ()
        self.pages.repair_preview = None
        self.rename_preview = None
        self.trash_preview = None
        self.pages.blocking_message = None

    async def reload_page(self) -> bool:
        """Replace the draft with the current file content after a conflict.

        Returns
        -------
        bool
            ``True`` when the file was re-read and read mode is shown.
        """
        async with self.command_lock:
            page = self.pages.page
            vault = self.session.vault
            if page is None or page.path is None or vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    content = await asyncio.to_thread(vault.read_page, page.path)
                    draft = PageDraftFactory.from_page(content, page.reference)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Page reload failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_OPEN_FAILED.format(detail=str(exc)))
                    return False
                self.pages.page = draft
                self.pages.conflict = None
                self.pages.editing = False
                self.status.clear_message()
                return True
            finally:
                self.status.set_busy(busy=False)

    async def overwrite_page(self) -> bool:
        """Write the draft over the current file after an explicit conflict choice.

        Returns
        -------
        bool
            ``True`` when the draft was written and the conflict cleared.
        """
        async with self.command_lock:
            page = self.pages.page
            vault = self.session.vault
            if page is None or page.path is None or vault is None:
                return False
            try:
                text = page.to_text()
            except NoteParseError as exc:
                self.status.show_message(str(exc))
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    content = await asyncio.to_thread(vault.read_page, page.path)
                    new_hash = await asyncio.to_thread(
                        afanes.core.vault.pages.VaultPages(vault).write_page, page.path, text, content.content_hash
                    )
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Page overwrite failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc)))
                    return False
                self.pages.page = page.after_write(text, content_hash=new_hash)
                self.pages.conflict = None
                self.status.clear_message()
                return True
            finally:
                self.status.set_busy(busy=False)

    async def recreate_page(self) -> bool:
        """Recreate a page that disappeared after it was read.

        Returns
        -------
        bool
            ``True`` when the missing file was recreated from the draft.
        """
        async with self.command_lock:
            page = self.pages.page
            vault = self.session.vault
            if page is None or page.path is None or vault is None:
                return False
            try:
                text = page.to_text()
            except NoteParseError as exc:
                self.status.show_message(str(exc))
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    new_hash = await asyncio.to_thread(
                        afanes.core.vault.pages.VaultPages(vault).recreate_page, page.path, text
                    )
                except ContentChangedError:
                    self.pages.conflict = "changed"
                    self.status.show_message(afanes.ui.strings.PAGE_CONFLICT_CHANGED)
                    return False
                except (AfanesError, OSError) as exc:
                    logger.debug("Page recreation failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc)))
                    return False
                self.pages.page = page.after_write(text, content_hash=new_hash)
                self.pages.conflict = None
                self.status.clear_message()
                return True
            finally:
                self.status.set_busy(busy=False)
