# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Vault scanning, path containment, atomic writes, and reference-safe edits."""

import dataclasses
import datetime
import hashlib
import os
from collections.abc import Iterable, Mapping
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Self

import afanes.core.atomic
import afanes.core.links
import afanes.core.names
from afanes.core.errors import (
    AfanesError,
    ContentChangedError,
    EmptyCaptureError,
    InvalidReferenceError,
    NameCollisionError,
    NoteParseError,
    ProcessingError,
    ReferenceRewriteError,
    VaultError,
    VaultMissingError,
    VaultNotDirectoryError,
    VaultNotEmptyError,
    VaultPathError,
    VaultUnreadableError,
)
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import CatalogEntry, NameCatalog, ReferenceKey, ResolutionOutcome
from afanes.core.processing import ProcessingOutcome, ProcessingPlan, ProcessingTarget
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status

# Public canonical note extension.
NOTE_SUFFIX = ".md"

# Public default storage layout.
INBOX_DIRECTORY = Path("inbox")
TRASH_DIRECTORY = Path("trash")
REFERENCE_DIRECTORY = Path("reference")
PROJECTS_DIRECTORY = Path("projects")
ACTIONS_DIRECTORY = Path("actions")
CATEGORY_DIRECTORIES: Mapping[ReferenceCategory, Path] = MappingProxyType({ReferenceCategory.PERSON: Path("people")})

_MIN_INBOX_PART_COUNT = 2


@dataclasses.dataclass(frozen=True, slots=True, order=True)
class NoteOrder:
    """Deterministic ordering key for notes.

    Attributes
    ----------
    undated : bool
        ``True`` when the note has no due date, so undated notes sort last.
    due : datetime.date
        Calendar due date, or :attr:`datetime.date.max` when undated.
    status_rank : int
        Workflow rank used to place active actions before deferred ones. Zero
        for projects and alphabetical listings.
    title_key : str
        Normalized display title.
    name_key : str
        Normalized identity.
    path_key : str
        Vault-relative POSIX path, the final deterministic tie-breaker.
    """

    undated: bool
    due: datetime.date
    status_rank: int
    title_key: str
    name_key: str
    path_key: str

    @classmethod
    def for_due(cls, note: "VaultNote", status_rank: int = 0) -> "NoteOrder":
        """Build a due-date-first ordering key for one note.

        Parameters
        ----------
        note : VaultNote
            Note to order.
        status_rank : int
            Workflow rank used only when due dates and titles tie.

        Returns
        -------
        NoteOrder
            Key that sorts dated notes before undated notes, then by due date,
            status rank, title, identity, and path.
        """
        due_date = note.due_date
        return cls(
            undated=due_date is None,
            due=due_date or datetime.date.max,
            status_rank=status_rank,
            title_key=afanes.core.names.normalize_name(note.title),
            name_key=afanes.core.names.normalize_name(note.name),
            path_key=note.relative_path.as_posix(),
        )

    @classmethod
    def alphabetical(cls, note: "VaultNote") -> "NoteOrder":
        """Build a title-first ordering key for one note.

        Parameters
        ----------
        note : VaultNote
            Note to order.

        Returns
        -------
        NoteOrder
            Key whose due and status fields are constant, so ordering falls
            through to title, identity, and path.
        """
        return cls(
            undated=True,
            due=datetime.date.max,
            status_rank=0,
            title_key=afanes.core.names.normalize_name(note.title),
            name_key=afanes.core.names.normalize_name(note.name),
            path_key=note.relative_path.as_posix(),
        )


