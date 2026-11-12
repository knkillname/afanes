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
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Self

import afanes.core.editing
import afanes.core.links
import afanes.core.names
import afanes.core.search
import afanes.core.steps
import afanes.core.templates
import afanes.ui.strings
from afanes.core.editing import DraftMode, NormalDraft, PageDraft, PageDraftFactory, PageLabels, RawDraft
from afanes.core.errors import (
    AfanesError,
    ConfigurationError,
    ContentChangedError,
    EmptyCaptureError,
    InvalidReferenceError,
    NoteParseError,
    TemplateError,
    VaultError,
    VaultMissingError,
    VaultNotDirectoryError,
    VaultNotEmptyError,
    VaultPathError,
    VaultUnreadableError,
)
from afanes.core.links import DestinationKind, ReferenceParser
from afanes.core.processing import AppendStepPlan, ProcessingOutcome, ProcessingPlan
from afanes.core.search import (
    BrowserListing,
    BrowserSection,
    ProjectGroup,
    ProjectSummary,
    ReviewItem,
    ReviewItemKind,
)
from afanes.core.settings import Settings, SettingsStore
from afanes.core.templates import TemplateSummary
from afanes.core.vault import (
    CategoryMovePreview,
    LinkOutcome,
    ReferenceRepairPreview,
    ReferenceSite,
    RenamePreview,
    TrashPreview,
    Vault,
    VaultCreation,
    VaultFailure,
    VaultNote,
    VaultPath,
    VaultSnapshot,
)
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteType, Status
from afanes.models.step import ProjectStep

logger = logging.getLogger(__name__)

PAGE_HISTORY_LIMIT = 50
AUTOSAVE_SECONDS = 30


