# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Single application state controller for the Flet interface.

Views forward user intent here and render the fields this controller exposes.
All blocking settings, scan, capture, and preview work runs in worker threads
so the Flet event loop stays responsive. One lock serializes commands, which
keeps a capture from overlapping a scan or a vault change.
"""

import asyncio
import dataclasses
import datetime
import hashlib
import logging
import os
from collections.abc import Callable
from pathlib import Path

import afanes.core.editing
import afanes.core.links
import afanes.core.names
import afanes.ui.strings
from afanes.core.editing import DraftMode, PageDraft, PageLabels
from afanes.core.errors import (
    AfanesError,
    ConfigurationError,
    ContentChangedError,
    EmptyCaptureError,
    InvalidReferenceError,
    NoteParseError,
    VaultError,
    VaultPathError,
)
from afanes.core.links import DestinationKind
from afanes.core.processing import ProcessingOutcome, ProcessingPlan
from afanes.core.settings import Settings, SettingsStore
from afanes.core.vault import (
    LinkOutcome,
    ReferenceRepairPreview,
    ReferenceSite,
    RenamePreview,
    TrashPreview,
    Vault,
    VaultFailure,
    VaultNote,
    VaultSnapshot,
)
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status

logger = logging.getLogger(__name__)

PAGE_HISTORY_LIMIT = 50
AUTOSAVE_SECONDS = 30


@dataclasses.dataclass(slots=True, eq=False)
class AppState:
    """Mutable state shared by the welcome and Inbox views.

    Attributes
    ----------
    vault : Vault | None
        Active vault service, or ``None`` while the welcome state is shown.
    notes : tuple[VaultNote, ...]
        Inbox notes, newest first.
    failures : tuple[VaultFailure, ...]
        Notes the last scan could not parse.
    selected : Path | None
        Absolute path of the note shown in the preview.
    preview_body : str | None
        Markdown body of the previewed note, without frontmatter.
    busy : bool
        Whether a blocking command is in progress.
    message : str | None
        Banner text for the current error or warning.
    processing_note : Path | None
        Capture currently open in the Processing Wizard.
    processing_body : str | None
        Markdown body of the processing capture.
    processing_plan : ProcessingPlan | None
        Validated plan waiting for confirmation.
    processing_result : Path | None
        Destination of the last successful processing apply.
    page : PageDraft | None
        Page currently open in the right pane, or ``None`` when no page is
        shown.
    editing : bool
        Whether the page is in edit mode.
    history : tuple[Path, ...]
        Page paths behind the current page, oldest first.
    conflict : str | None
        Disk conflict state: ``changed``, ``missing``, or ``None``.
    ambiguous : tuple[Path, ...]
        Candidate paths waiting for the user to choose one.
    pending_labels : PageLabels | None
        Labels waiting for a scheme-change confirmation.
    type_change_sites : tuple[ReferenceSite, ...]
        Notes whose references would become unresolved by a pending type
        change.
    repair_preview : ReferenceRepairPreview | None
        Unsafe-name repair waiting for the user to choose an action.
    rename_preview : RenamePreview | None
        Rename preview waiting for confirmation.
    trash_preview : TrashPreview | None
        Trash preview waiting for confirmation.
    saving : bool
        Whether a page write is in progress.

    Notes
    -----
    This is the only permitted mutable module-level state in the application.
    Tests call :meth:`reset` between cases. Views must not mutate these fields
    directly; they call the command methods.
    """

    vault: Vault | None = None
    notes: tuple[VaultNote, ...] = ()
    failures: tuple[VaultFailure, ...] = ()
    selected: Path | None = None
    preview_body: str | None = None
    busy: bool = False
    message: str | None = None
    processing_note: Path | None = None
    processing_body: str | None = None
    processing_plan: ProcessingPlan | None = None
    processing_result: Path | None = None
    page: PageDraft | None = None
    editing: bool = False
    history: tuple[Path, ...] = ()
    conflict: str | None = None
    ambiguous: tuple[Path, ...] = ()
    pending_labels: PageLabels | None = None
    type_change_sites: tuple[ReferenceSite, ...] = ()
    repair_preview: ReferenceRepairPreview | None = None
    rename_preview: RenamePreview | None = None
    trash_preview: TrashPreview | None = None
    saving: bool = False
    _snapshot: VaultSnapshot | None = dataclasses.field(default=None, repr=False)
    _autosave_task: asyncio.Task[None] | None = dataclasses.field(default=None, repr=False)
    _lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock, repr=False)

    @property
    def vault_root(self) -> Path | None:
        """Return the active vault root, or ``None`` in the welcome state.

        Returns
        -------
        Path | None
            Resolved root of :attr:`vault`, or ``None`` when no vault is open.
        """
        return None if self.vault is None else self.vault.root

    async def start(self) -> None:
        """Load saved settings and open the remembered vault.

        Notes
        -----
        A missing settings file, malformed settings, or an unavailable vault
        leaves the controller in the welcome state with a message. Blocking
        file I/O runs in a worker thread.
        """
        self._start_autosave()
        async with self._lock:
            self.busy = True
            try:
                try:
                    settings = await asyncio.to_thread(SettingsStore.default().load)
                except ConfigurationError:
                    logger.debug("Settings could not be read", exc_info=True)
                    self._show_welcome(afanes.ui.strings.SETTINGS_UNREADABLE)
                    return
                if settings is None:
                    self._show_welcome(None)
                    return
                try:
                    vault = await asyncio.to_thread(self._open_vault, settings.vault)
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Saved vault could not be opened", exc_info=True)
                    self._show_welcome(str(exc))
                    return
                self.vault = vault
                self._clear_processing()
                self.selected = None
                self.preview_body = None
                self.history = ()
                self._clear_page()
                self._apply_snapshot(snapshot)
            finally:
                self.busy = False

    async def choose_vault(self, path: Path) -> None:
        """Open a vault and remember it for later launches.

        Parameters
        ----------
        path : Path
            Directory chosen by the user.

        Notes
        -----
        The vault is scanned before its path is saved. A failed scan or save
        leaves the current state unchanged and reports a message. Blocking
        file I/O runs in a worker thread.
        """
        async with self._lock:
            if not await self._commit_current():
                return
            self.busy = True
            self.message = None
            try:
                try:
                    vault = await asyncio.to_thread(self._open_vault, path)
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Selected vault could not be opened", exc_info=True)
                    self.message = str(exc)
                    return
                try:
                    await asyncio.to_thread(
                        SettingsStore.default().save,
                        Settings(vault=vault.root),
                    )
                except ConfigurationError as exc:
                    logger.debug("Vault selection could not be saved", exc_info=True)
                    self.message = afanes.ui.strings.VAULT_SELECTION_FAILED.format(detail=str(exc))
                    return
                self.vault = vault
                self._clear_processing()
                self.selected = None
                self.preview_body = None
                self.history = ()
                self._clear_page()
                self._apply_snapshot(snapshot)
            finally:
                self.busy = False

    async def change_vault(self, path: Path) -> None:
        """Switch to a different vault without restarting the application.

        Parameters
        ----------
        path : Path
            Directory chosen by the user.

        Notes
        -----
        This delegates to :meth:`choose_vault`; the previous vault is never
        modified.
        """
        await self.choose_vault(path)

    async def refresh(self) -> None:
        """Re-read the vault and update the Inbox.

        Notes
        -----
        A selected note is re-read so an external edit appears in the preview.
        If the note disappeared, the preview is cleared. Blocking file I/O
        runs in a worker thread.
        """
        async with self._lock:
            vault = self.vault
            if vault is None:
                return
            self.busy = True
            try:
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Vault scan failed", exc_info=True)
                    self.message = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
                    return
                self._apply_snapshot(snapshot)
                page = self.page
                if page is not None and page.path is not None and not self.editing:
                    try:
                        content = await asyncio.to_thread(vault.read_page, page.path)
                        self.page = PageDraft.from_page(content, page.reference)
                    except (AfanesError, OSError, UnicodeError) as exc:
                        logger.debug("Page could not be refreshed", exc_info=True)
                        self._clear_page()
                        self.message = afanes.ui.strings.PAGE_OPEN_FAILED.format(detail=str(exc))
                selected = self.selected
                if selected is None:
                    return
                try:
                    self.preview_body = await asyncio.to_thread(vault.read_body, selected)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Preview could not be refreshed", exc_info=True)
                    self.selected = None
                    self.preview_body = None
                    self.message = afanes.ui.strings.PREVIEW_FAILED.format(detail=str(exc))
            finally:
                self.busy = False

    async def capture(self, text: str) -> Path | None:
        """Capture raw text into the vault's inbox.

        Parameters
        ----------
        text : str
            Thought typed into the composer.

        Returns
        -------
        Path | None
            Absolute path of the created note, or ``None`` when nothing was
            written. The caller keeps the composer text when this is ``None``.

        Notes
        -----
        The first non-blank line becomes the filename and the complete text
        becomes the body. The new note is promoted to the top of the list so
        it is visible even when filesystem timestamps tie. Blocking file I/O
        runs in a worker thread.
        """
        async with self._lock:
            if not text.strip():
                self.message = afanes.ui.strings.CAPTURE_EMPTY
                return None
            vault = self.vault
            if vault is None:
                return None
            self.busy = True
            self.message = None
            try:
                try:
                    path = await asyncio.to_thread(vault.capture, text)
                except EmptyCaptureError:
                    self.message = afanes.ui.strings.CAPTURE_EMPTY
                    return None
                except (AfanesError, OSError) as exc:
                    logger.debug("Capture failed", exc_info=True)
                    self.message = afanes.ui.strings.CAPTURE_FAILED.format(detail=str(exc))
                    return None
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Inbox refresh after capture failed", exc_info=True)
                    self.message = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
                    return path
                self._apply_snapshot(snapshot, focus=path)
                return path
            finally:
                self.busy = False

    async def select_note(self, path: Path) -> None:
        """Load a note body into the read-only preview.

        Parameters
        ----------
        path : Path
            Absolute path of a note shown in the Inbox.

        Notes
        -----
        The body is read from disk on demand and never written back. A parse
        or read failure clears the preview and reports a message. Blocking
        file I/O runs in a worker thread.
        """
        async with self._lock:
            vault = self.vault
            if vault is None:
                return
            self.busy = True
            try:
                try:
                    body = await asyncio.to_thread(vault.read_body, path)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Note preview failed", exc_info=True)
                    self.selected = None
                    self.preview_body = None
                    self.message = afanes.ui.strings.PREVIEW_FAILED.format(detail=str(exc))
                    return
                self.selected = path
                self.preview_body = body
                self.message = None
            finally:
                self.busy = False

    @property
    def page_title(self) -> str:
        """Return the display title of the current page.

        Returns
        -------
        str
            Title derived from the draft body, or an empty string when no page
            is open.
        """
        return "" if self.page is None else self.page.display_title

    @property
    def page_path_label(self) -> str:
        """Return the page path relative to the vault.

        Returns
        -------
        str
            Vault-relative path, ``New page`` for an unwritten draft, or an
            empty string when no page is open.
        """
        page = self.page
        if page is None:
            return ""
        if page.path is None:
            return afanes.ui.strings.PAGE_NEW
        root = self.vault_root
        if root is None:
            return page.path.as_posix()
        try:
            return page.path.relative_to(root).as_posix()
        except ValueError:
            return page.path.as_posix()

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
        async with self._lock:
            if self.vault is None:
                return False
            self.busy = True
            try:
                if not await self._commit_current():
                    return False
                previous = self.page.path if self.page is not None else None
                return await self._load_page(path, previous=previous)
            finally:
                self.busy = False

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
        async with self._lock:
            self.busy = True
            try:
                if not await self._commit_current():
                    return False
                while self.history:
                    path = self.history[-1]
                    self.history = self.history[:-1]
                    if await self._load_page(path, previous=None):
                        return True
                self._clear_page()
                return True
            finally:
                self.busy = False

    def edit_page(self) -> bool:
        """Switch the current page into edit mode.

        Returns
        -------
        bool
            ``True`` when a page is open.
        """
        if self.page is None:
            return False
        self.editing = True
        self.message = None
        return True

    async def done_editing(self) -> bool:
        """Commit the current draft and return to read mode.

        Returns
        -------
        bool
            ``True`` when the draft was written or was already clean.

        Notes
        -----
        A failed write keeps edit mode and the draft. A successful commit
        refreshes the Inbox scan.
        """
        async with self._lock:
            if self.page is None:
                self.editing = False
                return False
            self.busy = True
            try:
                if not await self._commit_current():
                    return False
                self.editing = False
                await self._refresh_snapshot()
                return True
            finally:
                self.busy = False

    async def autosave(self) -> bool:
        """Write a dirty edit draft if the page is in edit mode.

        Returns
        -------
        bool
            ``True`` when a write occurred.

        Notes
        -----
        Autosave is skipped when no page is open, edit mode is inactive, the
        draft is clean, or a disk conflict is unresolved.
        """
        async with self._lock:
            page = self.page
            if not self.editing or page is None or self.conflict is not None:
                return False
            if not page.is_dirty:
                return False
            return await self._save_page()

    async def set_page_body(self, body: str) -> None:
        """Replace the draft Markdown body.

        Parameters
        ----------
        body : str
            Complete body, including its heading.
        """
        async with self._lock:
            if self.page is not None:
                self.page = self.page.with_body(body)

    async def set_page_raw_text(self, text: str) -> None:
        """Replace raw rescue text.

        Parameters
        ----------
        text : str
            Complete file text.
        """
        async with self._lock:
            page = self.page
            if page is not None and page.mode is DraftMode.RAW:
                self.page = page.with_raw_text(text)

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
        async with self._lock:
            return await self._apply_label_change(lambda labels: labels.with_type(note_type))

    async def set_page_category(self, category: ReferenceCategory | None) -> bool:
        """Change the draft reference category, previewing stranded references.

        Parameters
        ----------
        category : ReferenceCategory | None
            New category, or ``None`` for an uncategorized reference.

        Returns
        -------
        bool
            ``True`` when the change was applied immediately.
        """
        async with self._lock:
            return await self._apply_label_change(lambda labels: labels.with_category(category))

    async def set_page_status(self, status: Status | None) -> None:
        """Change the draft workflow status.

        Parameters
        ----------
        status : Status | None
            New status, or ``None`` to clear it.
        """
        async with self._lock:
            await self._mutate_labels(lambda labels: labels.with_status(status))

    async def set_page_due_date(self, text: str) -> None:
        """Change the draft due-date field text.

        Parameters
        ----------
        text : str
            Text exactly as typed. It is validated when the draft is saved.
        """
        async with self._lock:
            await self._mutate_labels(lambda labels: labels.with_due_date_text(text))

    async def set_page_people(self, people: tuple[str, ...]) -> None:
        """Replace the draft person assignments.

        Parameters
        ----------
        people : tuple[str, ...]
            Person identities.
        """
        async with self._lock:
            await self._mutate_labels(lambda labels: labels.with_people(people))

    async def set_page_project(self, project: str | None) -> None:
        """Replace the draft project assignment.

        Parameters
        ----------
        project : str | None
            Project identity, or ``None`` to clear it.
        """
        async with self._lock:
            await self._mutate_labels(lambda labels: labels.with_project(project))

    async def apply_type_change(self) -> bool:
        """Apply a type or category change that was waiting for confirmation.

        Returns
        -------
        bool
            ``True`` when the pending labels were applied.
        """
        async with self._lock:
            page = self.page
            labels = self.pending_labels
            if page is None or labels is None:
                return False
            self.page = page.with_labels(labels)
            self.pending_labels = None
            self.type_change_sites = ()
            self.message = None
            return True

    async def cancel_type_change(self) -> None:
        """Discard a pending type or category change."""
        async with self._lock:
            self.pending_labels = None
            self.type_change_sites = ()
            self.message = None

    async def reload_page(self) -> bool:
        """Replace the draft with the current file content after a conflict.

        Returns
        -------
        bool
            ``True`` when the file was re-read and read mode is shown.
        """
        async with self._lock:
            page = self.page
            vault = self.vault
            if page is None or page.path is None or vault is None:
                return False
            self.busy = True
            try:
                try:
                    content = await asyncio.to_thread(vault.read_page, page.path)
                    draft = PageDraft.from_page(content, page.reference)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Page reload failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_OPEN_FAILED.format(detail=str(exc))
                    return False
                self.page = draft
                self.conflict = None
                self.editing = False
                self.message = None
                return True
            finally:
                self.busy = False

    async def overwrite_page(self) -> bool:
        """Write the draft over the current file after an explicit conflict choice.

        Returns
        -------
        bool
            ``True`` when the draft was written and the conflict cleared.
        """
        async with self._lock:
            page = self.page
            vault = self.vault
            if page is None or page.path is None or vault is None:
                return False
            try:
                text = page.to_text()
            except NoteParseError as exc:
                self.message = str(exc)
                return False
            self.busy = True
            try:
                try:
                    content = await asyncio.to_thread(vault.read_page, page.path)
                    new_hash = await asyncio.to_thread(vault.write_page, page.path, text, content.content_hash)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Page overwrite failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc))
                    return False
                self.page = page.after_write(text, content_hash=new_hash)
                self.conflict = None
                self.message = None
                return True
            finally:
                self.busy = False

    async def recreate_page(self) -> bool:
        """Recreate a page that disappeared after it was read.

        Returns
        -------
        bool
            ``True`` when the missing file was recreated from the draft.
        """
        async with self._lock:
            page = self.page
            vault = self.vault
            if page is None or page.path is None or vault is None:
                return False
            try:
                text = page.to_text()
            except NoteParseError as exc:
                self.message = str(exc)
                return False
            self.busy = True
            try:
                try:
                    new_hash = await asyncio.to_thread(vault.recreate_page, page.path, text)
                except ContentChangedError:
                    self.conflict = "changed"
                    self.message = afanes.ui.strings.PAGE_CONFLICT_CHANGED
                    return False
                except (AfanesError, OSError) as exc:
                    logger.debug("Page recreation failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc))
                    return False
                self.page = page.after_write(text, content_hash=new_hash)
                self.conflict = None
                self.message = None
                return True
            finally:
                self.busy = False

    async def discard_draft(self) -> None:
        """Drop the current draft without writing it."""
        async with self._lock:
            self._clear_page()
            self.message = None

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
        kind = afanes.core.links.classify_destination(destination)
        if kind is not DestinationKind.INTERNAL:
            return
        try:
            reference = afanes.core.links.parse_reference(destination)
        except InvalidReferenceError as exc:
            self.message = str(exc)
            return
        snapshot = self._snapshot
        if snapshot is None:
            await self._open_new_draft(reference)
            return
        target = snapshot.link_target(reference)
        if target.outcome is LinkOutcome.RESOLVED:
            await self.open_page(target.paths[0])
            return
        if target.outcome is LinkOutcome.AMBIGUOUS:
            async with self._lock:
                self.ambiguous = target.paths
                self.message = None
            return
        if target.outcome is LinkOutcome.BROKEN:
            if len(target.paths) == 1:
                await self.open_page(target.paths[0])
                return
            async with self._lock:
                self.ambiguous = target.paths
                self.message = None
            return
        safe_page = self._existing_safe_page(reference)
        if safe_page is not None:
            await self.open_page(safe_page)
            await self._offer_repair(reference)
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
        async with self._lock:
            self.ambiguous = ()
        return await self.open_page(path)

    async def clear_ambiguous(self) -> None:
        """Close the candidate picker without opening a page."""
        async with self._lock:
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

    async def apply_repair(self) -> bool:
        """Rewrite references that still use an unsafe link name.

        Returns
        -------
        bool
            ``True`` when the repair was applied.
        """
        async with self._lock:
            preview = self.repair_preview
            vault = self.vault
            if preview is None or vault is None:
                return False
            self.busy = True
            try:
                try:
                    report = await asyncio.to_thread(vault.apply_reference_repair, preview, confirm=True)
                except (AfanesError, OSError) as exc:
                    logger.debug("Reference repair failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_REPAIR_FAILED.format(detail=str(exc))
                    return False
                self.repair_preview = None
                await self._refresh_snapshot()
                remaining = len(report.failed) + len(report.skipped)
                if remaining:
                    self.message = afanes.ui.strings.PAGE_REPAIR_FAILED.format(
                        detail=f"{remaining} notes were not updated"
                    )
                return True
            finally:
                self.busy = False

    async def keep_repair(self) -> None:
        """Leave unsafe link names unchanged and close the repair prompt."""
        async with self._lock:
            self.repair_preview = None
            self.message = None

    async def cancel_repair(self) -> bool:
        """Remove the just-created page and restore the draft.

        Returns
        -------
        bool
            ``True`` when the page was moved to trash and the draft restored.
        """
        async with self._lock:
            page = self.page
            vault = self.vault
            if page is None or page.path is None or vault is None:
                return False
            self.busy = True
            try:
                try:
                    await asyncio.to_thread(vault.trash, page.path, confirm=True)
                except (AfanesError, OSError) as exc:
                    logger.debug("Created page could not be removed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc))
                    return False
                self.page = page.as_new()
                self.editing = True
                self.repair_preview = None
                await self._refresh_snapshot()
                return True
            finally:
                self.busy = False

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
        async with self._lock:
            page = self.page
            vault = self.vault
            if page is None or page.path is None or vault is None:
                return None
            if not await self._commit_current():
                return None
            current = self.page
            path = current.path if current is not None else page.path
            if path is None:
                return None
            self.busy = True
            try:
                try:
                    preview = await asyncio.to_thread(vault.plan_rename, path, new_title, snapshot=self._snapshot)
                except (AfanesError, OSError) as exc:
                    logger.debug("Rename planning failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_RENAME_FAILED.format(detail=str(exc))
                    return None
                self.rename_preview = preview
                self.message = None
                return preview
            finally:
                self.busy = False

    async def apply_rename(self) -> bool:
        """Apply the retained rename preview after confirmation.

        Returns
        -------
        bool
            ``True`` when the rename operation was applied.
        """
        async with self._lock:
            preview = self.rename_preview
            vault = self.vault
            if preview is None or vault is None:
                return False
            self.busy = True
            try:
                try:
                    report = await asyncio.to_thread(vault.apply_rename, preview, confirm=True)
                except (AfanesError, OSError) as exc:
                    logger.debug("Rename failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_RENAME_FAILED.format(detail=str(exc))
                    return False
                self.rename_preview = None
                self.history = tuple(
                    preview.target_path if path == preview.note_path else path for path in self.history
                )
                if not await self._load_page(preview.target_path, previous=None):
                    return False
                self.editing = False
                await self._refresh_snapshot()
                remaining = len(report.failed) + len(report.skipped)
                if remaining:
                    self.message = afanes.ui.strings.PAGE_RENAME_FAILED.format(
                        detail=f"{remaining} notes were not updated"
                    )
                return True
            finally:
                self.busy = False

    async def cancel_rename(self) -> None:
        """Discard the retained rename preview."""
        async with self._lock:
            self.rename_preview = None
            self.message = None

    async def begin_trash(self) -> TrashPreview | None:
        """Plan moving the current page to trash and retain it for confirmation.

        Returns
        -------
        TrashPreview | None
            Preview to show, or ``None`` when planning failed.
        """
        async with self._lock:
            page = self.page
            vault = self.vault
            if page is None or page.path is None or vault is None:
                return None
            if not await self._commit_current():
                return None
            current = self.page
            path = current.path if current is not None else page.path
            if path is None:
                return None
            self.busy = True
            try:
                try:
                    preview = await asyncio.to_thread(vault.plan_trash, path, snapshot=self._snapshot)
                except (AfanesError, OSError) as exc:
                    logger.debug("Trash planning failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_TRASH_FAILED.format(detail=str(exc))
                    return None
                self.trash_preview = preview
                self.message = None
                return preview
            finally:
                self.busy = False

    async def apply_trash(self) -> bool:
        """Move the current page to trash and return through history.

        Returns
        -------
        bool
            ``True`` when the page was moved.
        """
        async with self._lock:
            preview = self.trash_preview
            vault = self.vault
            if preview is None or vault is None:
                return False
            self.busy = True
            try:
                try:
                    await asyncio.to_thread(vault.trash, preview.note_path, confirm=True, snapshot=self._snapshot)
                except (AfanesError, OSError) as exc:
                    logger.debug("Trash failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_TRASH_FAILED.format(detail=str(exc))
                    return False
                self.trash_preview = None
                self.history = tuple(path for path in self.history if path != preview.note_path)
                self._clear_page()
                await self._refresh_snapshot()
            finally:
                self.busy = False
        return await self.back()

    async def cancel_trash(self) -> None:
        """Discard the retained trash preview."""
        async with self._lock:
            self.trash_preview = None
            self.message = None

    async def begin_processing(self, path: Path) -> bool:
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
        async with self._lock:
            vault = self.vault
            if vault is None:
                return False
            if all(note.path != path for note in self.notes):
                self.message = afanes.ui.strings.PROCESSING_MISSING
                return False
            self.busy = True
            self.message = None
            try:
                try:
                    body = await asyncio.to_thread(vault.read_body, path)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Capture could not be read for processing", exc_info=True)
                    self.message = afanes.ui.strings.PROCESSING_READ_FAILED.format(detail=str(exc))
                    return False
                self.processing_note = path
                self.processing_body = body
                self.processing_plan = None
                self.processing_result = None
                self.selected = path
                self.preview_body = body
                return True
            finally:
                self.busy = False

    async def plan_processing(
        self,
        outcome: ProcessingOutcome,
        *,
        status: Status | None = None,
        due_date: datetime.date | None = None,
        people: tuple[str, ...] = (),
        project: str | None = None,
    ) -> ProcessingPlan | None:
        """Build a processing preview for the open capture.

        Parameters
        ----------
        outcome : ProcessingOutcome
            Selected clarification outcome.
        status : Status | None
            Requested target status, when the outcome accepts one.
        due_date : datetime.date | None
            Optional calendar due date for an action or project.
        people : tuple[str, ...]
            Person names assigned to the target.
        project : str | None
            Project name assigned to an action.

        Returns
        -------
        ProcessingPlan | None
            The validated plan, or ``None`` when planning failed.

        Notes
        -----
        Planning never writes. The plan is retained in
        :attr:`processing_plan` for the preview and confirmation step. Blocking
        file I/O runs in a worker thread.
        """
        async with self._lock:
            vault = self.vault
            note = self.processing_note
            if vault is None or note is None:
                return None
            self.busy = True
            self.message = None
            try:
                try:
                    plan = await asyncio.to_thread(
                        vault.plan_processing,
                        note,
                        outcome,
                        status=status,
                        due_date=due_date,
                        people=people,
                        project=project,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Processing plan failed", exc_info=True)
                    self.processing_plan = None
                    self.message = afanes.ui.strings.PROCESSING_PLAN_FAILED.format(detail=str(exc))
                    return None
                self.processing_plan = plan
                return plan
            finally:
                self.busy = False

    async def apply_processing(self) -> Path | None:
        """Apply the current processing plan after confirmation.

        Returns
        -------
        Path | None
            Destination path on success, or ``None`` when the apply failed.

        Notes
        -----
        A successful apply leaves the wizard in a success state and refreshes
        the Inbox. A failed apply keeps the plan so the user can retry. Blocking
        writes and scans run in a worker thread.
        """
        async with self._lock:
            vault = self.vault
            plan = self.processing_plan
            if vault is None or plan is None:
                return None
            self.busy = True
            self.message = None
            try:
                try:
                    target = await asyncio.to_thread(vault.apply_processing, plan, confirm=True)
                except (AfanesError, OSError) as exc:
                    logger.debug("Processing apply failed", exc_info=True)
                    self.message = afanes.ui.strings.PROCESSING_FAILED.format(detail=str(exc))
                    return None
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Inbox refresh after processing failed", exc_info=True)
                    self.message = afanes.ui.strings.PROCESSING_REFRESH_FAILED.format(detail=str(exc))
                else:
                    self._apply_snapshot(snapshot)
                self._clear_processing()
                self.selected = None
                self.preview_body = None
                self.processing_result = target
                return target
            finally:
                self.busy = False

    def cancel_processing(self) -> None:
        """Close the wizard and discard its unsaved plan."""
        self._clear_processing()
        self.message = None

    def finish_processing(self) -> None:
        """Close the success state and return to the Inbox."""
        self._clear_processing()
        self.message = None

    async def _mutate_labels(self, transform: Callable[[PageLabels], PageLabels]) -> bool:
        """Apply a label transformation that cannot change the scheme."""
        page = self.page
        if page is None or page.labels is None:
            return False
        try:
            labels = transform(page.labels)
        except NoteParseError as exc:
            self.message = str(exc)
            return False
        self.page = page.with_labels(labels)
        self.message = None
        return True

    async def _apply_label_change(self, transform: Callable[[PageLabels], PageLabels]) -> bool:
        """Apply a label transformation, previewing a scheme change."""
        page = self.page
        if page is None or page.labels is None:
            return False
        current = page.labels
        try:
            proposed = transform(current)
        except NoteParseError as exc:
            self.message = str(exc)
            return False
        if proposed.scheme is current.scheme or page.path is None:
            self.page = page.with_labels(proposed)
            self.message = None
            return True
        sites = await self._scheme_change_sites(page.path)
        if sites is None:
            return False
        if not sites:
            self.page = page.with_labels(proposed)
            self.message = None
            return True
        self.pending_labels = proposed
        self.type_change_sites = sites
        self.message = None
        return False

    async def _scheme_change_sites(self, path: Path) -> tuple[ReferenceSite, ...] | None:
        """Refresh the snapshot and return references a scheme change would strand."""
        vault = self.vault
        if vault is None:
            return ()
        try:
            snapshot = await asyncio.to_thread(vault.scan)
        except (VaultError, OSError) as exc:
            logger.debug("Snapshot refresh before a type change failed", exc_info=True)
            self.message = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
            return None
        self._apply_snapshot(snapshot)
        return snapshot.referrers(path)

    async def _open_new_draft(self, reference: NoteReference) -> bool:
        """Open an unwritten page for a missing reference."""
        async with self._lock:
            if self.vault is None:
                return False
            self.busy = True
            try:
                if not await self._commit_current():
                    return False
                previous = self.page.path if self.page is not None else None
                self.page = PageDraft.new(reference)
                self.editing = True
                self.conflict = None
                self.ambiguous = ()
                self._clear_page_dialogs()
                self._push_history(previous)
                self.message = None
                return True
            finally:
                self.busy = False

    async def _commit_current(self) -> bool:
        """Write or discard the current draft before a page change."""
        page = self.page
        if page is None:
            return True
        if self.repair_preview is not None:
            self.message = afanes.ui.strings.PAGE_REPAIR_PENDING
            return False
        if self.pending_labels is not None:
            self.message = afanes.ui.strings.PAGE_TYPE_CHANGE_LEAVE
            return False
        if self.rename_preview is not None or self.trash_preview is not None:
            self.message = afanes.ui.strings.PAGE_PENDING_DIALOG
            return False
        if page.is_new and not page.is_dirty:
            self._clear_page()
            return True
        if self.conflict is not None:
            self.message = afanes.ui.strings.PAGE_CONFLICT_LEAVE
            return False
        if not page.is_dirty:
            return True
        if not await self._save_page():
            return False
        if self.repair_preview is not None:
            self.message = afanes.ui.strings.PAGE_REPAIR_PENDING
            return False
        return True

    async def _save_page(self) -> bool:
        """Write the current draft, creating a new page when needed."""
        page = self.page
        vault = self.vault
        if page is None or vault is None:
            return False
        if page.mode is DraftMode.RAW:
            return await self._save_raw_page(page, vault)

        labels = page.labels
        if labels is None:
            self.message = afanes.ui.strings.PAGE_SAVE_FAILED.format(detail="Labels are unavailable")
            return False
        try:
            text = page.to_text()
        except NoteParseError as exc:
            self.message = str(exc)
            return False

        self.saving = True
        try:
            if page.is_new:
                return await self._create_new_page(page, labels, text, vault)

            path = page.path
            if path is None:
                self.message = afanes.ui.strings.PAGE_SAVE_FAILED.format(detail="The page has no path")
                return False
            try:
                new_hash = await asyncio.to_thread(vault.write_page, path, text, page.baseline_hash)
            except ContentChangedError:
                self.conflict = "changed"
                self.message = afanes.ui.strings.PAGE_CONFLICT_CHANGED
                return False
            except VaultPathError:
                self.conflict = "missing"
                self.message = afanes.ui.strings.PAGE_CONFLICT_MISSING
                return False
            except (AfanesError, OSError) as exc:
                logger.debug("Page save failed", exc_info=True)
                self.message = afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc))
                return False
            self.page = page.after_write(text, content_hash=new_hash)
            self.message = None
            return True
        finally:
            self.saving = False

    async def _create_new_page(
        self,
        page: PageDraft,
        labels: PageLabels,
        text: str,
        vault: Vault,
    ) -> bool:
        """Create the file for a new draft and adopt its path."""
        reference = page.reference
        name = reference.name if reference is not None else page.identity
        try:
            path = await asyncio.to_thread(
                vault.create_page,
                name,
                labels.note_type,
                labels.category,
                text=text,
            )
        except (AfanesError, OSError) as exc:
            logger.debug("New page could not be created", exc_info=True)
            self.message = afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc))
            return False
        new_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.page = page.after_write(text, content_hash=new_hash, path=path)
        await self._plan_repair_after_create(self.page, vault)
        return True

    async def _save_raw_page(self, page: PageDraft, vault: Vault) -> bool:
        """Write raw rescue text with the conflict guard."""
        path = page.path
        if path is None:
            return False
        self.saving = True
        try:
            try:
                new_hash = await asyncio.to_thread(vault.write_page, path, page.raw_text, page.baseline_hash)
            except ContentChangedError:
                self.conflict = "changed"
                self.message = afanes.ui.strings.PAGE_CONFLICT_CHANGED
                return False
            except VaultPathError:
                self.conflict = "missing"
                self.message = afanes.ui.strings.PAGE_CONFLICT_MISSING
                return False
            except (AfanesError, OSError) as exc:
                logger.debug("Raw page save failed", exc_info=True)
                self.message = afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc))
                return False
            self.page = page.after_write(page.raw_text, content_hash=new_hash)
            if self.page.mode is DraftMode.NORMAL:
                self.message = afanes.ui.strings.PAGE_RAW_UPGRADED
            else:
                self.message = None
            return True
        finally:
            self.saving = False

    async def _plan_repair_after_create(self, page: PageDraft, vault: Vault) -> None:
        """Offer a repair when a created page's identity was sanitized."""
        reference = page.reference
        if reference is None:
            return
        safe_name = afanes.core.names.safe_filename(reference.name)
        if afanes.core.names.normalize_name(safe_name) == afanes.core.names.normalize_name(reference.name):
            return
        try:
            snapshot = await asyncio.to_thread(vault.scan)
        except (VaultError, OSError) as exc:
            logger.debug("Snapshot refresh after creating a page failed", exc_info=True)
            self.message = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
            return
        self._apply_snapshot(snapshot)
        await self._plan_repair(reference, snapshot, vault)

    async def _offer_repair(self, reference: NoteReference) -> None:
        """Offer a repair for an unsafe reference that opened an existing page."""
        vault = self.vault
        if vault is None:
            return
        try:
            snapshot = await asyncio.to_thread(vault.scan)
        except (VaultError, OSError) as exc:
            logger.debug("Snapshot refresh before a reference repair failed", exc_info=True)
            self.message = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
            return
        self._apply_snapshot(snapshot)
        await self._plan_repair(reference, snapshot, vault)

    async def _plan_repair(
        self,
        reference: NoteReference,
        snapshot: VaultSnapshot,
        vault: Vault,
    ) -> None:
        """Plan a reference repair and retain it for the dialog."""
        safe_name = afanes.core.names.safe_filename(reference.name)
        if afanes.core.names.normalize_name(safe_name) == afanes.core.names.normalize_name(reference.name):
            return
        new = NoteReference(scheme=reference.scheme, name=safe_name)
        try:
            preview = await asyncio.to_thread(vault.plan_reference_repair, reference, new, snapshot=snapshot)
        except (AfanesError, OSError) as exc:
            logger.debug("Reference repair could not be planned", exc_info=True)
            self.message = afanes.ui.strings.PAGE_REPAIR_FAILED.format(detail=str(exc))
            return
        if preview.sites:
            self.repair_preview = preview

    def _existing_safe_page(self, reference: NoteReference) -> Path | None:
        """Return the parsed page whose safe identity matches an unsafe reference."""
        safe_name = afanes.core.names.safe_filename(reference.name)
        if afanes.core.names.normalize_name(safe_name) == afanes.core.names.normalize_name(reference.name):
            return None
        snapshot = self._snapshot
        if snapshot is None:
            return None
        candidates = snapshot.catalog.candidates(reference.scheme, safe_name)
        return candidates[0] if len(candidates) == 1 else None

    async def _load_page(self, path: Path, *, previous: Path | None) -> bool:
        """Read a note into the page pane and optionally push the previous page."""
        vault = self.vault
        if vault is None:
            return False
        try:
            content = await asyncio.to_thread(vault.read_page, path)
            draft = PageDraft.from_page(content)
        except (AfanesError, OSError, UnicodeError) as exc:
            logger.debug("Page could not be read", exc_info=True)
            self.message = afanes.ui.strings.PAGE_OPEN_FAILED.format(detail=str(exc))
            return False
        self.page = draft
        self.editing = draft.mode is DraftMode.RAW
        self.conflict = None
        self.ambiguous = ()
        self._clear_page_dialogs()
        self._push_history(previous)
        self.message = None
        return True

    async def _refresh_snapshot(self) -> None:
        """Rescan the vault and update the Inbox lists."""
        vault = self.vault
        if vault is None:
            return
        try:
            snapshot = await asyncio.to_thread(vault.scan)
        except (VaultError, OSError) as exc:
            logger.debug("Snapshot refresh failed", exc_info=True)
            self.message = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
            return
        self._apply_snapshot(snapshot)

    def _start_autosave(self) -> None:
        """Start the single autosave loop when it is not already running."""
        if self._autosave_task is None or self._autosave_task.done():
            self._autosave_task = asyncio.create_task(self._autosave_loop())

    async def _autosave_loop(self) -> None:
        """Write a dirty draft roughly every :data:`AUTOSAVE_SECONDS`."""
        while True:
            await asyncio.sleep(AUTOSAVE_SECONDS)
            await self.autosave()

    def _push_history(self, path: Path | None) -> None:
        """Push one page path onto the bounded history."""
        if path is None:
            return
        self.history = (*self.history, path)[-PAGE_HISTORY_LIMIT:]

    def _clear_page(self) -> None:
        """Clear the page, its dialogs, and its conflict state."""
        self.page = None
        self.editing = False
        self.conflict = None
        self.ambiguous = ()
        self.saving = False
        self._clear_page_dialogs()

    def _clear_page_dialogs(self) -> None:
        """Clear pending page dialogs without changing the current page."""
        self.pending_labels = None
        self.type_change_sites = ()
        self.repair_preview = None
        self.rename_preview = None
        self.trash_preview = None

    def reset(self) -> None:
        """Return the controller to its initial state.

        Notes
        -----
        Tests call this between cases and the application calls it on
        shutdown. A fresh command lock is created for the next event loop.
        """
        if self._autosave_task is not None:
            self._autosave_task.cancel()
            self._autosave_task = None
        self.vault = None
        self.notes = ()
        self.failures = ()
        self.selected = None
        self.preview_body = None
        self.busy = False
        self.message = None
        self.history = ()
        self._snapshot = None
        self._clear_processing()
        self._clear_page()
        self._lock = asyncio.Lock()

    def note_title(self, path: Path) -> str:
        """Return the display title for a note in the current Inbox list.

        Parameters
        ----------
        path : Path
            Absolute path of a note shown in the Inbox.

        Returns
        -------
        str
            Display title derived from the note's first level-1 heading, or its
            identity when the body has none. When ``path`` is no longer in the
            current list, its filename stem is returned as a safe fallback.

        Notes
        -----
        This method is pure in-memory work over the last scan. It never reads
        the file and never parses Markdown in the view layer.
        """
        note = next((note for note in self.notes if note.path == path), None)
        return path.stem if note is None else note.title

    def assignment_candidates(self, scheme: ReferenceScheme, query: str) -> tuple[VaultNote, ...]:
        """Return assignment suggestions from the last vault scan.

        Parameters
        ----------
        scheme : ReferenceScheme
            Namespace to search, normally ``person`` or ``project``.
        query : str
            Free text typed by the user. An empty query matches every note in
            the scheme.

        Returns
        -------
        tuple[VaultNote, ...]
            Matching notes ordered by display title, then identity, or an empty
            tuple when no vault is open.

        Notes
        -----
        This is pure in-memory work over the retained snapshot. It performs no
        file I/O and never rescans the vault, so it is safe to call from a
        keystroke handler.
        """
        snapshot = self._snapshot
        if snapshot is None:
            return ()
        return snapshot.assignment_candidates(scheme, query)

    def _clear_processing(self) -> None:
        """Clear the Processing Wizard session fields."""
        self.processing_note = None
        self.processing_body = None
        self.processing_plan = None
        self.processing_result = None

    def _open_vault(self, path: Path) -> Vault:
        """Open a vault and map filesystem failures to user-facing errors.

        Parameters
        ----------
        path : Path
            Directory chosen by the user.

        Returns
        -------
        Vault
            Validated vault service for the directory.

        Raises
        ------
        VaultError
            If the path is missing, is not a directory, cannot be read, or
            cannot be resolved.
        """
        if not path.exists():
            raise VaultError(afanes.ui.strings.VAULT_MISSING)
        if not path.is_dir():
            raise VaultError(afanes.ui.strings.VAULT_NOT_DIRECTORY)
        if not os.access(path, os.R_OK):
            raise VaultError(afanes.ui.strings.VAULT_UNREADABLE)
        try:
            return Vault(path)
        except OSError as exc:
            raise VaultError(afanes.ui.strings.VAULT_UNREADABLE) from exc

    def _show_welcome(self, message: str | None) -> None:
        """Clear the vault state and show the welcome screen."""
        self.vault = None
        self.notes = ()
        self.failures = ()
        self.selected = None
        self.preview_body = None
        self._snapshot = None
        self.history = ()
        self._clear_processing()
        self._clear_page()
        self.message = message

    def _apply_snapshot(self, snapshot: VaultSnapshot, focus: Path | None = None) -> None:
        """Replace the inbox list from a scan result."""
        self._snapshot = snapshot
        notes = list(snapshot.inbox_notes())
        if focus is not None:
            for index, note in enumerate(notes):
                if note.path == focus:
                    notes.insert(0, notes.pop(index))
                    break
        self.notes = tuple(notes)
        self.failures = snapshot.failures
        if self.selected is not None and all(note.path != self.selected for note in self.notes):
            self.selected = None
            self.preview_body = None
        self.message = None


app_state = AppState()
