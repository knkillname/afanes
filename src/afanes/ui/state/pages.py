"""Page draft, editing mode, conflict recovery, and autosave state."""

import asyncio
import dataclasses
import datetime
import hashlib
import logging
from pathlib import Path

import afanes.core.editing
import afanes.core.names
import afanes.core.project_body
import afanes.core.steps
import afanes.core.vault.naming
import afanes.core.vault.pages
import afanes.core.vault.steps
import afanes.ui.strings
from afanes.core.editing import DraftMode, NormalDraft, PageDraft, PageDraftFactory, PageLabels, RawDraft
from afanes.core.errors import AfanesError, ContentChangedError, NoteParseError, VaultError, VaultPathError
from afanes.core.vault.naming import ReferenceRepairPreview
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import VaultSnapshot
from afanes.models.link import NoteReference
from afanes.models.note import NoteType
from afanes.models.step import ProjectStep, StepEdit, StepEditKind
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.session import VaultSession
from afanes.ui.state.status import UiStatus

logger = logging.getLogger(__name__)

AUTOSAVE_SECONDS = 30


@dataclasses.dataclass(slots=True)
class PageEditorState:
    """Page draft, editing mode, conflict recovery, and autosave state.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the scan snapshot.
    status : UiStatus
        Shared banner and busy flags.
    command_lock : CommandLock
        Shared command lock.
    page : PageDraft | None
        Page currently open in the right pane.
    editing : bool
        Whether the page is in edit mode.
    conflict : str | None
        Disk conflict state: ``changed``, ``missing``, or ``None``.
    saving : bool
        Whether a page write is in progress.
    autosave_task : asyncio.Task[None] | None
        Single background autosave loop, when started.
    blocking_message : str | None
        Banner text that explains why the page cannot be left yet, or
        ``None`` when a pending dialog does not block navigation.
    repair_preview : ReferenceRepairPreview | None
        Unsafe-name repair waiting for the user to choose an action.
    """

    session: VaultSession
    status: UiStatus
    command_lock: CommandLock
    page: PageDraft | None = None
    editing: bool = False
    conflict: str | None = None
    saving: bool = False
    autosave_task: asyncio.Task[None] | None = None
    blocking_message: str | None = None
    repair_preview: ReferenceRepairPreview | None = None

    async def follow_external_change(self, snapshot: VaultSnapshot) -> None:
        """Reconcile the open page after a background rescan.

        Parameters
        ----------
        snapshot : VaultSnapshot
            Scan that was just applied.

        Notes
        -----
        The caller decides whether a processing or review flow is focused; this
        method only reconciles the open page. A dirty draft raises the existing
        conflict state, and a clean draft is re-read from disk. This helper
        performs a blocking read in a worker thread and never writes.
        """
        vault = self.session.vault
        page = self.page
        if vault is None or page is None or page.path is None:
            return
        note = snapshot.find_note(page.path)
        if note is None:
            self._raise_page_conflict("missing")
            return
        if note.content_hash == page.baseline_hash:
            return
        if page.is_dirty:
            self._raise_page_conflict("changed")
            return
        try:
            content = await asyncio.to_thread(vault.read_page, page.path)
            draft = PageDraftFactory.from_page(content, page.reference)
        except (AfanesError, OSError, UnicodeError):
            logger.debug("Open page could not follow an external change", exc_info=True)
            self._raise_page_conflict("missing")
            return
        self.page = draft
        self.editing = self.editing or draft.mode is DraftMode.RAW
        self.conflict = None

    def _raise_page_conflict(self, conflict: str) -> None:
        """Set one disk conflict without replacing an existing one.

        Parameters
        ----------
        conflict : str
            ``changed`` when the file was rewritten, or ``missing`` when it
            disappeared.
        """
        if self.conflict is not None:
            return
        self.conflict = conflict
        if conflict == "missing":
            self.status.show_message(afanes.ui.strings.PAGE_CONFLICT_MISSING)
        else:
            self.status.show_message(afanes.ui.strings.PAGE_CONFLICT_CHANGED)

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
    def page_mode(self) -> DraftMode | None:
        """Return the current page's editing mode, or ``None``.

        Returns
        -------
        DraftMode | None
            Normal editing or raw rescue mode, or ``None`` when no page is
            open.
        """
        return None if self.page is None else self.page.mode

    @property
    def page_body(self) -> str:
        """Return the current page's editable body.

        Returns
        -------
        str
            Draft body, or an empty string when no page is open or the page is
            in raw rescue mode.
        """
        return "" if self.page is None else self.page.body

    @property
    def page_labels(self) -> PageLabels | None:
        """Return the current page's editable labels.

        Returns
        -------
        PageLabels | None
            Labels for a normal draft, or ``None`` when no page is open or the
            page is in raw rescue mode.
        """
        return None if self.page is None else self.page.labels

    @property
    def page_steps(self) -> tuple[ProjectStep, ...]:
        """Return the current page's project steps.

        Returns
        -------
        tuple[ProjectStep, ...]
            Steps from the latest scan for the open project, or an empty tuple
            for a non-project or unopened page.
        """
        page = self.page
        snapshot = self.session.snapshot
        if page is None or page.path is None or snapshot is None:
            return ()
        note = next((value for value in snapshot.notes if value.path == page.path), None)
        return () if note is None else note.steps

    @property
    def page_body_blocks(self) -> tuple[afanes.core.project_body.BodyBlock, ...]:
        """Return the current project body split into renderable blocks.

        Returns
        -------
        tuple[ProseBlock | StepListBlock, ...]
            Ordered blocks for a project page, or an empty tuple for a
            non-project or unopened page.
        """
        page = self.page
        if page is None:
            return ()
        labels = page.labels
        if labels is None or labels.note_type is not NoteType.PROJECT:
            return ()
        return afanes.core.project_body.ProjectBody(self.page_body).blocks

    @property
    def page_read_text(self) -> str:
        """Return the read-mode body, with step metadata comments hidden.

        Returns
        -------
        str
            Raw Markdown body for most pages, or the step-stripped body for a
            project so comments are not shown as text.
        """
        page = self.page
        if page is None:
            return ""
        labels = page.labels
        if labels is not None and labels.note_type is NoteType.PROJECT:
            return afanes.core.steps.StepDocument(self.page_body).search_text
        return self.page_body

    @property
    def page_raw_text(self) -> str:
        """Return the current page's complete text.

        Returns
        -------
        str
            Raw rescue text, or the serialized normal draft, or an empty string
            when no page is open.
        """
        return "" if self.page is None else self.page.raw_text

    @property
    def page_is_dirty(self) -> bool:
        """Return whether the current page differs from its baseline.

        Returns
        -------
        bool
            ``True`` for a dirty draft; ``False`` when no page is open.
        """
        return self.page is not None and self.page.is_dirty

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
        root = self.session.vault_root
        if root is None:
            return page.path.as_posix()
        try:
            return page.path.relative_to(root).as_posix()
        except ValueError:
            return page.path.as_posix()

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
        self.status.clear_message()
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
        async with self.command_lock:
            if self.page is None:
                self.editing = False
                return False
            self.status.set_busy(busy=True)
            try:
                if not await self.commit():
                    return False
                self.editing = False
                await self.session.refresh_snapshot()
                return True
            finally:
                self.status.set_busy(busy=False)

    async def autosave(self, *, force: bool = False) -> bool:
        """Write a dirty draft when the page is in edit mode or forced.

        Parameters
        ----------
        force : bool
            Write a dirty draft even when edit mode is inactive. Read-mode
            metadata commands use this for a single atomic frontmatter write.

        Returns
        -------
        bool
            ``True`` when a write occurred.

        Notes
        -----
        Autosave is skipped when no page is open, the draft is clean, or a disk
        conflict is unresolved. Without ``force`` it is also skipped when edit
        mode is inactive.
        """
        async with self.command_lock:
            page = self.page
            if page is None or self.conflict is not None:
                return False
            if not force and not self.editing:
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
        async with self.command_lock:
            page = self.page
            if isinstance(page, NormalDraft):
                self.page = page.with_body(body)

    async def toggle_page_step(self, line_index: int, *, checked: bool) -> bool:
        """Check or reopen one step of the open project page.

        Parameters
        ----------
        line_index : int
            Zero-based body line of the step.
        checked : bool
            ``True`` to complete the step, ``False`` to reopen it.

        Returns
        -------
        bool
            ``True`` when the line was rewritten and the page reloaded.

        Notes
        -----
        Only the target line changes. The write is atomic and the scan is
        refreshed so the Projects workspace sees the new state.
        """
        async with self.command_lock:
            page = self.page
            vault = self.session.vault
            if page is None or page.path is None or vault is None:
                return False
            self.status.set_busy(busy=True)
            self.status.clear_message()
            try:
                try:
                    if checked:
                        await asyncio.to_thread(
                            afanes.core.vault.steps.VaultSteps(vault).tick_step,
                            page.path,
                            line_index,
                            datetime.datetime.now(tz=datetime.UTC).astimezone().date(),
                            confirm=True,
                        )
                    else:
                        await asyncio.to_thread(
                            afanes.core.vault.steps.VaultSteps(vault).untick_step, page.path, line_index, confirm=True
                        )
                except (AfanesError, OSError) as exc:
                    logger.debug("Step toggle failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_STEP_FAILED.format(detail=str(exc)))
                    return False
                if not await self.load(page.path):
                    return False
                await self.session.refresh_snapshot()
                return True
            finally:
                self.status.set_busy(busy=False)

    async def edit_page_step_metadata(self, edit: StepEdit) -> bool:
        """Change one step's plan date or owner list from the open page.

        Parameters
        ----------
        edit : StepEdit
            Step line and metadata field to change.

        Returns
        -------
        bool
            ``True`` when the line was rewritten and the page reloaded.

        Notes
        -----
        Only the target line changes. The write is atomic, the page is reloaded
        from disk, and the scan is refreshed so every workspace view sees the
        new metadata.
        """
        async with self.command_lock:
            page = self.page
            vault = self.session.vault
            if page is None or page.path is None or vault is None:
                return False
            self.status.set_busy(busy=True)
            self.status.clear_message()
            try:
                try:
                    if edit.kind is StepEditKind.PLAN:
                        await asyncio.to_thread(
                            afanes.core.vault.steps.VaultSteps(vault).plan_step,
                            page.path,
                            edit.line_index,
                            edit.plan,
                            confirm=True,
                        )
                    else:
                        await asyncio.to_thread(
                            afanes.core.vault.steps.VaultSteps(vault).set_step_owners,
                            page.path,
                            edit.line_index,
                            edit.owners,
                            confirm=True,
                        )
                except (AfanesError, OSError) as exc:
                    logger.debug("Step metadata edit failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.PAGE_STEP_FAILED.format(detail=str(exc)))
                    return False
                if not await self.load(page.path):
                    return False
                await self.session.refresh_snapshot()
                return True
            finally:
                self.status.set_busy(busy=False)

    async def set_page_raw_text(self, text: str) -> None:
        """Replace raw rescue text.

        Parameters
        ----------
        text : str
            Complete file text.
        """
        async with self.command_lock:
            page = self.page
            if isinstance(page, RawDraft):
                self.page = page.with_raw_text(text)

    async def commit(self) -> bool:
        """Write or discard the current draft before a page change."""
        page = self.page
        if page is None:
            return True
        if self.repair_preview is not None:
            self.status.show_message(afanes.ui.strings.PAGE_REPAIR_PENDING)
            return False
        if self.blocking_message is not None:
            self.status.show_message(self.blocking_message)
            return False
        if page.is_new and not page.is_dirty:
            self.clear()
            return True
        if self.conflict is not None:
            self.status.show_message(afanes.ui.strings.PAGE_CONFLICT_LEAVE)
            return False
        if not page.is_dirty:
            return True
        if not await self._save_page():
            return False
        if self.repair_preview is not None:
            self.status.show_message(afanes.ui.strings.PAGE_REPAIR_PENDING)
            return False
        return True

    async def _save_page(self) -> bool:
        """Write the current draft, creating a new page when needed."""
        page = self.page
        vault = self.session.vault
        if page is None or vault is None:
            return False
        if isinstance(page, RawDraft):
            return await self._save_raw_page(page, vault)

        labels = page.labels
        try:
            text = page.to_text()
        except NoteParseError as exc:
            self.status.show_message(str(exc))
            return False

        self.saving = True
        try:
            if page.is_new:
                return await self._create_new_page(page, labels, text, vault)

            path = page.path
            if path is None:
                self.status.show_message(afanes.ui.strings.PAGE_SAVE_FAILED.format(detail="The page has no path"))
                return False
            try:
                new_hash = await asyncio.to_thread(
                    afanes.core.vault.pages.VaultPages(vault).write_page, path, text, page.baseline_hash
                )
            except ContentChangedError:
                self.conflict = "changed"
                self.status.show_message(afanes.ui.strings.PAGE_CONFLICT_CHANGED)
                return False
            except VaultPathError:
                self.conflict = "missing"
                self.status.show_message(afanes.ui.strings.PAGE_CONFLICT_MISSING)
                return False
            except (AfanesError, OSError) as exc:
                logger.debug("Page save failed", exc_info=True)
                self.status.show_message(afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc)))
                return False
            self.page = page.after_write(text, content_hash=new_hash)
            self.status.clear_message()
            return True
        finally:
            self.saving = False

    async def _create_new_page(
        self,
        page: NormalDraft,
        labels: PageLabels,
        text: str,
        vault: Vault,
    ) -> bool:
        """Create the file for a new draft and adopt its path."""
        reference = page.reference
        name = reference.name if reference is not None else page.identity
        try:
            path = await asyncio.to_thread(
                afanes.core.vault.pages.VaultPages(vault).create_page,
                name,
                labels.note_type,
                labels.category,
                text=text,
            )
        except (AfanesError, OSError) as exc:
            logger.debug("New page could not be created", exc_info=True)
            self.status.show_message(afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc)))
            return False
        new_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        updated = page.after_write(text, content_hash=new_hash, path=path)
        self.page = updated
        await self._plan_repair_after_create(updated, vault)
        return True

    async def _save_raw_page(self, page: RawDraft, vault: Vault) -> bool:
        """Write raw rescue text with the conflict guard."""
        path = page.path
        if path is None:
            return False
        self.saving = True
        try:
            try:
                new_hash = await asyncio.to_thread(
                    afanes.core.vault.pages.VaultPages(vault).write_page, path, page.raw_text, page.baseline_hash
                )
            except ContentChangedError:
                self.conflict = "changed"
                self.status.show_message(afanes.ui.strings.PAGE_CONFLICT_CHANGED)
                return False
            except VaultPathError:
                self.conflict = "missing"
                self.status.show_message(afanes.ui.strings.PAGE_CONFLICT_MISSING)
                return False
            except (AfanesError, OSError) as exc:
                logger.debug("Raw page save failed", exc_info=True)
                self.status.show_message(afanes.ui.strings.PAGE_SAVE_FAILED.format(detail=str(exc)))
                return False
            updated = page.after_write(page.raw_text, content_hash=new_hash)
            self.page = updated
            if updated.mode is DraftMode.NORMAL:
                self.status.show_message(afanes.ui.strings.PAGE_RAW_UPGRADED)
            else:
                self.status.clear_message()
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
            self.status.show_message(afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc)))
            return
        self.session.apply_snapshot(snapshot)
        await self._plan_repair(reference, snapshot, vault)

    async def offer_repair(self, reference: NoteReference) -> None:
        """Offer a repair for an unsafe reference that opened an existing page."""
        vault = self.session.vault
        if vault is None:
            return
        try:
            snapshot = await asyncio.to_thread(vault.scan)
        except (VaultError, OSError) as exc:
            logger.debug("Snapshot refresh before a reference repair failed", exc_info=True)
            self.status.show_message(afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc)))
            return
        self.session.apply_snapshot(snapshot)
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
            preview = await asyncio.to_thread(
                afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair, reference, new, snapshot=snapshot
            )
        except (AfanesError, OSError) as exc:
            logger.debug("Reference repair could not be planned", exc_info=True)
            self.status.show_message(afanes.ui.strings.PAGE_REPAIR_FAILED.format(detail=str(exc)))
            return
        if preview.sites:
            self.repair_preview = preview

    async def load(self, path: Path, *, editing: bool = False) -> bool:
        """Read a note into the page pane.

        Parameters
        ----------
        path : Path
            Note path, relative or absolute, inside the active vault.
        editing : bool
            Whether to open the page in edit mode. Raw rescue drafts always open
            in edit mode because their text must be repaired directly.

        Returns
        -------
        bool
            ``True`` when the page was read and shown.

        Notes
        -----
        A failed read keeps the previous page and reports a message. Blocking
        file I/O runs in a worker thread.
        """
        vault = self.session.vault
        if vault is None:
            return False
        try:
            content = await asyncio.to_thread(vault.read_page, path)
            draft = PageDraftFactory.from_page(content)
        except (AfanesError, OSError, UnicodeError) as exc:
            logger.debug("Page could not be read", exc_info=True)
            self.status.show_message(afanes.ui.strings.PAGE_OPEN_FAILED.format(detail=str(exc)))
            return False
        self.page = draft
        self.editing = editing or draft.mode is DraftMode.RAW
        self.conflict = None
        self.status.clear_message()
        return True

    def start_autosave(self) -> None:
        """Start the single autosave loop when it is not already running."""
        if self.autosave_task is None or self.autosave_task.done():
            self.autosave_task = asyncio.create_task(self._autosave_loop())

    async def _autosave_loop(self) -> None:
        """Write a dirty draft roughly every :data:`AUTOSAVE_SECONDS`."""
        while True:
            await asyncio.sleep(AUTOSAVE_SECONDS)
            await self.autosave()

    def clear(self) -> None:
        """Clear the page and its conflict state."""
        self.page = None
        self.editing = False
        self.conflict = None
        self.saving = False

    def start_new(self, reference: NoteReference) -> None:
        """Open an unwritten draft for a missing reference.

        Parameters
        ----------
        reference : NoteReference
            Reference the new page will satisfy.
        """
        self.page = NormalDraft.new(reference)
        self.editing = True
        self.conflict = None

    def reset(self) -> None:
        """Return the editor to its initial state."""
        if self.autosave_task is not None:
            self.autosave_task.cancel()
            self.autosave_task = None
        self.page = None
        self.editing = False
        self.conflict = None
        self.saving = False
        self.blocking_message = None
        self.repair_preview = None