class VaultOpener:
    """Translate vault path failures into interface messages.

    Notes
    -----
    This is the interface's translation point for the folder picker, the typed
    path field, the creation action, and the command-line vault option. All
    filesystem validation lives in :class:`afanes.core.vault.Vault`; this class
    only maps domain errors to user-facing copy.
    """

    @staticmethod
    def open(path: Path) -> Vault:
        """Open and validate a vault directory.

        Parameters
        ----------
        path : pathlib.Path
            Candidate vault directory. A relative path is resolved by
            :class:`afanes.core.vault.Vault`.

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
        try:
            return Vault.open(path)
        except VaultMissingError as exc:
            raise VaultError(afanes.ui.strings.VAULT_MISSING) from exc
        except VaultNotDirectoryError as exc:
            raise VaultError(afanes.ui.strings.VAULT_NOT_DIRECTORY) from exc
        except VaultUnreadableError as exc:
            raise VaultError(afanes.ui.strings.VAULT_UNREADABLE) from exc

    @staticmethod
    def create(path: Path, *, template: str | None = None) -> VaultCreation:
        """Create a new vault and translate refusals into interface messages.

        Parameters
        ----------
        path : pathlib.Path
            Directory to create or seed. It must be missing or empty.
        template : str | None
            Bundled template identifier, or ``None`` to write only the guide
            note.

        Returns
        -------
        VaultCreation
            Created vault, the intermediate directories made for it, the
            default folders created inside it, and the notes written into it.

        Raises
        ------
        VaultError
            If the path is not a directory, is not empty, cannot be created, or
            the bundled starter content cannot be written.
        """
        try:
            return Vault.create_directory(path, template=template)
        except TemplateError as exc:
            raise VaultError(afanes.ui.strings.NEW_VAULT_TEMPLATE_FAILED.format(detail=exc)) from exc
        except VaultNotEmptyError as exc:
            raise VaultError(afanes.ui.strings.VAULT_NOT_EMPTY) from exc
        except VaultNotDirectoryError as exc:
            raise VaultError(afanes.ui.strings.VAULT_NOT_DIRECTORY) from exc
        except VaultMissingError as exc:
            raise VaultError(afanes.ui.strings.VAULT_MISSING) from exc
        except VaultUnreadableError as exc:
            raise VaultError(afanes.ui.strings.VAULT_UNREADABLE) from exc


class WorkspaceSection(StrEnum):
    """Top-level destinations in the workspace sidebar.

    Attributes
    ----------
    REVIEW : str
        Guided review of pending captures, steps, and projects.
    INBOX : str
        Captures stored under the inbox directory.
    PROJECTS : str
        Project notes grouped by status.
    REFERENCES : str
        Reference notes grouped by category label.
    NEEDS_ATTENTION : str
        Unclarified notes found outside the inbox.
    """

    REVIEW = "review"
    INBOX = "inbox"
    PROJECTS = "projects"
    REFERENCES = "references"
    NEEDS_ATTENTION = "needs_attention"

    @property
    def browser_section(self) -> BrowserSection | None:
        """Return the matching browser section, or ``None`` for Review.

        Returns
        -------
        BrowserSection | None
            Section used to select browser entries. Review has no browser
            section because it changes the main workspace area.
        """
        if self is WorkspaceSection.REVIEW:
            return None
        return BrowserSection(self.value)


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewSession:
    """Snapshot queue and progress for one guided review.

    Attributes
    ----------
    items : tuple[ReviewItem, ...]
        Queue captured when the session started.
    index : int
        Position of the current item in :attr:`items`.
    reviewed : tuple[Path, ...]
        Paths the user reviewed, in order.
    skipped : tuple[Path, ...]
        Paths the user skipped, in order.
    """

    items: tuple[ReviewItem, ...]
    index: int = 0
    reviewed: tuple[Path, ...] = ()
    skipped: tuple[Path, ...] = ()

    @property
    def current(self) -> ReviewItem | None:
        """Return the current item, or ``None`` when the queue is complete.

        Returns
        -------
        ReviewItem | None
            Item at :attr:`index`, or ``None`` past the end of the queue.
        """
        if 0 <= self.index < len(self.items):
            return self.items[self.index]
        return None

    @property
    def complete(self) -> bool:
        """Return whether every queued item has been passed.

        Returns
        -------
        bool
            ``True`` when :attr:`index` is at or past the end of the queue.
        """
        return self.index >= len(self.items)

    @property
    def reviewed_count(self) -> int:
        """Return the number of reviewed items.

        Returns
        -------
        int
            Length of :attr:`reviewed`.
        """
        return len(self.reviewed)

    @property
    def skipped_count(self) -> int:
        """Return the number of skipped items.

        Returns
        -------
        int
            Length of :attr:`skipped`.
        """
        return len(self.skipped)

    def record_reviewed(self) -> Self:
        """Mark the current item reviewed and advance.

        Returns
        -------
        ReviewSession
            New session with the current path recorded and the index advanced.
            The original is unchanged. A complete session is returned as is.
        """
        item = self.current
        if item is None:
            return self
        return dataclasses.replace(
            self,
            index=self.index + 1,
            reviewed=(*self.reviewed, item.path),
        )

    def record_skipped(self) -> Self:
        """Mark the current item skipped and advance.

        Returns
        -------
        ReviewSession
            New session with the current path recorded as skipped and the
            index advanced. The original is unchanged.
        """
        item = self.current
        if item is None:
            return self
        return dataclasses.replace(
            self,
            index=self.index + 1,
            skipped=(*self.skipped, item.path),
        )

    def replace_current_project(self, summary: ProjectSummary) -> Self:
        """Replace the current project item with a refreshed summary.

        Parameters
        ----------
        summary : ProjectSummary
            Refreshed summary for the project at the current position.

        Returns
        -------
        ReviewSession
            New session whose current item carries ``summary``. The original is
            unchanged. A non-project or complete session is returned as is.
        """
        item = self.current
        if item is None or item.kind is not ReviewItemKind.PROJECT:
            return self
        replacement = ReviewItem(kind=item.kind, path=item.path, project=summary)
        items = list(self.items)
        items[self.index] = replacement
        return dataclasses.replace(self, items=tuple(items))


@dataclasses.dataclass(slots=True)
class UiStatus:
    """Cross-cutting status flags shared by the application collaborators.

    Attributes
    ----------
    message : str | None
        Banner text for the current error or warning.
    busy : bool
        Whether a blocking command is in progress.
    session_active : bool
        Whether a presentation session currently drives the workspace.
    """

    message: str | None = None
    busy: bool = False
    session_active: bool = False


@dataclasses.dataclass(slots=True)
class VaultSession:
    """Vault lifecycle, scan snapshot, and selection state.

    Attributes
    ----------
    status : UiStatus
        Shared banner and busy flags.
    vault : Vault | None
        Active vault service, or ``None`` while the welcome state is shown.
    snapshot : VaultSnapshot | None
        Latest scan result.
    notes : tuple[VaultNote, ...]
        Inbox notes, newest first.
    failures : tuple[VaultFailure, ...]
        Notes the last scan could not parse.
    selected : Path | None
        Absolute path of the note shown in the preview.
    preview_body : str | None
        Markdown body of the previewed note, without frontmatter.
    """

    status: UiStatus
    vault: Vault | None = None
    snapshot: VaultSnapshot | None = None
    notes: tuple[VaultNote, ...] = ()
    failures: tuple[VaultFailure, ...] = ()
    selected: Path | None = None
    preview_body: str | None = None

    @property
    def vault_root(self) -> Path | None:
        """Return the active vault root, or ``None`` in the welcome state.

        Returns
        -------
        Path | None
            Resolved root of :attr:`vault`, or ``None`` when no vault is open.
        """
        return None if self.vault is None else self.vault.root

    def begin_session(self) -> bool:
        """Claim the single active workspace session.

        Returns
        -------
        bool
            ``True`` when this caller became the active session.
        """
        if self.status.session_active:
            return False
        self.status.session_active = True
        return True

    def release_session(self) -> None:
        """Release the active workspace session."""
        self.status.session_active = False

    def note_title(self, path: Path) -> str:
        """Return the display title for a note in the latest scan.

        Parameters
        ----------
        path : Path
            Absolute path of a note in the vault.

        Returns
        -------
        str
            Display title, or the filename stem when the note is not in the
            latest scan.
        """
        if self.snapshot is not None:
            note = next((note for note in self.snapshot.notes if note.path == path), None)
            if note is not None:
                return note.title
        note = next((note for note in self.notes if note.path == path), None)
        return path.stem if note is None else note.title

    def assignment_candidates(self, scheme: ReferenceScheme, query: str) -> tuple[VaultNote, ...]:
        """Return assignment suggestions from the last vault scan.

        Parameters
        ----------
        scheme : ReferenceScheme
            Namespace to search, normally ``person`` or ``project``.
        query : str
            Free text typed by the user.

        Returns
        -------
        tuple[VaultNote, ...]
            Matching notes ordered by display title, then identity, or an
            empty tuple when no vault is open.
        """
        if self.snapshot is None:
            return ()
        return self.snapshot.assignment_candidates(scheme, query)

    async def refresh_snapshot(self) -> None:
        """Rescan the vault and update the inbox lists."""
        vault = self.vault
        if vault is None:
            return
        try:
            snapshot = await asyncio.to_thread(vault.scan)
        except (VaultError, OSError) as exc:
            logger.debug("Snapshot refresh failed", exc_info=True)
            self.status.message = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
            return
        self.apply_snapshot(snapshot)

    def apply_snapshot(self, snapshot: VaultSnapshot, focus: Path | None = None) -> None:
        """Replace the inbox list from a scan result.

        Parameters
        ----------
        snapshot : VaultSnapshot
            Scan result to retain.
        focus : Path | None
            Note to promote to the top of the inbox list.
        """
        self.snapshot = snapshot
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
        self.status.message = None


@dataclasses.dataclass(slots=True)
class BrowserState:
    """Sidebar destination and browser query.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the scan snapshot.
    active_section : WorkspaceSection
        Sidebar destination currently shown.
    query : str
        Title and identity filter typed into the browser search field.
    """

    session: VaultSession
    active_section: WorkspaceSection = WorkspaceSection.INBOX
    query: str = ""

    def set_section(self, section: WorkspaceSection) -> None:
        """Select one workspace sidebar destination.

        Parameters
        ----------
        section : WorkspaceSection
            Destination to show.
        """
        self.active_section = section
        self.session.status.message = None

    def set_query(self, query: str) -> None:
        """Filter browser entries by display title or identity.

        Parameters
        ----------
        query : str
            Text typed into the search field.
        """
        self.query = query
        self.session.status.message = None

    def listing(self) -> BrowserListing | None:
        """Return the current browser groups after applying the query.

        Returns
        -------
        BrowserListing | None
            Grouped notes from the latest scan, or ``None`` when no vault is
            open.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return None
        return afanes.core.search.Browser(snapshot).filter(self.query)

    def project_groups(self) -> tuple[ProjectGroup, ...]:
        """Return project summaries grouped by presentation stage.

        Returns
        -------
        tuple[ProjectGroup, ...]
            Active, Waiting, Later, and Closed groups, or an empty tuple when
            no vault is open.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return ()
        return afanes.core.search.ProjectBoard(snapshot).groups()

    def pending_count(self) -> int:
        """Return the number of items that need review attention.

        Returns
        -------
        int
            Pending inbox captures plus open projects without an open action.
            Zero when no vault is open.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return 0
        return afanes.core.search.ReviewPlanner(snapshot).pending_count()