@dataclasses.dataclass(frozen=True, slots=True, order=True)
class InboxOrder:
    """Newest-first ordering key for inbox captures.

    Attributes
    ----------
    recency_rank : int
        Negative modification time, so newer files sort first.
    name_key : str
        Normalized identity.
    path_key : str
        Vault-relative POSIX path.
    """

    recency_rank: int
    name_key: str
    path_key: str

    @classmethod
    def from_note(cls, note: "VaultNote") -> "InboxOrder":
        """Build a newest-first key for one note.

        Parameters
        ----------
        note : VaultNote
            Note to order.

        Returns
        -------
        InboxOrder
            Key ordered by modification time newest first, then identity and
            path.
        """
        return cls(
            recency_rank=-note.modified_ns,
            name_key=note.name.casefold(),
            path_key=note.relative_path.as_posix(),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class VaultPath:
    """One path interpreted under the vault's path policy.

    Attributes
    ----------
    value : Path
        Vault-relative path to interpret.
    """

    value: Path

    @property
    def is_inbox(self) -> bool:
        """Return whether the path is inside the inbox directory.

        Returns
        -------
        bool
            ``True`` when the first path component names the inbox directory,
            compared case-insensitively, and the path has a filename
            component.

        Notes
        -----
        Only the first component is checked. Nested inbox folders remain part
        of the inbox, matching the capture workflow and the scan's
        classification.
        """
        return (
            len(self.value.parts) >= _MIN_INBOX_PART_COUNT
            and self.value.parts[0].casefold() == INBOX_DIRECTORY.name.casefold()
        )

    @classmethod
    def same(cls, left: Path, right: Path) -> bool:
        """Compare two paths after resolving filesystem aliases.

        Parameters
        ----------
        left : Path
            First path to compare.
        right : Path
            Second path to compare.

        Returns
        -------
        bool
            ``True`` when both paths resolve to the same location.
        """
        return left.resolve() == right.resolve()


@dataclasses.dataclass(frozen=True, slots=True)
class NotePath:
    """A scanned note path and its vault-relative form.

    Attributes
    ----------
    path : Path
        Absolute path to the note file.
    relative_path : Path
        Vault-relative path used for diagnostics.
    """

    path: Path
    relative_path: Path


@dataclasses.dataclass(frozen=True, slots=True)
class VaultNote:
    """One note discovered during a read-only vault scan.

    Attributes
    ----------
    path : Path
        Absolute path to the note file.
    relative_path : Path
        Vault-relative path used for diagnostics.
    name : str
        Filename stem, preserving display case. This is the note's identity and
        reference name.
    title : str
        Display title derived from the first level-1 heading, falling back to
        :attr:`name` when the body has no level-1 heading. It is display-only
        and does not participate in identity or reference resolution.
    note_type : NoteType
        Declared type from frontmatter.
    category : ReferenceCategory | None
        Declared reference category, or ``None`` for an uncategorized
        reference or a non-reference note.
    status : Status | None
        Validated workflow status, or ``None`` when absent.
    due_date : datetime.date | None
        Calendar due date read from frontmatter, or ``None`` when the key is
        absent, null, or not a valid date. An invalid value is kept in the
        file; only the derived scan value is ``None``.
    content_hash : str
        SHA-256 digest of the file bytes, used as an optimistic write guard.
    modified_ns : int
        File modification time in nanoseconds since the epoch, used only for
        display ordering. It is filesystem metadata, not durable vault data.
    body_references : tuple[NoteReference, ...]
        References extracted from the Markdown body.
    frontmatter_references : tuple[NoteReference, ...]
        References declared by ``people`` and ``project`` values.
    """

    path: Path
    relative_path: Path
    name: str
    title: str
    note_type: NoteType
    category: ReferenceCategory | None
    status: Status | None
    due_date: datetime.date | None
    content_hash: str
    modified_ns: int
    body_references: tuple[NoteReference, ...]
    frontmatter_references: tuple[NoteReference, ...]

    @property
    def references(self) -> tuple[NoteReference, ...]:
        """Return body and frontmatter references in that order.

        Returns
        -------
        tuple[NoteReference, ...]
            Body references followed by frontmatter references.
        """
        return self.body_references + self.frontmatter_references

    @property
    def order(self) -> NoteOrder:
        """Return the due-date-first ordering key for this note.

        Returns
        -------
        NoteOrder
            Key used for project and general due-date ordering.
        """
        return NoteOrder.for_due(self)

    @property
    def action_order(self) -> NoteOrder:
        """Return the action ordering key for this note.

        Returns
        -------
        NoteOrder
            Due-date-first key that places active actions before waiting ones
            when earlier fields tie.
        """
        status_rank = 0 if self.status in (None, Status.ACTIVE) else 1
        return NoteOrder.for_due(self, status_rank=status_rank)

    @property
    def alphabetical_order(self) -> NoteOrder:
        """Return the title-first ordering key for this note.

        Returns
        -------
        NoteOrder
            Key that orders by display title, identity, and path.
        """
        return NoteOrder.alphabetical(self)

    @property
    def inbox_order(self) -> InboxOrder:
        """Return the newest-first ordering key for this note.

        Returns
        -------
        InboxOrder
            Key that orders by modification time, identity, and path.
        """
        return InboxOrder.from_note(self)

    @property
    def is_inbox(self) -> bool:
        """Return whether this note is inside the vault's inbox directory.

        Returns
        -------
        bool
            ``True`` when the first vault-relative path component names the
            inbox directory, compared case-insensitively.
        """
        return VaultPath(self.relative_path).is_inbox

    @property
    def is_open_project(self) -> bool:
        """Return whether this note is an open project.

        Returns
        -------
        bool
            ``True`` when the note is a project whose status is absent,
            ``active``, ``waiting``, or ``later``.
        """
        if self.note_type is not NoteType.PROJECT:
            return False
        return self.status not in (Status.DONE, Status.CANCELLED, Status.ARCHIVED)

    @property
    def is_open_action(self) -> bool:
        """Return whether this note is an open action.

        Returns
        -------
        bool
            ``True`` when the note is an action whose status is absent,
            ``active``, or ``waiting``. A ``later`` action is deferred and not
            open.
        """
        if self.note_type is not NoteType.ACTION:
            return False
        return self.status in (None, Status.ACTIVE, Status.WAITING)

    @staticmethod
    def due_date_from_raw(value: object) -> datetime.date | None:
        """Convert a raw frontmatter due date into a calendar date.

        Parameters
        ----------
        value : object
            Raw value from the parsed frontmatter mapping.

        Returns
        -------
        datetime.date | None
            The declared date for a YAML date or a valid ISO date string;
            otherwise ``None``.

        Notes
        -----
        Invalid input is not an error: the scan continues and the page editor
        is responsible for reporting the invalid text when the note is edited.
        A YAML timestamp with a time component is not a calendar date and
        becomes ``None``.
        """
        if isinstance(value, datetime.datetime):
            return None
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            try:
                return datetime.date.fromisoformat(value.strip())
            except ValueError:
                return None
        return None


@dataclasses.dataclass(frozen=True, slots=True)
class VaultFailure:
    """A note that could not be parsed during a scan.

    Attributes
    ----------
    path : Path
        Vault-relative path to the failing note.
    message : str
        Concise diagnostic. The scan continues with the remaining notes.
    """

    path: Path
    message: str


@dataclasses.dataclass(frozen=True, slots=True)
class PageFile:
    """One note file read from disk.

    Attributes
    ----------
    path : Path
        Absolute path to the note file.
    relative_path : Path
        Vault-relative path used for display and diagnostics.
    text : str
        Complete file text, including any frontmatter block.
    content_hash : str
        SHA-256 digest of the file bytes, captured when the note was read.
    """

    path: Path
    relative_path: Path
    text: str
    content_hash: str


@dataclasses.dataclass(frozen=True, slots=True)
class ParsedPage:
    """A page whose frontmatter parsed successfully.

    Attributes
    ----------
    file : PageFile
        Raw file content and identity.
    document : NoteDocument
        Parsed document with a declared note type.
    """

    file: PageFile
    document: NoteDocument

    @property
    def path(self) -> Path:
        """Return the absolute note path."""
        return self.file.path

    @property
    def relative_path(self) -> Path:
        """Return the vault-relative note path."""
        return self.file.relative_path

    @property
    def text(self) -> str:
        """Return the complete file text."""
        return self.file.text

    @property
    def content_hash(self) -> str:
        """Return the content hash captured at read time."""
        return self.file.content_hash


@dataclasses.dataclass(frozen=True, slots=True)
class UnparsedPage:
    """A page whose frontmatter or type could not be parsed.

    Attributes
    ----------
    file : PageFile
        Raw file content and identity.
    failure : str
        Parse failure message. The raw text is retained so the page can open in
        raw rescue mode without losing the file's current content.
    """

    file: PageFile
    failure: str

    @property
    def path(self) -> Path:
        """Return the absolute note path."""
        return self.file.path

    @property
    def relative_path(self) -> Path:
        """Return the vault-relative note path."""
        return self.file.relative_path

    @property
    def text(self) -> str:
        """Return the complete file text."""
        return self.file.text

    @property
    def content_hash(self) -> str:
        """Return the content hash captured at read time."""
        return self.file.content_hash


type PageContent = ParsedPage | UnparsedPage


class LinkOutcome(StrEnum):
    """Outcome of routing an internal reference to a page.

    Attributes
    ----------
    RESOLVED : str
        Exactly one parsed note matches the reference.
    AMBIGUOUS : str
        Several parsed notes match the reference.
    BROKEN : str
        No parsed note matches, but one or more unparseable files share the
        reference name.
    MISSING : str
        No parsed note and no unparseable file matches the reference.
    """

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    BROKEN = "broken"
    MISSING = "missing"


@dataclasses.dataclass(frozen=True, slots=True)
class LinkTarget:
    """One routed internal reference and the page paths it reaches.

    Attributes
    ----------
    reference : NoteReference
        Reference that was routed.
    outcome : LinkOutcome
        Whether the reference resolved, was ambiguous, pointed at an
        unparseable file, or matched nothing.
    paths : tuple[Path, ...]
        Absolute paths for a resolved, ambiguous, or broken outcome. Empty for
        a missing outcome. Ambiguous and broken outcomes keep every candidate.
    """

    reference: NoteReference
    outcome: LinkOutcome
    paths: tuple[Path, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceSite:
    """References in one note that point at a target note.

    Attributes
    ----------
    path : Path
        Absolute path to the referring note.
    reference_count : int
        Number of references in that note that resolve to the target.
    """

    path: Path
    reference_count: int


@dataclasses.dataclass(frozen=True, slots=True)
class VaultSnapshot:
    """Read-only result of scanning a vault.

    Attributes
    ----------
    root : Path
        Resolved vault root.
    notes : tuple[VaultNote, ...]
        Successfully parsed notes in deterministic path order.
    failures : tuple[VaultFailure, ...]
        Notes that could not be parsed, in deterministic path order.
    catalog : NameCatalog
        Name catalog built from the parsed notes.
    """

    root: Path
    notes: tuple[VaultNote, ...]
    failures: tuple[VaultFailure, ...]
    catalog: NameCatalog

    def inbox_notes(self) -> tuple[VaultNote, ...]:
        """Return the notes currently in this vault's inbox.

        Returns
        -------
        tuple[VaultNote, ...]
            Notes under the vault's ``inbox/`` directory, including nested
            subdirectories, ordered by modification time newest first. Ties are
            broken by case-folded name and then vault-relative path.

        Notes
        -----
        The first path component is matched case-insensitively so the same
        vault behaves consistently on case-sensitive and case-insensitive
        filesystems. This method performs no file I/O.
        """
        notes = [note for note in self.notes if note.is_inbox]
        return tuple(sorted(notes, key=lambda note: note.inbox_order))

    def assignment_candidates(self, scheme: ReferenceScheme, query: str) -> tuple[VaultNote, ...]:
        """Return notes whose identity or display title contains a query.

        Parameters
        ----------
        scheme : ReferenceScheme
            Namespace to search, normally ``person`` or ``project``.
        query : str
            Free text typed by the user. Matching ignores case, Unicode form,
            and repeated whitespace. An empty query matches every note in the
            scheme.

        Returns
        -------
        tuple[VaultNote, ...]
            Matching notes ordered by display title, then identity, then
            vault-relative path. Empty when nothing matches.

        Notes
        -----
        This method performs no file I/O and no rescan. Identity and display
        title are normalized with :func:`afanes.core.names.normalize_name`, so
        matching follows the same rule as reference resolution. Display titles
        are only matched; they never become reference targets.
        """
        normalized_query = afanes.core.names.normalize_name(query)
        matches = [
            note
            for note in self.notes
            if ReferenceScheme.for_note(note.note_type, note.category) is scheme
            and (
                normalized_query in afanes.core.names.normalize_name(note.name)
                or normalized_query in afanes.core.names.normalize_name(note.title)
            )
        ]
        return tuple(
            sorted(
                matches,
                key=lambda note: note.alphabetical_order,
            )
        )

    def link_target(self, reference: NoteReference) -> LinkTarget:
        """Route one internal reference to its page without reading the vault.

        Parameters
        ----------
        reference : NoteReference
            Internal reference to route. External destinations are classified
            before this method is called and are never passed here.

        Returns
        -------
        LinkTarget
            Resolved, ambiguous, broken, or missing outcome with every matching
            absolute path.

        Notes
        -----
        A broken outcome is reported when the catalog has no match but one or
        more unparseable files share the normalized reference name. Their
        vault-relative failure paths are resolved against :attr:`root` so the
        caller can open the file in raw rescue mode. This method performs no
        file I/O and never chooses among ambiguous candidates.
        """
        resolution = self.catalog.resolve(reference)
        if resolution.outcome is ResolutionOutcome.RESOLVED:
            return LinkTarget(reference=reference, outcome=LinkOutcome.RESOLVED, paths=resolution.targets)
        if resolution.outcome is ResolutionOutcome.AMBIGUOUS:
            return LinkTarget(reference=reference, outcome=LinkOutcome.AMBIGUOUS, paths=resolution.targets)

        normalized = afanes.core.names.normalize_name(reference.name)
        broken = tuple(
            self.root / failure.path
            for failure in self.failures
            if afanes.core.names.normalize_name(failure.path.stem) == normalized
        )
        if broken:
            return LinkTarget(reference=reference, outcome=LinkOutcome.BROKEN, paths=broken)
        return LinkTarget(reference=reference, outcome=LinkOutcome.MISSING)

    def find_note(self, source: Path) -> VaultNote | None:
        """Find a scanned note by path.

        Parameters
        ----------
        source : Path
            Note path, relative or absolute.

        Returns
        -------
        VaultNote | None
            Matching scanned note, or ``None`` when the path is not in this
            snapshot.
        """
        return next((note for note in self.notes if VaultPath.same(note.path, source)), None)

    def affected_sites(self, source: Path) -> tuple[ReferenceSite, ...]:
        """Collect per-note reference counts that resolve to a target note.

        Parameters
        ----------
        source : Path
            Target note path.

        Returns
        -------
        tuple[ReferenceSite, ...]
            Referring notes with per-note reference counts, in scan order.
        """
        sites: list[ReferenceSite] = []
        for note in self.notes:
            count = sum(1 for reference in note.references if self.resolves_to(reference, source))
            if count:
                sites.append(ReferenceSite(path=note.path, reference_count=count))
        return tuple(sites)

    def resolves_to(self, reference: NoteReference, source: Path) -> bool:
        """Return whether a reference uniquely resolves to a target note.

        Parameters
        ----------
        reference : NoteReference
            Reference to resolve.
        source : Path
            Target note path.

        Returns
        -------
        bool
            ``True`` only for a unique resolution to ``source``.
        """
        resolution = self.catalog.resolve(reference)
        if resolution.outcome is not ResolutionOutcome.RESOLVED:
            return False
        return VaultPath.same(resolution.targets[0], source)

    def hash_for_note(self, path: Path) -> str:
        """Return the content hash captured for a scanned note.

        Parameters
        ----------
        path : Path
            Note path to find.

        Returns
        -------
        str
            SHA-256 digest captured during the scan.

        Raises
        ------
        StopIteration
            If the path is not part of this snapshot.
        """
        note = next(note for note in self.notes if VaultPath.same(note.path, path))
        return note.content_hash

    def referrers(self, note_path: Path) -> tuple[ReferenceSite, ...]:
        """Return notes whose references resolve to one target note.

        Parameters
        ----------
        note_path : Path
            Target note path, relative or absolute.

        Returns
        -------
        tuple[ReferenceSite, ...]
            Referring notes with per-note reference counts, in scan order.
            Empty when no reference resolves to the target.

        Notes
        -----
        Only unique resolution counts; an ambiguous reference is not attributed
        to any candidate. The result is computed from the snapshot and performs
        no file I/O.
        """
        return self.affected_sites(note_path)


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceRepairPreview:
    """References that would be rewritten from one name to another.

    Attributes
    ----------
    old : NoteReference
        Reference name currently written in the vault.
    new : NoteReference
        Replacement reference name in the same scheme.
    sites : tuple[ReferenceSite, ...]
        Referring notes and their per-note reference counts, in scan order.
    content_hashes : dict[Path, str]
        Content hash captured at planning time for every referring note.
    """

    old: NoteReference
    new: NoteReference
    sites: tuple[ReferenceSite, ...]
    content_hashes: dict[Path, str]


@dataclasses.dataclass(frozen=True, slots=True)
class RenamePreview:
    """Planned rename and the references that would change.

    Attributes
    ----------
    note_path : Path
        Current absolute path of the note.
    target_path : Path
        Absolute path after the rename.
    scheme : ReferenceScheme
        Namespace of the note, used to match inbound references.
    old_name : str
        Current filename stem.
    new_name : str
        Sanitized replacement stem.
    heading_update : bool
        Whether the first level-1 heading currently matches the old identity
        and should be updated to the new one.
    affected : tuple[ReferenceSite, ...]
        Referring notes and counts, in scan order.
    reference_count : int
        Total number of references that would be rewritten.
    content_hashes : dict[Path, str]
        Content hash captured at planning time for every affected note,
        including the renamed note when it refers to itself or needs a heading
        update.
    """

    note_path: Path
    target_path: Path
    scheme: ReferenceScheme
    old_name: str
    new_name: str
    heading_update: bool
    affected: tuple[ReferenceSite, ...]
    reference_count: int
    content_hashes: dict[Path, str]


@dataclasses.dataclass(frozen=True, slots=True)
class RewriteFailure:
    """A referring note that could not be rewritten.

    Attributes
    ----------
    path : Path
        Absolute path to the note.
    message : str
        Concise failure reason.
    """

    path: Path
    message: str


@dataclasses.dataclass(frozen=True, slots=True)
class RewriteReport:
    """Outcome of applying a reference repair.

    Attributes
    ----------
    updated : tuple[Path, ...]
        Notes whose references were rewritten.
    skipped : tuple[Path, ...]
        Notes skipped because their content changed after planning.
    unchanged : tuple[Path, ...]
        Notes that no longer contained the old reference.
    failed : tuple[RewriteFailure, ...]
        Notes that could not be rewritten, with reasons.
    """

    updated: tuple[Path, ...]
    skipped: tuple[Path, ...]
    unchanged: tuple[Path, ...]
    failed: tuple[RewriteFailure, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class RenameReport:
    """Outcome of applying a rename preview.

    Attributes
    ----------
    renamed : bool
        Whether this call moved the file. ``False`` means a previous run had
        already renamed it and only reference rewrites remained.
    updated : tuple[Path, ...]
        Notes whose references were rewritten.
    skipped : tuple[Path, ...]
        Notes skipped because their content changed after planning.
    unchanged : tuple[Path, ...]
        Notes that no longer needed a rewrite.
    failed : tuple[RewriteFailure, ...]
        Notes that could not be rewritten, with reasons.
    """

    renamed: bool
    updated: tuple[Path, ...]
    skipped: tuple[Path, ...]
    unchanged: tuple[Path, ...]
    failed: tuple[RewriteFailure, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class TrashPreview:
    """Inbound references and destination reported before trashing a note.

    Attributes
    ----------
    note_path : Path
        Absolute path to the note that would be moved.
    trash_path : Path
        Absolute destination inside ``trash/``.
    reference_count : int
        Number of references that point to the note.
    affected_notes : tuple[Path, ...]
        Notes containing at least one inbound reference.
    """

    note_path: Path
    trash_path: Path
    reference_count: int
    affected_notes: tuple[Path, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class Vault:
    """A resolved vault root and the operations scoped to it.

    Attributes
    ----------
    root : Path
        Absolute, resolved vault directory.
    """

    root: Path

    def __post_init__(self) -> None:
        """Resolve and validate the vault root.

        Raises
        ------
        VaultMissingError
            If the path does not exist.
        VaultNotDirectoryError
            If the path exists and is not a directory.
        """
        resolved = self.root.expanduser().resolve()
        if not resolved.exists():
            message = f"Vault root does not exist: {self.root}"
            raise VaultMissingError(message)
        if not resolved.is_dir():
            message = f"Vault root is not a directory: {self.root}"
            raise VaultNotDirectoryError(message)
        object.__setattr__(self, "root", resolved)

    @classmethod
    def open(cls, path: Path) -> Self:
        """Open an existing directory as a vault.

        Parameters
        ----------
        path : pathlib.Path
            Candidate vault directory. A relative path is resolved against the
            current working directory.

        Returns
        -------
        Vault
            Validated vault service for ``path``.

        Raises
        ------
        VaultMissingError
            If the path does not exist.
        VaultNotDirectoryError
            If the path exists and is not a directory.
        VaultUnreadableError
            If the directory cannot be read.

        Notes
        -----
        This method performs blocking filesystem checks and never writes. It is
        the single validation path shared by the interface and the command
        line.
        """
        vault = cls(path)
        if not os.access(vault.root, os.R_OK):
            message = f"Vault root cannot be read: {path}"
            raise VaultUnreadableError(message)
        return vault

    @classmethod
    def default_layout(cls) -> tuple[Path, ...]:
        """Return the default folders relative to a vault root.

        Returns
        -------
        tuple[pathlib.Path, ...]
            Canonical relative folders seeded when a vault is created, in the
            order a created vault reports them.

        Notes
        -----
        This method is a pure lookup. It reads no filesystem and creates
        nothing.
        """
        return (
            INBOX_DIRECTORY,
            TRASH_DIRECTORY,
            REFERENCE_DIRECTORY,
            *(REFERENCE_DIRECTORY / folder for folder in CATEGORY_DIRECTORIES.values()),
            PROJECTS_DIRECTORY,
            ACTIONS_DIRECTORY,
        )

    @classmethod
    def create_directory(cls, path: Path) -> "VaultCreation":
        """Create and seed a vault directory.

        Parameters
        ----------
        path : pathlib.Path
            Directory to create or seed. It must be missing or empty.

        Returns
        -------
        VaultCreation
            Created vault, the intermediate directories made for it, and the
            default folders created inside it.

        Raises
        ------
        VaultNotDirectoryError
            If the path exists and is not a directory.
        VaultNotEmptyError
            If the directory exists and already contains entries.
        VaultError
            If a directory cannot be created or seeded.

        Notes
        -----
        Missing intermediate folders are created. The path is resolved before
        it is inspected, so a symlink cannot smuggle a populated directory past
        the emptiness check. Nothing is rolled back when seeding fails partway:
        the directories already created stay in place.
        """
        target = path.expanduser().resolve()
        try:
            if target.exists() and not target.is_dir():
                message = f"Vault path is not a directory: {path}"
                raise VaultNotDirectoryError(message)
            if target.is_dir() and any(target.iterdir()):
                message = f"Vault path is not empty: {path}"
                raise VaultNotEmptyError(message)
            created = cls._missing_directories(target.parent)
            target.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            message = f"Could not create the vault directory: {path}"
            raise VaultError(message) from exc
        vault = cls(target)
        try:
            seeded = vault._seed_layout()
        except OSError as exc:
            message = f"Could not seed the vault directory: {path}"
            raise VaultError(message) from exc
        return VaultCreation(vault=vault, created_directories=created, seeded_directories=seeded)

    @staticmethod
    def _missing_directories(start: Path) -> tuple[Path, ...]:
        """Return the missing ancestor directories of ``start``, outermost first."""
        missing: list[Path] = []
        current = start
        while not current.exists():
            missing.append(current)
            parent = current.parent
            if parent == current:
                break
            current = parent
        return tuple(reversed(missing))

    def _seed_layout(self) -> tuple[Path, ...]:
        """Create the default folders and return the ones that were made."""
        destinations = [
            self.directory_for(NoteType.NOTE),
            self._existing_directory(self.root, TRASH_DIRECTORY),
            self.directory_for(NoteType.REFERENCE),
            *(self.directory_for(NoteType.REFERENCE, category) for category in CATEGORY_DIRECTORIES),
            self.directory_for(NoteType.PROJECT),
            self.directory_for(NoteType.ACTION),
        ]
        created: list[Path] = []
        for destination in destinations:
            if destination.is_dir():
                continue
            destination.mkdir(parents=True, exist_ok=True)
            created.append(destination)
        return tuple(created)

    def contained(self, candidate: Path) -> Path:
        """Resolve a path and verify that it stays inside this vault.

        Parameters
        ----------
        candidate : Path
            Relative or absolute candidate path.

        Returns
        -------
        Path
            Resolved candidate path inside the vault.

        Raises
        ------
        VaultPathError
            If the resolved candidate escapes the vault root.
        """
        resolved = candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()
        if not resolved.is_relative_to(self.root):
            message = f"Path escapes the vault: {candidate}"
            raise VaultPathError(message)
        return resolved

    def scan(self) -> VaultSnapshot:
        """Scan this vault without writing anything.

        Returns
        -------
        VaultSnapshot
            Parsed notes, failures, and the resulting name catalog.

        Notes
        -----
        Files are visited in deterministic path order. Directories whose names
        begin with a dot are skipped, as are symlinks that resolve outside the
        vault. A malformed note becomes a ``VaultFailure`` and does not abort
        the scan. This method performs blocking file I/O and never writes.
        """
        return self._scan()

    def _scan(self) -> VaultSnapshot:
        """Scan this vault's notes and build the name catalog."""
        notes: list[VaultNote] = []
        failures: list[VaultFailure] = []
        reader = afanes.core.links.ReferenceReader()

        for note_path in self._note_paths():
            try:
                notes.append(Vault._read_note(note_path, reader))
            except (OSError, UnicodeDecodeError, AfanesError) as exc:
                failures.append(VaultFailure(path=note_path.relative_path, message=str(exc)))

        catalog = NameCatalog.from_entries(
            CatalogEntry(path=note.path, note_type=note.note_type, category=note.category) for note in notes
        )
        return VaultSnapshot(root=self.root, notes=tuple(notes), failures=tuple(failures), catalog=catalog)

    def _note_paths(self) -> list[NotePath]:
        """Return note paths and their vault-relative paths in deterministic order."""
        paths: list[NotePath] = []
        trash_name = TRASH_DIRECTORY.name.casefold()
        for path in sorted(self.root.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(self.root)
            if relative.parts and relative.parts[0].casefold() == trash_name:
                continue
            if any(part.startswith(".") for part in relative.parts[:-1]):
                continue
            if path.suffix.casefold() != NOTE_SUFFIX or not path.is_file():
                continue
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if not resolved.is_relative_to(self.root):
                continue
            paths.append(NotePath(path=path, relative_path=relative))
        return paths

    @staticmethod
    def _read_note(
        note_path: NotePath,
        reader: afanes.core.links.ReferenceReader,
    ) -> VaultNote:
        """Read and parse one note, raising on malformed input."""
        stat = note_path.path.stat()
        data = note_path.path.read_bytes()
        text = data.decode("utf-8")
        document = NoteDocument.from_text(text)
        if document.note_type is None:
            message = "Note has no type"
            raise NoteParseError(message)
        body_references = tuple(reader.extract(document.body))
        return VaultNote(
            path=note_path.path,
            relative_path=note_path.relative_path,
            name=note_path.path.stem,
            title=document.title or note_path.path.stem,
            note_type=document.note_type,
            category=document.category,
            status=document.status,
            due_date=VaultNote.due_date_from_raw(document.raw.get("due_date")),
            content_hash=hashlib.sha256(data).hexdigest(),
            modified_ns=stat.st_mtime_ns,
            body_references=body_references,
            frontmatter_references=document.references,
        )

    def directory_for(self, note_type: NoteType, category: ReferenceCategory | None = None) -> Path:
        """Return the default destination directory for a note kind.

        Parameters
        ----------
        note_type : NoteType
            Type of the note to file.
        category : ReferenceCategory | None
            Reference category. Only valid when ``note_type`` is
            :attr:`NoteType.REFERENCE`.

        Returns
        -------
        Path
            Absolute default directory inside the vault. An existing directory
            whose name differs only by case is reused. The directory is not
            created by this method.

        Raises
        ------
        VaultError
            If a category is supplied for a non-reference note or the category
            has no default directory.
        """
        if category is not None and note_type is not NoteType.REFERENCE:
            message = "Only reference notes can declare a category"
            raise VaultError(message)
        if note_type is NoteType.ACTION:
            return self._existing_directory(self.root, ACTIONS_DIRECTORY)
        if note_type is NoteType.PROJECT:
            return self._existing_directory(self.root, PROJECTS_DIRECTORY)
        if note_type is NoteType.REFERENCE:
            reference_root = self._existing_directory(self.root, REFERENCE_DIRECTORY)
            if category is None:
                return reference_root
            folder = CATEGORY_DIRECTORIES.get(category)
            if folder is None:
                message = f"Unknown reference category: {category}"
                raise VaultError(message)
            return self._existing_directory(reference_root, folder)
        return self._existing_directory(self.root, INBOX_DIRECTORY)

    def plan_processing(
        self,
        note_path: Path,
        outcome: ProcessingOutcome,
        *,
        status: Status | None = None,
        due_date: datetime.date | None = None,
        people: Iterable[str] = (),
        project: str | None = None,
        snapshot: VaultSnapshot | None = None,
    ) -> ProcessingPlan:
        """Plan one clarification step for an inbox capture.

        Parameters
        ----------
        note_path : Path
            Capture path, relative or absolute, under the vault's ``inbox/``.
        outcome : ProcessingOutcome
            Selected clarification outcome.
        status : Status | None
            Requested target status. Actions and projects default to
            ``active``; Later is always ``later``; Reference has no status.
        due_date : datetime.date | None
            Optional calendar due date for an action or project.
        people : Iterable[str]
            Person names assigned to the target. Names may be unresolved.
        project : str | None
            Project name assigned to an action. The project may be unresolved.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        ProcessingPlan
            Destination, target metadata, inbound reference report, content
            hashes, scheme-change flag, and unresolved assignments.

        Raises
        ------
        ProcessingError
            If the note is outside ``inbox/``, is missing from the vault, or
            the requested metadata is not valid for the outcome.
        NameCollisionError
            If the destination filename or target scheme name already exists.
        NoteParseError
            If the capture cannot be parsed.
        VaultPathError
            If a path escapes the vault.

        Notes
        -----
        Planning performs blocking reads but never writes. The plan captures
        the current source hash so apply can detect an external edit.
        """
        source = self.contained(note_path)
        self._require_inbox_note(source)

        vault = snapshot or self.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise ProcessingError(message)

        people_references = tuple(self._person_reference(name) for name in people)
        project_reference = self._project_reference(project) if project is not None else None
        source_scheme = ReferenceScheme.for_note(note.note_type, note.category)
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

        if outcome is ProcessingOutcome.TRASH:
            if status is not None or due_date is not None or people_references or project_reference is not None:
                message = "Trash does not accept assignment metadata"
                raise ProcessingError(message)
            trash_preview = self.plan_trash(source, snapshot=vault)
            return ProcessingPlan(
                source_path=source,
                target_path=trash_preview.trash_path,
                outcome=outcome,
                target_type=note.note_type,
                target_category=note.category,
                target_status=note.status,
                due_date=None,
                people=(),
                project=None,
                source_hash=source_hash,
                processed_hash=source_hash,
                reference_count=trash_preview.reference_count,
                affected_notes=trash_preview.affected_notes,
                changes_scheme=False,
                unresolved_references=(),
            )

        target = ProcessingTarget.from_outcome(outcome, status)
        target_type = target.note_type
        target_status = target.status
        if due_date is not None and outcome not in (ProcessingOutcome.ACTION, ProcessingOutcome.PROJECT):
            message = "Only actions and projects accept a due date"
            raise ProcessingError(message)
        if project_reference is not None and outcome is not ProcessingOutcome.ACTION:
            message = "Only actions accept a project reference"
            raise ProcessingError(message)

        target_path = self.directory_for(target_type) / f"{source.stem}{NOTE_SUFFIX}"
        target_scheme = ReferenceScheme.for_note(target_type)
        existing = vault.catalog.candidates(target_scheme, source.stem)
        if any(not VaultPath.same(path, source) for path in existing):
            message = f"A {target_scheme.value} note named {source.stem!r} already exists"
            raise NameCollisionError(message)
        if target_path.exists() and not VaultPath.same(target_path, source):
            message = f"Destination already exists: {target_path}"
            raise NameCollisionError(message)

        affected = vault.affected_sites(source)
        unresolved = tuple(
            reference
            for reference in (*people_references, project_reference)
            if reference is not None and vault.catalog.resolve(reference).outcome is not ResolutionOutcome.RESOLVED
        )
        plan = ProcessingPlan(
            source_path=source,
            target_path=target_path,
            outcome=outcome,
            target_type=target_type,
            target_category=None,
            target_status=target_status,
            due_date=due_date,
            people=people_references,
            project=project_reference,
            source_hash=source_hash,
            processed_hash=source_hash,
            reference_count=sum(site.reference_count for site in affected),
            affected_notes=tuple(site.path for site in affected),
            changes_scheme=source_scheme is not target_scheme,
            unresolved_references=unresolved,
        )
        document = NoteDocument.from_text(source.read_text(encoding="utf-8"))
        processed_text = plan.processed_text(document)
        return dataclasses.replace(
            plan,
            processed_hash=hashlib.sha256(processed_text.encode("utf-8")).hexdigest(),
        )

    def apply_processing(
        self,
        plan: ProcessingPlan,
        *,
        confirm: bool = False,
    ) -> Path:
        """Apply a processing plan after explicit confirmation.

        Parameters
        ----------
        plan : ProcessingPlan
            Plan produced by :meth:`plan_processing`.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.

        Returns
        -------
        Path
            Absolute destination path after the move.

        Raises
        ------
        ProcessingError
            If confirmation is missing, the source is no longer an inbox
            capture, the source changed after planning, the processed text
            does not match the plan, or the move fails.
        NameCollisionError
            If the destination appears after planning.
        VaultPathError
            If a plan path escapes the vault.

        Notes
        -----
        The classified frontmatter is written atomically to the source before
        the rename. A failed move therefore leaves a processed-looking note in
        ``inbox/``, and the same plan can be retried. Trash plans move the file
        without rewriting it.
        """
        if not confirm:
            message = "Processing requires explicit confirmation"
            raise ProcessingError(message)

        source = self.contained(plan.source_path)
        self._require_inbox_note(source)
        if not source.is_file():
            message = f"Capture no longer exists: {plan.source_path}"
            raise ProcessingError(message)

        target = self._processing_destination(plan)
        self._write_processing(plan, source)
        return self._move_processing(source, target)

    def _processing_destination(self, plan: ProcessingPlan) -> Path:
        """Resolve and validate the destination path for a plan."""
        target = self.contained(plan.target_path)
        if target.exists():
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)
        return target

    def _write_processing(self, plan: ProcessingPlan, source: Path) -> None:
        """Write the classified frontmatter, or confirm it is already written."""
        data = source.read_bytes()
        current_hash = hashlib.sha256(data).hexdigest()
        if plan.outcome is ProcessingOutcome.TRASH:
            if current_hash != plan.source_hash:
                message = "Source note changed after planning"
                raise ProcessingError(message)
            return
        if current_hash == plan.processed_hash:
            return
        if current_hash != plan.source_hash:
            message = "Source note changed after planning"
            raise ProcessingError(message)
        document = NoteDocument.from_text(data.decode("utf-8"))
        text = plan.processed_text(document)
        processed_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if processed_hash != plan.processed_hash:
            message = "Processed note does not match the plan"
            raise ProcessingError(message)
        afanes.core.atomic.write_text_atomic(source, text)

    def _move_processing(self, source: Path, target: Path) -> Path:
        """Move a processed note to its destination."""
        if target.exists():
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.replace(target)
        except OSError as exc:
            message = f"Could not move the note to its destination: {source}"
            raise ProcessingError(message) from exc
        return target

    def read_body(self, note_path: Path) -> str:
        """Read a note and return its Markdown body without frontmatter.

        Parameters
        ----------
        note_path : Path
            Relative or absolute path to a note inside this vault.

        Returns
        -------
        str
            Markdown body with the frontmatter block removed.

        Raises
        ------
        VaultPathError
            If the path escapes the vault root.
        NoteParseError
            If the note's frontmatter is malformed.
        InvalidReferenceError
            If a frontmatter reference is invalid.

        Notes
        -----
        This method performs blocking file I/O and never writes.
        """
        source = self.contained(note_path)
        text = source.read_text(encoding="utf-8")
        return NoteDocument.from_text(text).body

    def read_page(self, note_path: Path) -> PageContent:
        """Read one note for viewing or editing without writing anything.

        Parameters
        ----------
        note_path : Path
            Relative or absolute path to a note inside this vault.

        Returns
        -------
        PageContent
            Raw text, content hash, parsed document, and any parse failure.

        Raises
        ------
        VaultPathError
            If the path escapes the vault root, does not exist, or is a
            directory.
        OSError
            If the file cannot be read.
        UnicodeError
            If the file is not valid UTF-8.

        Notes
        -----
        A note with malformed frontmatter is returned as an
        :class:`UnparsedPage` with a diagnostic in ``failure``. The raw text is
        preserved so the page can offer raw rescue mode. This method performs
        blocking file I/O and never writes.
        """
        source = self.contained(note_path)
        try:
            data = source.read_bytes()
        except FileNotFoundError as exc:
            message = f"Note does not exist: {note_path}"
            raise VaultPathError(message) from exc
        except IsADirectoryError as exc:
            message = f"Not a note file: {note_path}"
            raise VaultPathError(message) from exc

        text = data.decode("utf-8")
        content_hash = hashlib.sha256(data).hexdigest()
        relative_path = source.relative_to(self.root)
        file = PageFile(path=source, relative_path=relative_path, text=text, content_hash=content_hash)
        try:
            document = NoteDocument.from_text(text)
        except (NoteParseError, InvalidReferenceError) as exc:
            return UnparsedPage(file=file, failure=str(exc))
        if document.note_type is None:
            return UnparsedPage(file=file, failure="Note has no type")
        return ParsedPage(file=file, document=document)

    def write_page(self, note_path: Path, text: str, expected_hash: str) -> str:
        """Write a note after confirming that its content is unchanged.

        Parameters
        ----------
        note_path : Path
            Relative or absolute path to an existing note inside this vault.
        text : str
            Complete file text to write. The caller owns the newline style; the
            text is written as provided.
        expected_hash : str
            SHA-256 digest of the content read before editing.

        Returns
        -------
        str
            SHA-256 digest of the written bytes, for the next comparison.

        Raises
        ------
        VaultPathError
            If the path escapes the vault, does not exist, or is a directory.
        ContentChangedError
            If the file's current content differs from ``expected_hash``.
        VaultError
            If the destination directory is missing or the atomic write fails.
        OSError
            If the file cannot be read.

        Notes
        -----
        The current file is read and hashed immediately before the atomic
        replace. A concurrent write between the check and the replace is not
        detected; this is accepted for the local single-writer application.
        Nothing is written when the hash does not match.
        """
        source = self.contained(note_path)
        try:
            data = source.read_bytes()
        except FileNotFoundError as exc:
            message = f"Note does not exist: {note_path}"
            raise VaultPathError(message) from exc
        except IsADirectoryError as exc:
            message = f"Not a note file: {note_path}"
            raise VaultPathError(message) from exc

        if hashlib.sha256(data).hexdigest() != expected_hash:
            message = f"Note changed on disk: {note_path}"
            raise ContentChangedError(message)

        afanes.core.atomic.write_text_atomic(source, text)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def create(
        self,
        title: str,
        note_type: NoteType,
        *,
        category: ReferenceCategory | None = None,
        directory: Path | None = None,
        body: str = "",
        status: Status | None = None,
    ) -> Path:
        """Create a note whose sanitized filename stem becomes its identity.

        Parameters
        ----------
        title : str
            Name to sanitize into the identity filename. The new note's display
            title is derived separately from its body.
        note_type : NoteType
            Declared type for the new note.
        category : ReferenceCategory | None
            Reference category. Only valid when ``note_type`` is
            :attr:`NoteType.REFERENCE`; ``None`` creates an uncategorized
            reference.
        directory : Path | None
            Vault-relative or absolute classification directory. Defaults to
            the layout destination for ``note_type`` and ``category``. Missing
            directories are created.
        body : str
            Initial Markdown body. New files use LF and UTF-8 without a BOM.
        status : Status | None
            Initial status value. ``None`` omits the ``status`` key entirely.

        Returns
        -------
        Path
            Absolute path to the created note.

        Raises
        ------
        NoteParseError
            If a category is supplied for a non-reference note.
        VaultPathError
            If the target directory escapes the vault.
        VaultError
            If the target path is not a directory.
        """
        if category is not None and note_type is not NoteType.REFERENCE:
            message = "Only reference notes can declare a category"
            raise NoteParseError(message)

        target_directory = (
            self.contained(self.directory_for(note_type, category)) if directory is None else self.contained(directory)
        )
        if target_directory.exists() and not target_directory.is_dir():
            message = f"Note directory is not a directory: {target_directory}"
            raise VaultError(message)
        target_directory.mkdir(parents=True, exist_ok=True)

        snapshot = self.scan()
        scheme = ReferenceScheme.for_note(note_type, category)
        taken = {
            note.name for note in snapshot.notes if ReferenceScheme.for_note(note.note_type, note.category) is scheme
        }
        taken.update(entry.stem for entry in target_directory.iterdir())
        taken.update(entry.name for entry in target_directory.iterdir())
        name = afanes.core.names.unique_name(afanes.core.names.safe_filename(title), taken)

        document = self._new_note_document(note_type, category, status, body)
        path = target_directory / f"{name}{NOTE_SUFFIX}"
        afanes.core.atomic.write_text_atomic(path, document.to_text())
        return path

    def create_page(
        self,
        reference_name: str,
        note_type: NoteType,
        category: ReferenceCategory | None = None,
        *,
        body: str = "",
        text: str | None = None,
    ) -> Path:
        """Create a note under its exact name, without adding a suffix.

        Parameters
        ----------
        reference_name : str
            Name from the reference that requested the page. It is sanitized
            into the identity filename.
        note_type : NoteType
            Declared type for the new note.
        category : ReferenceCategory | None
            Reference category. Only valid when ``note_type`` is
            :attr:`NoteType.REFERENCE`; ``None`` creates an uncategorized
            reference.
        body : str
            Initial Markdown body used when ``text`` is ``None``.
        text : str | None
            Complete note text to write exactly. When supplied, it takes
            precedence over ``body`` and must declare the requested type and
            category.

        Returns
        -------
        Path
            Absolute path to the created note.

        Raises
        ------
        NoteParseError
            If a category is supplied for a non-reference note, ``text`` does
            not parse, or ``text`` declares a different type or category.
        NameCollisionError
            If the exact name already belongs to a note in the same scheme or
            the target filename exists, including a case-insensitive sibling.
        VaultPathError
            If the target directory escapes the vault.
        VaultError
            If the target path is not a directory or the write fails.

        Notes
        -----
        Unlike :meth:`create`, this method never changes the requested name. It
        is used for pages created from unresolved links, where a suffix would
        leave the link unresolved. Collision checks run before the destination
        directory is created and before any file is written.
        """
        if category is not None and note_type is not NoteType.REFERENCE:
            message = "Only reference notes can declare a category"
            raise NoteParseError(message)

        content: str
        if text is None:
            content = self._new_note_document(note_type, category, None, body).to_text()
        else:
            parsed = NoteDocument.from_text(text)
            if parsed.note_type is not note_type or parsed.category is not category:
                message = "Note text does not match the requested type and category"
                raise NoteParseError(message)
            content = text

        target_directory = self.contained(self.directory_for(note_type, category))
        if target_directory.exists() and not target_directory.is_dir():
            message = f"Note directory is not a directory: {target_directory}"
            raise VaultError(message)

        name = afanes.core.names.safe_filename(reference_name)
        scheme = ReferenceScheme.for_note(note_type, category)
        snapshot = self.scan()
        if snapshot.catalog.candidates(scheme, name):
            message = f"A {scheme.value} note named {name!r} already exists"
            raise NameCollisionError(message)

        target = target_directory / f"{name}{NOTE_SUFFIX}"
        folded_name = target.name.casefold()
        if target_directory.is_dir() and any(
            child.name.casefold() == folded_name for child in target_directory.iterdir()
        ):
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)

        target_directory.mkdir(parents=True, exist_ok=True)
        afanes.core.atomic.write_text_atomic(target, content)
        return target

    def create_project_action(
        self,
        title: str,
        project: NoteReference,
        *,
        status: Status | None = Status.ACTIVE,
        due_date: datetime.date | None = None,
        people: Iterable[str] = (),
    ) -> Path:
        """Create an action linked to a resolved project.

        Parameters
        ----------
        title : str
            Human title for the action. The first line becomes the note's
            heading and the sanitized title becomes its identity.
        project : NoteReference
            Project reference to write into the action's ``project``
            frontmatter. It must use the ``project`` scheme and resolve
            uniquely in the current vault.
        status : Status | None
            Initial action status. ``None`` omits the key entirely. Defaults
            to ``active``.
        due_date : datetime.date | None
            Optional calendar due date.
        people : Iterable[str]
            Person names assigned to the action. Names may be unresolved.

        Returns
        -------
        Path
            Absolute path to the created action.

        Raises
        ------
        VaultError
            If the title is blank, the project reference does not resolve, or
            the destination is not a directory.
        InvalidReferenceError
            If ``project`` is not a project-scheme reference or a person name
            is invalid.
        NoteParseError
            If the status is not valid for an action.
        VaultPathError
            If the action directory escapes the vault.
        NameCollisionError
            If the generated filename cannot be made unique.

        Notes
        -----
        Existing action identities are preserved: a collision receives the
        smallest available numeric suffix. Only the new action is written; the
        project note is never changed. The write is atomic.
        """
        trimmed = title.strip()
        if not trimmed:
            message = "An action needs a title"
            raise VaultError(message)
        if project.scheme is not ReferenceScheme.PROJECT or not project.name.strip():
            message = "An action needs a project reference"
            raise InvalidReferenceError(message)
        if status is not None and status not in NoteType.ACTION.allowed_statuses:
            message = "Status is not valid for an action"
            raise NoteParseError(message)

        snapshot = self.scan()
        resolution = snapshot.catalog.resolve(project)
        if resolution.outcome is not ResolutionOutcome.RESOLVED:
            message = f"Project reference does not resolve: {project.name}"
            raise VaultError(message)

        people_references = tuple(self._person_reference(name) for name in people)
        target_directory = self.contained(self.directory_for(NoteType.ACTION))
        if target_directory.exists() and not target_directory.is_dir():
            message = f"Note directory is not a directory: {target_directory}"
            raise VaultError(message)
        target_directory.mkdir(parents=True, exist_ok=True)

        taken = {
            note.name
            for note in snapshot.notes
            if ReferenceScheme.for_note(note.note_type, note.category) is ReferenceScheme.NOTE
        }
        taken.update(entry.stem for entry in target_directory.iterdir())
        taken.update(entry.name for entry in target_directory.iterdir())
        name = afanes.core.names.unique_name(afanes.core.names.safe_filename(trimmed), taken)

        document = self._new_note_document(NoteType.ACTION, None, status, f"# {trimmed}\n")
        raw = dict(document.raw)
        if due_date is not None:
            raw["due_date"] = due_date.isoformat()
        if people_references:
            raw["people"] = [f"{reference.scheme.value}:{reference.name}" for reference in people_references]
        raw["project"] = f"{project.scheme.value}:{project.name}"
        document = document.with_metadata(raw)

        path = target_directory / f"{name}{NOTE_SUFFIX}"
        afanes.core.atomic.write_text_atomic(path, document.to_text())
        return path

    def set_status(
        self,
        note_path: Path,
        status: Status | None,
        *,
        snapshot: VaultSnapshot | None = None,
        confirm: bool = False,
    ) -> str:
        """Change one note's workflow status without touching its body.

        Parameters
        ----------
        note_path : Path
            Relative or absolute path to an existing note inside this vault.
        status : Status | None
            New status, or ``None`` to remove the key.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.

        Returns
        -------
        str
            SHA-256 digest of the written bytes, for a later comparison.

        Raises
        ------
        VaultError
            If confirmation is missing, the note is not part of the vault, or
            the destination directory is missing.
        VaultPathError
            If the path escapes the vault or is not a note file.
        ContentChangedError
            If the file changed after the supplied snapshot was taken.
        NoteParseError
            If the current note cannot be parsed or the status is not valid
            for its type.

        Notes
        -----
        Only the ``status`` key is modified. Unknown keys, the body, and the
        newline style are preserved, and the write is atomic.
        """
        if not confirm:
            message = "Changing a status requires explicit confirmation"
            raise VaultError(message)

        source = self.contained(note_path)
        if not source.is_file() or source.suffix.casefold() != NOTE_SUFFIX:
            message = f"Not a note file: {note_path}"
            raise VaultPathError(message)
        vault = snapshot or self.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise VaultError(message)
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != note.content_hash:
            message = f"Note changed on disk: {note_path}"
            raise ContentChangedError(message)

        document = NoteDocument.from_text(data.decode("utf-8"))
        raw = dict(document.raw)
        if status is None:
            raw.pop("status", None)
        else:
            raw["status"] = status.value
        text = document.with_metadata(raw).to_text()
        afanes.core.atomic.write_text_atomic(source, text)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def recreate_page(self, note_path: Path, text: str) -> str:
        """Recreate a note that disappeared after it was read for editing.

        Parameters
        ----------
        note_path : Path
            Original relative or absolute path of the missing note.
        text : str
            Complete text to write. It is written as provided and is not
            parsed, so a raw rescue draft can be recreated as typed.

        Returns
        -------
        str
            SHA-256 digest of the written bytes.

        Raises
        ------
        VaultPathError
            If the path escapes the vault.
        ContentChangedError
            If a file already exists at the path.
        VaultError
            If the destination directory is missing or the write fails.

        Notes
        -----
        This is an explicit recovery action, not a normal save: the caller has
        confirmed that the draft should replace the missing file. It never
        overwrites an existing file.
        """
        source = self.contained(note_path)
        if source.exists():
            message = f"Note already exists: {note_path}"
            raise ContentChangedError(message)
        if not source.parent.is_dir():
            message = f"Destination directory does not exist: {source.parent}"
            raise VaultError(message)
        afanes.core.atomic.write_text_atomic(source, text)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def capture(self, text: str) -> Path:
        """Capture raw text as an unclassified note in this vault's inbox.

        Parameters
        ----------
        text : str
            Captured thought. The first non-blank line becomes the filename
            stem and receives a level-1 heading marker in the body.

        Returns
        -------
        Path
            Absolute path to the created note.

        Raises
        ------
        EmptyCaptureError
            If ``text`` contains no non-blank line.
        VaultPathError
            If the inbox directory escapes the vault.
        VaultError
            If the inbox path is not a directory or the note cannot be written.

        Notes
        -----
        The complete text becomes the Markdown body. ``# `` is inserted at the
        start of the first non-blank line unless its first non-whitespace
        character is already ``#``. All other text, including leading blank
        lines, is preserved. The note declares only ``type: note``; no status,
        project, people, due date, or references are inferred. The inbox
        directory is created on demand. This method performs blocking file I/O.
        """
        lines = text.splitlines(keepends=True)
        first_index = next((index for index, line in enumerate(lines) if line.strip()), None)
        if first_index is None:
            message = "A captured thought must contain text"
            raise EmptyCaptureError(message)
        first_line = lines[first_index]
        body_lines = list(lines)
        if not first_line.lstrip().startswith("#"):
            body_lines[first_index] = f"# {first_line}"
        return self.create(
            first_line,
            NoteType.NOTE,
            body="".join(body_lines),
            status=None,
        )

    def move(
        self,
        note_path: Path,
        destination_directory: Path,
        *,
        confirm: bool = False,
    ) -> Path:
        """Move a note between directories without touching links.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        destination_directory : Path
            Classification directory inside the vault. Missing directories are
            created.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``; user interfaces ask the user first.

        Returns
        -------
        Path
            Absolute path to the moved note.

        Raises
        ------
        VaultError
            If confirmation is missing or the destination is not a directory.
        VaultPathError
            If the note or destination escapes the vault, or the source is not
            a Markdown note.
        NameCollisionError
            If the destination already contains a file with the same name.
        """
        if not confirm:
            message = "Directory moves require explicit confirmation"
            raise VaultError(message)

        source = self.contained(note_path)
        if not source.is_file() or source.suffix.casefold() != NOTE_SUFFIX:
            message = f"Not a note file: {note_path}"
            raise VaultPathError(message)

        destination = self.contained(destination_directory)
        if destination.exists() and not destination.is_dir():
            message = f"Move destination is not a directory: {destination}"
            raise VaultError(message)
        destination.mkdir(parents=True, exist_ok=True)

        target = destination / source.name
        if target.exists():
            message = f"Destination already contains a note named {source.name!r}"
            raise NameCollisionError(message)

        source.replace(target)
        return target

    def plan_rename(
        self,
        note_path: Path,
        new_title: str,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> RenamePreview:
        """Plan a rename without changing any file.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        new_title : str
            Requested name for the note's identity. It is sanitized before
            comparison and use.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        RenamePreview
            Target path, affected notes, reference count, and content hashes
            taken at planning time.

        Raises
        ------
        VaultError
            If the note is not part of the vault snapshot.
        NameCollisionError
            If the sanitized name is already used in the same scheme or the
            target filename already exists.
        """
        source = self.contained(note_path)
        vault = snapshot or self.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise VaultError(message)

        new_name = afanes.core.names.safe_filename(new_title)
        scheme = ReferenceScheme.for_note(note.note_type, note.category)
        target = source.with_name(f"{new_name}{NOTE_SUFFIX}")
        same_name = afanes.core.names.normalize_name(new_name) == afanes.core.names.normalize_name(note.name)

        if not same_name:
            existing = vault.catalog.candidates(scheme, new_name)
            if any(not VaultPath.same(path, source) for path in existing):
                message = f"A {scheme.value} note named {new_name!r} already exists"
                raise NameCollisionError(message)
            if target.exists():
                message = f"Destination already exists: {target}"
                raise NameCollisionError(message)

        affected = () if same_name else vault.affected_sites(source)
        hashes = {site.path: vault.hash_for_note(site.path) for site in affected}

        heading_update = False
        if not same_name:
            try:
                data = source.read_bytes()
                document = NoteDocument.from_text(data.decode("utf-8"))
            except (OSError, UnicodeDecodeError, AfanesError) as exc:
                message = f"Could not inspect the note before renaming: {source}"
                raise VaultError(message) from exc
            heading_update = document.title == note.name
            if heading_update:
                hashes[source] = hashlib.sha256(data).hexdigest()

        return RenamePreview(
            note_path=source,
            target_path=target,
            scheme=scheme,
            old_name=note.name,
            new_name=new_name,
            heading_update=heading_update,
            affected=affected,
            reference_count=sum(site.reference_count for site in affected),
            content_hashes=hashes,
        )

    def apply_rename(
        self,
        preview: RenamePreview,
        *,
        confirm: bool = False,
    ) -> RenameReport:
        """Apply a rename preview and rewrite resolving references.

        Parameters
        ----------
        preview : RenamePreview
            Plan produced by :meth:`plan_rename`. Re-applying the same preview
            is safe and completes any remaining rewrites.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.

        Returns
        -------
        RenameReport
            Renamed flag plus the updated, skipped, unchanged, and failed
            notes.

        Raises
        ------
        VaultError
            If confirmation is missing or the note cannot be found.
        NameCollisionError
            If the target path appeared after planning.
        """
        if not confirm:
            message = "Renames require explicit confirmation"
            raise VaultError(message)

        source = self.contained(preview.note_path)
        target = self.contained(preview.target_path)
        renamed = False

        if source.exists():
            if target.exists() and not VaultPath.same(source, target):
                message = f"Destination already exists: {target}"
                raise NameCollisionError(message)
            source.replace(target)
            renamed = True
        elif not target.exists():
            message = f"Note no longer exists: {preview.note_path}"
            raise VaultError(message)

        old_reference = NoteReference(scheme=preview.scheme, name=preview.old_name)
        new_reference = NoteReference(scheme=preview.scheme, name=preview.new_name)
        updated: list[Path] = []
        skipped: list[Path] = []
        unchanged: list[Path] = []
        failed: list[RewriteFailure] = []

        if preview.heading_update:
            heading_updated, heading_skipped, heading_unchanged, heading_failed = self._apply_heading_update(
                preview, source, target, old_reference, new_reference
            )
            updated.extend(heading_updated)
            skipped.extend(heading_skipped)
            unchanged.extend(heading_unchanged)
            failed.extend(heading_failed)

        site_updated, site_skipped, site_unchanged, site_failed = self._apply_reference_sites(
            preview,
            source,
            target,
            old_reference,
            new_reference,
            skip_source=preview.heading_update,
        )
        updated.extend(site_updated)
        skipped.extend(site_skipped)
        unchanged.extend(site_unchanged)
        failed.extend(site_failed)

        return RenameReport(
            renamed=renamed,
            updated=tuple(updated),
            skipped=tuple(skipped),
            unchanged=tuple(unchanged),
            failed=tuple(failed),
        )

    def _apply_heading_update(
        self,
        preview: RenamePreview,
        source: Path,
        target: Path,
        old_reference: NoteReference,
        new_reference: NoteReference,
    ) -> tuple[tuple[Path, ...], tuple[Path, ...], tuple[Path, ...], tuple[RewriteFailure, ...]]:
        """Apply the heading update and classify the outcome."""
        try:
            data = target.read_bytes()
        except OSError as exc:
            return ((), (), (), (RewriteFailure(path=target, message=str(exc)),))
        if hashlib.sha256(data).hexdigest() != preview.content_hashes.get(source):
            return ((), (target,), (), ())
        try:
            changed = self._rewrite_renamed_note(
                target,
                data,
                old_reference,
                new_reference,
                preview.new_name,
            )
        except (OSError, UnicodeDecodeError, AfanesError) as exc:
            return ((), (), (), (RewriteFailure(path=target, message=str(exc)),))
        if changed:
            return ((target,), (), (), ())
        return ((), (), (target,), ())

    def _apply_reference_sites(
        self,
        preview: RenamePreview,
        source: Path,
        target: Path,
        old_reference: NoteReference,
        new_reference: NoteReference,
        *,
        skip_source: bool,
    ) -> tuple[list[Path], list[Path], list[Path], list[RewriteFailure]]:
        """Rewrite the preview's referring notes, optionally skipping the renamed note."""
        updated: list[Path] = []
        skipped: list[Path] = []
        unchanged: list[Path] = []
        failed: list[RewriteFailure] = []
        for site in preview.affected:
            if skip_source and VaultPath.same(site.path, source):
                continue
            read_path = target if VaultPath.same(site.path, source) else site.path
            try:
                data = read_path.read_bytes()
            except OSError as exc:
                failed.append(RewriteFailure(path=read_path, message=str(exc)))
                continue
            if hashlib.sha256(data).hexdigest() != preview.content_hashes.get(site.path):
                skipped.append(read_path)
                continue

            try:
                changed = self._rewrite_note(read_path, data, old_reference, new_reference)
            except (OSError, UnicodeDecodeError, AfanesError) as exc:
                failed.append(RewriteFailure(path=read_path, message=str(exc)))
                continue
            if changed:
                updated.append(read_path)
            else:
                unchanged.append(read_path)
        return updated, skipped, unchanged, failed

    def plan_reference_repair(
        self,
        old: NoteReference,
        new: NoteReference,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> ReferenceRepairPreview:
        """Plan a rewrite of one reference name to another without writing.

        Parameters
        ----------
        old : NoteReference
            Reference name currently written in the vault.
        new : NoteReference
            Replacement reference name. It must use the same scheme as ``old``.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        ReferenceRepairPreview
            Referring notes, per-note counts, and content hashes captured at
            planning time. Empty when no note contains the old reference.

        Raises
        ------
        VaultError
            If the two references use different schemes.

        Notes
        -----
        Matching compares reference keys (scheme and normalized name) rather
        than resolution. It therefore finds references to a name that has no
        page yet, which is exactly the unsafe-link repair case. This method
        performs blocking file I/O when it scans, and never writes.
        """
        if old.scheme is not new.scheme:
            message = "Reference repair must stay within one scheme"
            raise VaultError(message)

        vault = snapshot or self.scan()
        old_key = ReferenceKey.from_reference(old)
        sites: list[ReferenceSite] = []
        hashes: dict[Path, str] = {}
        for note in vault.notes:
            count = sum(1 for reference in note.references if ReferenceKey.from_reference(reference) == old_key)
            if count:
                sites.append(ReferenceSite(path=note.path, reference_count=count))
                hashes[note.path] = note.content_hash
        return ReferenceRepairPreview(old=old, new=new, sites=tuple(sites), content_hashes=hashes)

    def apply_reference_repair(
        self,
        preview: ReferenceRepairPreview,
        *,
        confirm: bool = False,
    ) -> RewriteReport:
        """Apply a reference repair after confirmation.

        Parameters
        ----------
        preview : ReferenceRepairPreview
            Plan produced by :meth:`plan_reference_repair`.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.

        Returns
        -------
        RewriteReport
            Updated, skipped, unchanged, and failed notes.

        Raises
        ------
        VaultError
            If confirmation is missing.

        Notes
        -----
        Each referring note is rewritten atomically only when its content still
        matches the hash captured at planning time. A changed note is skipped
        and reported. Re-applying the same preview is safe: notes already
        rewritten by an earlier run are skipped by the hash guard.
        """
        if not confirm:
            message = "Reference repairs require explicit confirmation"
            raise VaultError(message)

        updated: list[Path] = []
        skipped: list[Path] = []
        unchanged: list[Path] = []
        failed: list[RewriteFailure] = []
        for site in preview.sites:
            try:
                data = site.path.read_bytes()
            except OSError as exc:
                failed.append(RewriteFailure(path=site.path, message=str(exc)))
                continue
            if hashlib.sha256(data).hexdigest() != preview.content_hashes.get(site.path):
                skipped.append(site.path)
                continue
            try:
                changed = self._rewrite_note(site.path, data, preview.old, preview.new)
            except (OSError, UnicodeDecodeError, AfanesError) as exc:
                failed.append(RewriteFailure(path=site.path, message=str(exc)))
                continue
            if changed:
                updated.append(site.path)
            else:
                unchanged.append(site.path)
        return RewriteReport(
            updated=tuple(updated),
            skipped=tuple(skipped),
            unchanged=tuple(unchanged),
            failed=tuple(failed),
        )

    def plan_trash(
        self,
        note_path: Path,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> TrashPreview:
        """Report inbound references and the trash destination without writing.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        TrashPreview
            Destination inside ``trash/``, inbound reference count, and the
            notes that contain those references.

        Raises
        ------
        VaultError
            If the note is not part of the vault snapshot.
        """
        source = self.contained(note_path)
        vault = snapshot or self.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise VaultError(message)

        trash_directory = self._existing_directory(self.root, TRASH_DIRECTORY)
        taken: set[str] = set()
        if trash_directory.is_dir():
            taken.update(entry.stem for entry in trash_directory.iterdir())
            taken.update(entry.name for entry in trash_directory.iterdir())
        trash_name = afanes.core.names.unique_name(source.stem, taken)
        affected = vault.affected_sites(source)
        return TrashPreview(
            note_path=source,
            trash_path=trash_directory / f"{trash_name}{NOTE_SUFFIX}",
            reference_count=sum(site.reference_count for site in affected),
            affected_notes=tuple(site.path for site in affected),
        )

    @staticmethod
    def _person_reference(name: str) -> NoteReference:
        """Build a person reference from a name supplied by the user."""
        trimmed = name.strip()
        if not trimmed:
            message = "A person reference needs a name"
            raise ProcessingError(message)
        return NoteReference(scheme=ReferenceScheme.PERSON, name=trimmed)

    @staticmethod
    def _project_reference(name: str) -> NoteReference:
        """Build a project reference from a name supplied by the user."""
        trimmed = name.strip()
        if not trimmed:
            message = "A project reference needs a name"
            raise ProcessingError(message)
        return NoteReference(scheme=ReferenceScheme.PROJECT, name=trimmed)

    @staticmethod
    def _new_note_document(
        note_type: NoteType,
        category: ReferenceCategory | None,
        status: Status | None,
        body: str,
    ) -> NoteDocument:
        """Build the canonical document for a newly created note."""
        normalized_body = body.replace("\r\n", "\n").replace("\r", "\n").removeprefix("\ufeff")
        raw: dict[str, object] = {"type": note_type.value}
        if category is not None:
            raw["category"] = category.value
        if status is not None:
            raw["status"] = status.value
        return NoteDocument(
            raw=raw,
            body=normalized_body,
            newline="\n",
            has_frontmatter=True,
            note_type=note_type,
            references=(),
            category=category,
            status=status,
        )

    def _require_inbox_note(self, source: Path) -> None:
        """Require a source path to be under the vault's inbox directory."""
        relative = source.relative_to(self.root)
        if (
            len(relative.parts) < _MIN_INBOX_PART_COUNT
            or relative.parts[0].casefold() != INBOX_DIRECTORY.name.casefold()
        ):
            message = "Only notes in the inbox can be processed"
            raise ProcessingError(message)

    @staticmethod
    def _existing_directory(parent: Path, name: Path) -> Path:
        """Return an existing case variant of a directory, or the canonical path."""
        candidate = parent / name
        if candidate.is_dir() or not parent.is_dir():
            return candidate
        folded = name.name.casefold()
        matches = sorted(
            (child for child in parent.iterdir() if child.is_dir() and child.name.casefold() == folded),
            key=lambda child: child.name,
        )
        return matches[0] if matches else candidate

    @staticmethod
    def _rewrite_note(
        path: Path,
        data: bytes,
        old: NoteReference,
        new: NoteReference,
    ) -> bool:
        """Rewrite body and frontmatter references in one note atomically."""
        document = NoteDocument.from_text(data.decode("utf-8"))
        rewrite = afanes.core.links.MarkdownBody(document.body).rewrite_references(old, new)
        rewritten, frontmatter_count = document.rewrite_references(old, new)
        if rewrite.count + frontmatter_count == 0:
            return False

        final = rewritten.with_body(rewrite.text)
        text = final.to_text()
        reader = afanes.core.links.ReferenceReader()
        Vault._verify_rewrite(text, old, reader)
        afanes.core.atomic.write_text_atomic(path, text)
        return True

    @staticmethod
    def _rewrite_renamed_note(
        path: Path,
        data: bytes,
        old: NoteReference,
        new: NoteReference,
        new_title: str,
    ) -> bool:
        """Rewrite a renamed note's heading and references atomically."""
        current = data.decode("utf-8")
        document = NoteDocument.from_text(current)
        rewrite = afanes.core.links.MarkdownBody(document.body).rewrite_references(old, new)
        rewritten, _ = document.rewrite_references(old, new)
        final = rewritten.with_body(rewrite.text).with_heading(new_title)
        text = final.to_text()
        if text == current:
            return False
        reader = afanes.core.links.ReferenceReader()
        Vault._verify_rewrite(text, old, reader)
        afanes.core.atomic.write_text_atomic(path, text)
        return True

    @staticmethod
    def _verify_rewrite(
        text: str,
        old: NoteReference,
        reader: afanes.core.links.ReferenceReader,
    ) -> None:
        """Confirm that a rewritten note no longer names the old reference."""
        document = NoteDocument.from_text(text)
        old_key = ReferenceKey.from_reference(old)
        body_references = reader.extract(document.body)
        remaining = body_references + list(document.references)
        if any(ReferenceKey.from_reference(reference) == old_key for reference in remaining):
            message = "Rewritten note still contains the old reference"
            raise ReferenceRewriteError(message)

    def trash(
        self,
        note_path: Path,
        *,
        confirm: bool = False,
        snapshot: VaultSnapshot | None = None,
    ) -> int:
        """Move a note to ``trash/`` after confirmation without rewriting references.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.
        snapshot : VaultSnapshot | None
            Pre-built scan used to report inbound references, or ``None`` to
            scan the vault.

        Returns
        -------
        int
            Number of inbound references reported before trashing.

        Raises
        ------
        VaultError
            If confirmation is missing, the note is not part of the vault, or
            the move fails.
        NameCollisionError
            If the trash destination appears after planning.
        """
        if not confirm:
            message = "Trashing requires explicit confirmation"
            raise VaultError(message)

        preview = self.plan_trash(note_path, snapshot=snapshot)
        if preview.trash_path.exists():
            message = f"Trash destination already exists: {preview.trash_path}"
            raise NameCollisionError(message)
        try:
            preview.trash_path.parent.mkdir(parents=True, exist_ok=True)
            preview.note_path.replace(preview.trash_path)
        except OSError as exc:
            message = f"Could not move the note to trash: {preview.note_path}"
            raise VaultError(message) from exc
        return preview.reference_count


@dataclasses.dataclass(frozen=True, slots=True)
class VaultCreation:
    """Directories produced by one vault creation.

    Attributes
    ----------
    vault : Vault
        The created and seeded vault.
    created_directories : tuple[pathlib.Path, ...]
        Intermediate directories created for the vault path, outermost first.
        The vault root itself is not included.
    seeded_directories : tuple[pathlib.Path, ...]
        Default folders created inside the vault, in layout order.
    """

    vault: Vault
    created_directories: tuple[Path, ...]
    seeded_directories: tuple[Path, ...]
