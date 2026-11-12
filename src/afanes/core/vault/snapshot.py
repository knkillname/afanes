# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only vault value types and the storage layout they describe.

The scan result, note, failure, path, ordering, and page value objects live
here so the vault service and its write services can share them without
importing each other. The module performs no file I/O.
"""

import dataclasses
import datetime
from enum import StrEnum
from pathlib import Path

import afanes.core.links
import afanes.core.names
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import NameCatalog, ResolutionOutcome
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteType, Status
from afanes.models.step import ProjectStep

# Public canonical note extension.
NOTE_SUFFIX = ".md"

# Public default storage layout.
INBOX_DIRECTORY = Path("inbox")
TRASH_DIRECTORY = Path("trash")
REFERENCE_DIRECTORY = Path("reference")
PROJECTS_DIRECTORY = Path("projects")
TEMPLATES_DIRECTORY = Path("templates")

MIN_INBOX_PART_COUNT = 2


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
            len(self.value.parts) >= MIN_INBOX_PART_COUNT
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
    category : CategoryLabel | None
        Declared reference category, or ``None`` for an uncategorized
        reference or a non-reference note.
    status : Status | None
        Validated workflow status, or ``None`` when absent.
    due_date : datetime.date | None
        Calendar due date read from frontmatter, or ``None`` when absent.
    content_hash : str
        SHA-256 digest of the file bytes, used as an optimistic write guard.
    modified_ns : int
        File modification time in nanoseconds since the epoch, used only for
        display ordering. It is filesystem metadata, not durable vault data.
    body_references : tuple[NoteReference, ...]
        References extracted from the Markdown body.
    steps : tuple[ProjectStep, ...]
        Task list items derived from the body of a project note. Empty for every
        other note type.
    search_text : str
        Body text used by browser search, with step metadata comments removed.
    """

    path: Path
    relative_path: Path
    name: str
    title: str
    note_type: NoteType
    category: CategoryLabel | None
    status: Status | None
    due_date: datetime.date | None
    content_hash: str
    modified_ns: int
    body_references: tuple[NoteReference, ...]
    steps: tuple[ProjectStep, ...]
    search_text: str

    @property
    def references(self) -> tuple[NoteReference, ...]:
        """Return the body references of this note.

        Returns
        -------
        tuple[NoteReference, ...]
            References extracted from the Markdown body.
        """
        return self.body_references

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
    def is_misplaced(self) -> bool:
        """Return whether an unclarified note sits outside the inbox.

        Returns
        -------
        bool
            ``True`` when the note declares ``type: note`` and is not inside
            the vault's inbox directory.
        """
        return self.note_type is NoteType.NOTE and not self.is_inbox

    @property
    def open_steps(self) -> tuple[ProjectStep, ...]:
        """Return the unchecked steps of this project in document order.

        Returns
        -------
        tuple[ProjectStep, ...]
            Unchecked steps, or an empty tuple for a non-project note.
        """
        return tuple(step for step in self.steps if not step.checked)

    @property
    def next_step(self) -> ProjectStep | None:
        """Return the first unchecked step of this project.

        Returns
        -------
        ProjectStep | None
            First unchecked step in document order, or ``None`` when the note
            is not a project or has no unchecked step.
        """
        open_steps = self.open_steps
        return open_steps[0] if open_steps else None

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
    fingerprint : tuple[tuple[str, int, int], ...]
        Change fingerprint of the files the scan walked, in the same
        ``(vault-relative path, mtime_ns, size)`` shape as
        :meth:`afanes.core.vault.service.Vault.scan_fingerprint`.
    """

    root: Path
    notes: tuple[VaultNote, ...]
    failures: tuple[VaultFailure, ...]
    catalog: NameCatalog
    fingerprint: tuple[tuple[str, int, int], ...] = ()

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
            Namespace to search, normally ``project``.
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
            if ReferenceScheme.for_note(note.note_type) is scheme
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


type PageContent = ParsedPage | UnparsedPage