@dataclasses.dataclass(slots=True)
class PageEditorState:
    """Page draft, editing mode, history, and pending page dialogs.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the scan snapshot.
    status : UiStatus
        Shared banner and busy flags.
    page : PageDraft | None
        Page currently open in the right pane.
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
    category_move : CategoryMovePreview | None
        Category move waiting for confirmation.
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
    autosave_task : asyncio.Task[None] | None
        Single background autosave loop, when started.
    """

    session: VaultSession
    status: UiStatus
    page: PageDraft | None = None
    editing: bool = False
    history: tuple[Path, ...] = ()
    conflict: str | None = None
    ambiguous: tuple[Path, ...] = ()
    pending_labels: PageLabels | None = None
    category_move: CategoryMovePreview | None = None
    type_change_sites: tuple[ReferenceSite, ...] = ()
    repair_preview: ReferenceRepairPreview | None = None
    rename_preview: RenamePreview | None = None
    trash_preview: TrashPreview | None = None
    saving: bool = False
    autosave_task: asyncio.Task[None] | None = None


@dataclasses.dataclass(slots=True)
class ProcessingState:
    """Processing Wizard session for one capture.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the active vault and snapshot.
    status : UiStatus
        Shared banner and busy flags.
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
    note: Path | None = None
    body: str | None = None
    plan: ProcessingPlan | AppendStepPlan | None = None
    result: Path | None = None


@dataclasses.dataclass(slots=True)
class ReviewState:
    """Guided review session and queue navigation.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the active vault and snapshot.
    browser : BrowserState
        Sidebar destination state.
    processing : ProcessingState
        Processing state used to load the current capture.
    pages : PageEditorState
        Page state used when a review opens a note.
    status : UiStatus
        Shared banner and busy flags.
    review_session : ReviewSession | None
        Guided review session in progress, or ``None``.
    """

    session: VaultSession
    browser: BrowserState
    processing: ProcessingState
    pages: PageEditorState
    status: UiStatus
    review_session: ReviewSession | None = None


@dataclasses.dataclass(slots=True, eq=False)
class AppState:
    """Single mutable controller exposed to the presentation layer.

    The controller owns five collaborators, the shared command lock, and the
    cross-cutting status flags. Views use the module-level
    :data:`app_state` instance and call its command methods; they never mutate
    collaborator fields directly.

    Attributes
    ----------
    _status : UiStatus
        Shared message, busy, and session flags.
    _lock : asyncio.Lock
        Lock that serializes commands.
    _vault_session : VaultSession
        Vault lifecycle, snapshot, and selection state.
    _browser : BrowserState
        Sidebar destination and browser query.
    _pages : PageEditorState
        Page draft, editing mode, and page dialogs.
    _processing : ProcessingState
        Processing Wizard session.
    _review : ReviewState
        Guided review session.
    """

    _status: UiStatus = dataclasses.field(default_factory=UiStatus)
    _lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock, repr=False)
    _vault_session: VaultSession = dataclasses.field(init=False)
    _browser: BrowserState = dataclasses.field(init=False)
    _pages: PageEditorState = dataclasses.field(init=False)
    _processing: ProcessingState = dataclasses.field(init=False)
    _review: ReviewState = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        """Create the collaborators and wire their shared state."""
        self._vault_session = VaultSession(self._status)
        self._browser = BrowserState(self._vault_session)
        self._pages = PageEditorState(self._vault_session, self._status)
        self._processing = ProcessingState(self._vault_session, self._status)
        self._review = ReviewState(
            self._vault_session,
            self._browser,
            self._processing,
            self._pages,
            self._status,
        )

    @property
    def vault(self) -> Vault | None:
        """Return the active vault service, or ``None`` in the welcome state."""
        return self._vault_session.vault

    @vault.setter
    def vault(self, value: Vault | None) -> None:
        self._vault_session.vault = value

    @property
    def notes(self) -> tuple[VaultNote, ...]:
        """Return inbox notes, newest first."""
        return self._vault_session.notes

    @notes.setter
    def notes(self, value: tuple[VaultNote, ...]) -> None:
        self._vault_session.notes = value

    @property
    def failures(self) -> tuple[VaultFailure, ...]:
        """Return notes the last scan could not parse."""
        return self._vault_session.failures

    @failures.setter
    def failures(self, value: tuple[VaultFailure, ...]) -> None:
        self._vault_session.failures = value

    @property
    def selected(self) -> Path | None:
        """Return the absolute path of the previewed note."""
        return self._vault_session.selected

    @selected.setter
    def selected(self, value: Path | None) -> None:
        self._vault_session.selected = value

    @property
    def preview_body(self) -> str | None:
        """Return the Markdown body of the previewed note."""
        return self._vault_session.preview_body

    @preview_body.setter
    def preview_body(self, value: str | None) -> None:
        self._vault_session.preview_body = value

    @property
    def _snapshot(self) -> VaultSnapshot | None:
        """Return the latest scan result."""
        return self._vault_session.snapshot

    @_snapshot.setter
    def _snapshot(self, value: VaultSnapshot | None) -> None:
        self._vault_session.snapshot = value

    @property
    def active_section(self) -> WorkspaceSection:
        """Return the sidebar destination currently shown."""
        return self._browser.active_section

    @active_section.setter
    def active_section(self, value: WorkspaceSection) -> None:
        self._browser.active_section = value

    @property
    def browser_query(self) -> str:
        """Return the browser search text."""
        return self._browser.query

    @browser_query.setter
    def browser_query(self, value: str) -> None:
        self._browser.query = value

    @property
    def review_session(self) -> ReviewSession | None:
        """Return the guided review session in progress."""
        return self._review.review_session

    @review_session.setter
    def review_session(self, value: ReviewSession | None) -> None:
        self._review.review_session = value

    @property
    def page(self) -> PageDraft | None:
        """Return the page currently open in the right pane."""
        return self._pages.page

    @page.setter
    def page(self, value: PageDraft | None) -> None:
        self._pages.page = value

    @property
    def editing(self) -> bool:
        """Return whether the page is in edit mode."""
        return self._pages.editing

    @editing.setter
    def editing(self, value: bool) -> None:
        self._pages.editing = value

    @property
    def history(self) -> tuple[Path, ...]:
        """Return page paths behind the current page."""
        return self._pages.history

    @history.setter
    def history(self, value: tuple[Path, ...]) -> None:
        self._pages.history = value

    @property
    def conflict(self) -> str | None:
        """Return the disk conflict state."""
        return self._pages.conflict

    @conflict.setter
    def conflict(self, value: str | None) -> None:
        self._pages.conflict = value

    @property
    def ambiguous(self) -> tuple[Path, ...]:
        """Return candidate paths waiting for the user."""
        return self._pages.ambiguous

    @ambiguous.setter
    def ambiguous(self, value: tuple[Path, ...]) -> None:
        self._pages.ambiguous = value

    @property
    def pending_labels(self) -> PageLabels | None:
        """Return labels waiting for a scheme-change confirmation."""
        return self._pages.pending_labels

    @pending_labels.setter
    def pending_labels(self, value: PageLabels | None) -> None:
        self._pages.pending_labels = value

    @property
    def type_change_sites(self) -> tuple[ReferenceSite, ...]:
        """Return references a pending type change would strand."""
        return self._pages.type_change_sites

    @type_change_sites.setter
    def type_change_sites(self, value: tuple[ReferenceSite, ...]) -> None:
        self._pages.type_change_sites = value

    @property
    def category_move(self) -> CategoryMovePreview | None:
        """Return the category move waiting for confirmation."""
        return self._pages.category_move

    @category_move.setter
    def category_move(self, value: CategoryMovePreview | None) -> None:
        self._pages.category_move = value

    @property
    def repair_preview(self) -> ReferenceRepairPreview | None:
        """Return the unsafe-name repair waiting for an action."""
        return self._pages.repair_preview

    @repair_preview.setter
    def repair_preview(self, value: ReferenceRepairPreview | None) -> None:
        self._pages.repair_preview = value

    @property
    def rename_preview(self) -> RenamePreview | None:
        """Return the rename preview waiting for confirmation."""
        return self._pages.rename_preview

    @rename_preview.setter
    def rename_preview(self, value: RenamePreview | None) -> None:
        self._pages.rename_preview = value

    @property
    def trash_preview(self) -> TrashPreview | None:
        """Return the trash preview waiting for confirmation."""
        return self._pages.trash_preview

    @trash_preview.setter
    def trash_preview(self, value: TrashPreview | None) -> None:
        self._pages.trash_preview = value

    @property
    def saving(self) -> bool:
        """Return whether a page write is in progress."""
        return self._pages.saving

    @saving.setter
    def saving(self, value: bool) -> None:
        self._pages.saving = value

    @property
    def _autosave_task(self) -> asyncio.Task[None] | None:
        """Return the single background autosave loop."""
        return self._pages.autosave_task

    @_autosave_task.setter
    def _autosave_task(self, value: asyncio.Task[None] | None) -> None:
        self._pages.autosave_task = value

    @property
    def processing_note(self) -> Path | None:
        """Return the capture currently open in the wizard."""
        return self._processing.note

    @processing_note.setter
    def processing_note(self, value: Path | None) -> None:
        self._processing.note = value

    @property
    def processing_body(self) -> str | None:
        """Return the Markdown body of the processing capture."""
        return self._processing.body

    @processing_body.setter
    def processing_body(self, value: str | None) -> None:
        self._processing.body = value

    @property
    def processing_plan(self) -> ProcessingPlan | AppendStepPlan | None:
        """Return the validated plan waiting for confirmation."""
        return self._processing.plan

    @processing_plan.setter
    def processing_plan(self, value: ProcessingPlan | AppendStepPlan | None) -> None:
        self._processing.plan = value

    @property
    def processing_result(self) -> Path | None:
        """Return the destination of the last successful apply."""
        return self._processing.result

    @processing_result.setter
    def processing_result(self, value: Path | None) -> None:
        self._processing.result = value

    @property
    def message(self) -> str | None:
        """Return the banner text for the current error or warning."""
        return self._status.message

    @message.setter
    def message(self, value: str | None) -> None:
        self._status.message = value

    @property
    def busy(self) -> bool:
        """Return whether a blocking command is in progress."""
        return self._status.busy

    @busy.setter
    def busy(self, value: bool) -> None:
        self._status.busy = value

    @property
    def session_active(self) -> bool:
        """Return whether a presentation session drives the workspace."""
        return self._status.session_active

    @session_active.setter
    def session_active(self, value: bool) -> None:
        self._status.session_active = value

    @property
    def vault_root(self) -> Path | None:
        """Return the active vault root, or ``None`` in the welcome state.

        Returns
        -------
        Path | None
            Resolved root of :attr:`vault`, or ``None`` when no vault is open.
        """
        return self._vault_session.vault_root

    @property
    def browser_listing(self) -> BrowserListing | None:
        """Return the current browser groups after applying the search query.

        Returns
        -------
        BrowserListing | None
            Grouped notes from the latest scan, filtered by
            :attr:`browser_query`, or ``None`` when no vault is open.

        Notes
        -----
        This property is pure in-memory work. It never reads a note body and
        never changes the vault.
        """
        snapshot = self._snapshot
        if snapshot is None:
            return None
        return self._browser.listing()

    @property
    def project_groups(self) -> tuple[ProjectGroup, ...]:
        """Return project summaries grouped by presentation stage.

        Returns
        -------
        tuple[ProjectGroup, ...]
            Active, Waiting, Later, and Closed groups, or an empty tuple when
            no vault is open.

        Notes
        -----
        This property is pure in-memory work over the latest scan.
        """
        snapshot = self._snapshot
        if snapshot is None:
            return ()
        return self._browser.project_groups()

    @property
    def review_pending_count(self) -> int:
        """Return the number of items that need review attention.

        Returns
        -------
        int
            Pending inbox captures plus open projects without an open action.
            Zero when no vault is open.
        """
        snapshot = self._snapshot
        if snapshot is None:
            return 0
        return self._browser.pending_count()

    @property
    def review_due_count(self) -> int:
        """Return the number of due or overdue own steps.

        Returns
        -------
        int
            Due own steps from the latest scan. Zero when no vault is open.

        Notes
        -----
        This property is pure in-memory work over the latest scan. It never
        writes to the vault.
        """
        snapshot = self._snapshot
        if snapshot is None:
            return 0
        return afanes.core.search.ReviewPlanner(snapshot).due_count()

    async def set_section(self, section: WorkspaceSection) -> None:
        """Select one workspace sidebar destination.

        Parameters
        ----------
        section : WorkspaceSection
            Destination to show.

        Notes
        -----
        Switching sections performs no vault write and leaves the open page in
        the page pane.
        """
        async with self._lock:
            self._browser.set_section(section)

    async def set_browser_query(self, query: str) -> None:
        """Filter browser entries by display title or identity.

        Parameters
        ----------
        query : str
            Text typed into the search field. An empty value keeps every note.

        Notes
        -----
        This command performs no file I/O and never reads a note body.
        """
        async with self._lock:
            self._browser.set_query(query)

    async def start_review(self) -> bool:
        """Start a guided review from the latest vault scan.

        Returns
        -------
        bool
            ``True`` when a session with at least one item started.

        Notes
        -----
        The queue is a snapshot: pending inbox captures first, then open
        projects without a next action, then healthy open projects. Work
        created during the session waits for the next session. A zero queue
        opens the Review destination without creating a session. Blocking
        reads run in a worker thread.
        """
        async with self._lock:
            snapshot = self._snapshot
            if snapshot is None:
                return False
            queue = afanes.core.search.ReviewPlanner(snapshot).queue()
            self.review_session = ReviewSession(items=queue) if queue else None
            self.active_section = WorkspaceSection.REVIEW
            self.message = None
            self._clear_processing()
            if not queue:
                return False
            await self._enter_current_review_item()
            return True

    async def review_next(self) -> bool:
        """Mark the current project reviewed and show the next item.

        Returns
        -------
        bool
            ``True`` when the session advanced. Inbox items cannot be advanced
            with this command; they require a processing outcome or Skip.
        """
        async with self._lock:
            session = self.review_session
            if session is None or session.current is None or session.current.kind is not ReviewItemKind.PROJECT:
                return False
            self.review_session = session.record_reviewed()
            self.message = None
            await self._enter_current_review_item()
            return True

    async def review_skip(self) -> bool:
        """Skip the current item without changing it.

        Returns
        -------
        bool
            ``True`` when an item was skipped and the session advanced.
        """
        async with self._lock:
            session = self.review_session
            if session is None or session.current is None:
                return False
            self.review_session = session.record_skipped()
            self.message = None
            await self._enter_current_review_item()
            return True

    async def add_review_step(self, text: str) -> Path | None:
        """Append the next step to the current stalled project.

        Parameters
        ----------
        text : str
            Step text typed into the review card. Whitespace-only input is
            rejected without writing.

        Returns
        -------
        Path | None
            Absolute path of the project that gained the step, or ``None``
            when nothing was written.

        Notes
        -----
        Only the project body changes. The refreshed summary is applied to the
        current item so the card shows the new next step. Blocking writes and
        scans run in a worker thread.
        """
        async with self._lock:
            item = self._current_review_project()
            vault = self.vault
            if item is None or vault is None or not text.strip():
                return None
            self.busy = True
            self.message = None
            try:
                try:
                    await asyncio.to_thread(vault.append_step, item.path, text, confirm=True)
                except (AfanesError, OSError) as exc:
                    logger.debug("Review step creation failed", exc_info=True)
                    self.message = afanes.ui.strings.REVIEW_STEP_FAILED.format(detail=str(exc))
                    return None
                await self._refresh_snapshot()
                self._replace_review_project(item.path)
                return item.path
            finally:
                self.busy = False

    async def review_do_now(self) -> bool:
        """Complete the current due step and record today as its actual date.

        Returns
        -------
        bool
            ``True`` when the step was written and the session advanced.
        """
        item = self._current_review_step()
        if item is None or item.step is None:
            return False
        return await self._update_review_step(
            lambda vault: vault.tick_step(
                item.path,
                item.step.line_index,
                datetime.datetime.now(tz=datetime.UTC).astimezone().date(),
                confirm=True,
            ),
        )

    async def review_postpone(self, plan: datetime.date) -> bool:
        """Postpone the current due step to a later plan date.

        Parameters
        ----------
        plan : datetime.date
            New calendar plan date.

        Returns
        -------
        bool
            ``True`` when the step was written and the session advanced.
        """
        item = self._current_review_step()
        if item is None or item.step is None:
            return False
        return await self._update_review_step(
            lambda vault: vault.plan_step(item.path, item.step.line_index, plan, confirm=True),
        )

    async def review_delegate(self, owner: str) -> bool:
        """Add an owner to the current due step, moving it to waiting.

        Parameters
        ----------
        owner : str
            Owner name. Whitespace-only input is rejected without writing.

        Returns
        -------
        bool
            ``True`` when the step was written and the session advanced.
        """
        item = self._current_review_step()
        if item is None or item.step is None or not owner.strip():
            return False
        owners = (*item.step.owners, owner.strip())
        return await self._update_review_step(
            lambda vault: vault.set_step_owners(item.path, item.step.line_index, owners, confirm=True),
        )

    async def review_reassign(self, owner: str) -> bool:
        """Replace the owners of the current waiting step.

        Parameters
        ----------
        owner : str
            New owner name. Whitespace-only input is rejected without writing.

        Returns
        -------
        bool
            ``True`` when the step was written and the session advanced.
        """
        item = self._current_review_step()
        if item is None or item.step is None or not owner.strip():
            return False
        return await self._update_review_step(
            lambda vault: vault.set_step_owners(
                item.path,
                item.step.line_index,
                (owner.strip(),),
                confirm=True,
            ),
        )

    async def review_open_project(self) -> bool:
        """Open the project page for the current review item.

        Returns
        -------
        bool
            ``True`` when the project page was loaded.
        """
        item = self._current_review_step() or self._current_review_project()
        if item is None:
            return False
        if not await self.open_page(item.path):
            return False
        await self.set_section(WorkspaceSection.PROJECTS)
        return True

    async def mark_review_project_done(self) -> bool:
        """Mark the current review project ``done`` after confirmation.

        Returns
        -------
        bool
            ``True`` when the status changed and the session advanced.
        """
        return await self._set_review_project_status(Status.DONE)

    async def defer_review_project(self) -> bool:
        """Defer the current review project to ``later`` after confirmation.

        Returns
        -------
        bool
            ``True`` when the status changed and the session advanced.
        """
        return await self._set_review_project_status(Status.LATER)

    async def finish_review(self) -> None:
        """Close the review session and return to the browser."""
        async with self._lock:
            self.review_session = None
            self.active_section = WorkspaceSection.INBOX
            self._clear_processing()
            self.message = None

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
                    vault = await asyncio.to_thread(VaultOpener.open, settings.vault)
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Saved vault could not be opened", exc_info=True)
                    self._show_welcome(str(exc))
                    return
                self.vault = vault
                self._clear_processing()
                self.active_section = WorkspaceSection.INBOX
                self.browser_query = ""
                self.review_session = None
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
            await self._open_vault_state(path, remember=True)

    async def open_vault_path(self, text: str) -> None:
        """Open a vault from a path typed by the user.

        Parameters
        ----------
        text : str
            Path typed into the welcome state or the change-vault dialog.
            Leading and trailing whitespace is ignored. Blank input is
            rejected before any filesystem access.

        Notes
        -----
        Delegates to :meth:`choose_vault`, so resolution, validation, and
        settings persistence are shared with the folder picker. A rejected
        path leaves the controller in its previous state and sets
        :attr:`message`.
        """
        trimmed = text.strip()
        if not trimmed:
            self.message = afanes.ui.strings.VAULT_PATH_REQUIRED
            return
        await self.choose_vault(Path(trimmed))

    async def open_vault_for_run(self, path: Path) -> None:
        """Open a vault for this run without replacing remembered settings.

        Parameters
        ----------
        path : Path
            Vault directory supplied when the process started.

        Notes
        -----
        The vault is validated, scanned, and shown exactly as
        :meth:`choose_vault` would, but the settings file is not written, so
        the remembered vault survives the run. Blocking file I/O runs in a
        worker thread.
        """
        self._start_autosave()
        async with self._lock:
            await self._open_vault_state(path, remember=False)

    async def _open_vault_state(self, path: Path, *, remember: bool) -> None:
        """Open a vault while the command lock is held."""
        if not await self._commit_current():
            return
        self.busy = True
        self.message = None
        try:
            try:
                vault = await asyncio.to_thread(VaultOpener.open, path)
                snapshot = await asyncio.to_thread(vault.scan)
            except (VaultError, OSError) as exc:
                logger.debug("Selected vault could not be opened", exc_info=True)
                self.message = str(exc)
                return
            if remember:
                try:
                    await asyncio.to_thread(
                        SettingsStore.default().save,
                        Settings(vault=vault.root),
                    )
                except ConfigurationError as exc:
                    logger.debug("Vault selection could not be saved", exc_info=True)
                    self.message = afanes.ui.strings.VAULT_SELECTION_FAILED.format(detail=str(exc))
                    return
            self._enter_vault(vault, snapshot)
        finally:
            self.busy = False

    async def create_vault(self, path: Path, template: str | None = None) -> bool:
        """Create a new vault, seed it, and open it.

        Parameters
        ----------
        path : pathlib.Path
            Directory to create or seed. Missing intermediate folders are
            created.
        template : str | None
            Bundled template identifier, or ``None`` to write only the guide
            note.

        Returns
        -------
        bool
            ``True`` when the new vault opened, ``False`` when creation was
            refused or the current draft could not be saved.

        Notes
        -----
        The vault is created and scanned before its path is saved. When the
        preferences write fails, the created vault still opens for this session
        and :attr:`message` explains that it will not be remembered. Blocking
        file I/O runs in a worker thread.
        """
        async with self._lock:
            return await self._create_vault_state(path, template)

    async def close_vault(self) -> bool:
        """Close the current vault and return to the welcome state.

        Returns
        -------
        bool
            ``True`` when the vault was closed, ``False`` when no vault was
            open or the open page could not be committed.

        Notes
        -----
        Closing saves a dirty draft and forgets the remembered vault by removing
        the preferences file. When the preferences cannot be removed, the
        welcome state is still shown and :attr:`message` explains that the
        vault may reopen next launch. The single-session guard is not released.
        Blocking file I/O runs in a worker thread.
        """
        async with self._lock:
            if self.vault is None:
                return False
            if not await self._commit_current():
                return False
            self.busy = True
            try:
                try:
                    await asyncio.to_thread(SettingsStore.default().clear)
                except ConfigurationError as exc:
                    logger.debug("Remembered vault could not be forgotten", exc_info=True)
                    self._show_welcome(afanes.ui.strings.VAULT_CLOSE_NOT_FORGOTTEN.format(detail=str(exc)))
                    return True
                self._show_welcome(None)
                return True
            finally:
                self.busy = False

    async def template_summaries(self) -> tuple[TemplateSummary, ...] | None:
        """Read the bundled template catalog without blocking the interface.

        Returns
        -------
        tuple[TemplateSummary, ...] | None
            Every catalog entry with the number of notes it writes, or ``None``
            when the bundled content cannot be read.

        Notes
        -----
        A read failure is an expected degradation: the creation action still
        offers a vault without starter content. The read performs blocking
        package I/O in a worker thread and never writes.
        """
        try:
            return await asyncio.to_thread(afanes.core.templates.TemplateCatalog.bundled().summaries)
        except (VaultError, OSError):
            logger.debug("Bundled starter content could not be read", exc_info=True)
            return None

    async def _create_vault_state(self, path: Path, template: str | None) -> bool:
        """Create a vault while the command lock is held."""
        if not await self._commit_current():
            return False
        self.busy = True
        self.message = None
        try:
            try:
                creation = await asyncio.to_thread(VaultOpener.create, path, template=template)
                snapshot = await asyncio.to_thread(creation.vault.scan)
            except (VaultError, OSError) as exc:
                logger.debug("New vault could not be created", exc_info=True)
                self.message = str(exc)
                return False
            remember_failure: str | None = None
            try:
                await asyncio.to_thread(
                    SettingsStore.default().save,
                    Settings(vault=creation.vault.root),
                )
            except ConfigurationError as exc:
                logger.debug("New vault could not be remembered", exc_info=True)
                remember_failure = afanes.ui.strings.VAULT_CREATED_NOT_REMEMBERED.format(detail=str(exc))
            self._enter_vault(creation.vault, snapshot)
            if remember_failure is not None:
                self.message = remember_failure
            return True
        finally:
            self.busy = False

    def _enter_vault(self, vault: Vault, snapshot: VaultSnapshot) -> None:
        """Reset per-vault state and apply a freshly scanned snapshot."""
        self.vault = vault
        self._clear_processing()
        self.active_section = WorkspaceSection.INBOX
        self.browser_query = ""
        self.review_session = None
        self.selected = None
        self.preview_body = None
        self.history = ()
        self._clear_page()
        self._apply_snapshot(snapshot)

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

    def begin_session(self) -> bool:
        """Claim the single active workspace session.

        Returns
        -------
        bool
            ``True`` when this caller became the active session, ``False``
            when another session already holds it.

        Notes
        -----
        The marker is process-wide, matching the single controller and single
        vault. A refused caller must not scan or write the vault.
        """
        return self._vault_session.begin_session()

    def release_session(self) -> None:
        """Release the active workspace session.

        Notes
        -----
        The interface shell calls this when its page disconnects. Releasing an
        unclaimed session is a no-op.
        """
        self._vault_session.release_session()

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
                        self.page = PageDraftFactory.from_page(content, page.reference)
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
        snapshot = self._snapshot
        if page is None or page.path is None or snapshot is None:
            return ()
        note = next((value for value in snapshot.notes if value.path == page.path), None)
        return () if note is None else note.steps

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
    def page_is_new(self) -> bool:
        """Return whether the current page has not been written yet.

        Returns
        -------
        bool
            ``True`` for an unwritten draft; ``False`` when no page is open.
        """
        return self.page is not None and self.page.is_new

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
        async with self._lock:
            page = self.page
            vault = self.vault
            if page is None or page.path is None or vault is None:
                return False
            self.busy = True
            self.message = None
            try:
                try:
                    if checked:
                        await asyncio.to_thread(
                            vault.tick_step,
                            page.path,
                            line_index,
                            datetime.datetime.now(tz=datetime.UTC).astimezone().date(),
                            confirm=True,
                        )
                    else:
                        await asyncio.to_thread(vault.untick_step, page.path, line_index, confirm=True)
                except (AfanesError, OSError) as exc:
                    logger.debug("Step toggle failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_STEP_FAILED.format(detail=str(exc))
                    return False
                if not await self._load_page(page.path, previous=None):
                    return False
                await self._refresh_snapshot()
                return True
            finally:
                self.busy = False

    async def set_page_raw_text(self, text: str) -> None:
        """Replace raw rescue text.

        Parameters
        ----------
        text : str
            Complete file text.
        """
        async with self._lock:
            page = self.page
            if isinstance(page, RawDraft):
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
        async with self._lock:
            page = self.page
            if not isinstance(page, NormalDraft):
                return False
            proposed = page.labels.with_category(category)
            if proposed == page.labels:
                return True
            if page.path is None:
                self.page = page.with_labels(proposed)
                self.message = None
                return True
            vault = self.vault
            if vault is None:
                return False
            try:
                preview = await asyncio.to_thread(
                    vault.plan_category_move,
                    page.path,
                    proposed.category,
                    snapshot=self._snapshot,
                )
            except (AfanesError, OSError) as exc:
                logger.debug("Category move planning failed", exc_info=True)
                self.message = afanes.ui.strings.PAGE_CATEGORY_MOVE_FAILED.format(detail=str(exc))
                return False
            if VaultPath.same(preview.target_path, preview.note_path):
                self.page = page.with_labels(proposed)
                self.message = None
                return True
            self.category_move = preview
            self.pending_labels = proposed
            self.message = None
            return False

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

    async def apply_category_move(self) -> bool:
        """Apply the pending category change and move the file.

        Returns
        -------
        bool
            ``True`` when the category was written and the file moved.
        """
        async with self._lock:
            preview = self.category_move
            labels = self.pending_labels
            vault = self.vault
            if preview is None or labels is None or vault is None:
                return False
            self.busy = True
            try:
                try:
                    target = await asyncio.to_thread(vault.apply_category_move, preview, confirm=True)
                except (AfanesError, OSError) as exc:
                    logger.debug("Category move failed", exc_info=True)
                    self.message = afanes.ui.strings.PAGE_CATEGORY_MOVE_FAILED.format(detail=str(exc))
                    return False
                self.category_move = None
                self.pending_labels = None
                self.history = tuple(target if path == preview.note_path else path for path in self.history)
                if not await self._load_page(target, previous=None):
                    return False
                self.editing = False
                await self._refresh_snapshot()
                return True
            finally:
                self.busy = False

    async def cancel_category_move(self) -> None:
        """Discard a pending category change and keep the file in place.

        Notes
        -----
        The category and the file location are unchanged.
        """
        async with self._lock:
            self.category_move = None
            self.pending_labels = None
            self.message = None

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
            if not isinstance(page, NormalDraft) or labels is None:
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
                    draft = PageDraftFactory.from_page(content, page.reference)
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
        kind = DestinationKind.classify(destination)
        if kind is not DestinationKind.INTERNAL:
            return
        try:
            reference = ReferenceParser().parse(destination)
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
        A successful apply refreshes the scan. Outside a review it leaves the
        wizard in a success state; during a review it records the item as
        reviewed and opens the next queued item. A failed apply keeps the plan
        so the user can retry. Blocking writes and scans run in a worker thread.
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
                session = self.review_session
                if session is not None:
                    self.review_session = session.record_reviewed()
                    await self._enter_current_review_item()
                else:
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

    def _current_review_project(self) -> ReviewItem | None:
        """Return the current project review item, or ``None``."""
        session = self.review_session
        if session is None:
            return None
        item = session.current
        if item is None or item.kind is not ReviewItemKind.PROJECT or item.project is None:
            return None
        return item

    def _current_review_step(self) -> ReviewItem | None:
        """Return the current step review item, or ``None``."""
        session = self.review_session
        if session is None:
            return None
        item = session.current
        if item is None or item.kind not in (ReviewItemKind.DUE_STEP, ReviewItemKind.WAITING_STEP):
            return None
        if item.step is None or item.project is None:
            return None
        return item

    async def _update_review_step(
        self,
        action: Callable[[Vault], object],
    ) -> bool:
        """Apply one confirmed write to the current review step."""
        async with self._lock:
            vault = self.vault
            if vault is None:
                return False
            self.busy = True
            self.message = None
            try:
                try:
                    await asyncio.to_thread(action, vault)
                except (AfanesError, OSError) as exc:
                    logger.debug("Review step write failed", exc_info=True)
                    self.message = afanes.ui.strings.REVIEW_STEP_FAILED.format(detail=str(exc))
                    return False
                await self._refresh_snapshot()
                session = self.review_session
                if session is not None:
                    self.review_session = session.record_reviewed()
                await self._enter_current_review_item()
                return True
            finally:
                self.busy = False

    async def _enter_current_review_item(self) -> None:
        """Load the current review item, skipping captures that disappeared."""
        while True:
            session = self.review_session
            if session is None:
                return
            item = session.current
            self._clear_processing()
            if item is None:
                self.selected = None
                self.preview_body = None
                return
            if item.kind is not ReviewItemKind.INBOX:
                self.selected = None
                self.preview_body = None
                return
            vault = self.vault
            if vault is None:
                return
            try:
                body = await asyncio.to_thread(vault.read_body, item.path)
            except (AfanesError, OSError, UnicodeError) as exc:
                logger.debug("Review capture could not be read", exc_info=True)
                self.message = afanes.ui.strings.REVIEW_CAPTURE_READ_FAILED.format(detail=str(exc))
                self.review_session = session.record_skipped()
                continue
            self.processing_note = item.path
            self.processing_body = body
            self.processing_plan = None
            self.processing_result = None
            self.selected = item.path
            self.preview_body = body
            return

    async def _set_review_project_status(self, status: Status) -> bool:
        """Apply one confirmed status change to the current review project."""
        async with self._lock:
            item = self._current_review_project()
            vault = self.vault
            if item is None or vault is None:
                return False
            self.busy = True
            self.message = None
            try:
                try:
                    await asyncio.to_thread(
                        vault.set_status,
                        item.path,
                        status,
                        snapshot=self._snapshot,
                        confirm=True,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Review project status change failed", exc_info=True)
                    self.message = afanes.ui.strings.REVIEW_PROJECT_FAILED.format(detail=str(exc))
                    return False
                await self._refresh_snapshot()
                session = self.review_session
                if session is not None:
                    self.review_session = session.record_reviewed()
                await self._enter_current_review_item()
                return True
            finally:
                self.busy = False

    def _replace_review_project(self, path: Path) -> None:
        """Replace the current review project with its refreshed summary."""
        snapshot = self._snapshot
        session = self.review_session
        if snapshot is None or session is None:
            return
        summary = next(
            (value for value in afanes.core.search.ProjectBoard(snapshot).summaries() if value.note.path == path),
            None,
        )
        if summary is not None:
            self.review_session = session.replace_current_project(summary)

    async def _mutate_labels(self, transform: Callable[[PageLabels], PageLabels]) -> bool:
        """Apply a label transformation that cannot change the scheme."""
        page = self.page
        if not isinstance(page, NormalDraft):
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
        if not isinstance(page, NormalDraft):
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
                self.page = NormalDraft.new(reference)
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
        if isinstance(page, RawDraft):
            return await self._save_raw_page(page, vault)

        labels = page.labels
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
            updated = page.after_write(page.raw_text, content_hash=new_hash)
            self.page = updated
            if updated.mode is DraftMode.NORMAL:
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
            draft = PageDraftFactory.from_page(content)
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
        await self._vault_session.refresh_snapshot()

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
        self.category_move = None
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
        self.active_section = WorkspaceSection.INBOX
        self.browser_query = ""
        self.review_session = None
        self.selected = None
        self.preview_body = None
        self.busy = False
        self.message = None
        self.session_active = False
        self.history = ()
        self._snapshot = None
        self._clear_processing()
        self._clear_page()
        self._lock = asyncio.Lock()

    def note_title(self, path: Path) -> str:
        """Return the display title for a note in the latest scan.

        Parameters
        ----------
        path : Path
            Absolute path of a note in the vault.

        Returns
        -------
        str
            Display title derived from the note's first level-1 heading, or its
            identity when the body has none. When ``path`` is no longer in the
            latest scan, its filename stem is returned as a safe fallback.

        Notes
        -----
        This method is pure in-memory work over the last scan. It never reads
        the file and never parses Markdown in the view layer.
        """
        return self._vault_session.note_title(path)

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
        return self._vault_session.assignment_candidates(scheme, query)

    def _clear_processing(self) -> None:
        """Clear the Processing Wizard session fields."""
        self.processing_note = None
        self.processing_body = None
        self.processing_plan = None
        self.processing_result = None

    def _show_welcome(self, message: str | None) -> None:
        """Clear the vault state and show the welcome screen."""
        self._vault_session.vault = None
        self._vault_session.snapshot = None
        self._vault_session.notes = ()
        self._vault_session.failures = ()
        self._vault_session.selected = None
        self._vault_session.preview_body = None
        self._browser.active_section = WorkspaceSection.INBOX
        self._browser.query = ""
        self._review.review_session = None
        self._clear_processing()
        self._clear_page()
        self.message = message

    def _apply_snapshot(self, snapshot: VaultSnapshot, focus: Path | None = None) -> None:
        """Replace the inbox list from a scan result."""
        self._vault_session.apply_snapshot(snapshot, focus)


app_state = AppState()
