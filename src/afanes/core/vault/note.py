# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Scanned note value types and the ordering keys they expose.

The scan result, note, path, and ordering value objects live here so the
vault service, the snapshot, and their write services can share them without
importing each other. The module performs no file I/O.
"""

import dataclasses
import datetime
from pathlib import Path

import afanes.core.names
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status
from afanes.models.step import ProjectStep

# Public default inbox storage layout.
INBOX_DIRECTORY = Path("inbox")

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
            title_key=afanes.core.names.NamePolicy.normalize(note.title),
            name_key=afanes.core.names.NamePolicy.normalize(note.name),
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
            title_key=afanes.core.names.NamePolicy.normalize(note.title),
            name_key=afanes.core.names.NamePolicy.normalize(note.name),
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
    date : NoteDate | None
        ISO partial date read from frontmatter, or ``None`` when absent or
        malformed.
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
    asked_by : str | None
        Requester name declared by a project, or ``None`` when the key is
        absent or the note is not a project.
    owner : str | None
        Accountable person or team declared by a project, or ``None`` when the
        key is absent or the note is not a project.
    """

    path: Path
    relative_path: Path
    name: str
    title: str
    note_type: NoteType
    category: CategoryLabel | None
    status: Status | None
    due_date: datetime.date | None
    date: NoteDate | None
    content_hash: str
    modified_ns: int
    body_references: tuple[NoteReference, ...]
    steps: tuple[ProjectStep, ...]
    search_text: str
    asked_by: str | None = None
    owner: str | None = None

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
    def metadata_references(self) -> tuple[NoteReference, ...]:
        """Return the role-name references declared by this note.

        Returns
        -------
        tuple[NoteReference, ...]
            One ``note:`` reference for the project owner, one for the
            requester, and one for each step owner, in that order. Repeated
            names are preserved so a rename preview can count each written
            occurrence.

        Notes
        -----
        These references come from frontmatter and step metadata, not from the
        body. They resolve through the same catalog as body references but are
        never listed as inbound body links.
        """
        names: list[str] = []
        if self.owner is not None:
            names.append(self.owner)
        if self.asked_by is not None:
            names.append(self.asked_by)
        for step in self.steps:
            names.extend(step.owners)
        return tuple(NoteReference(scheme=ReferenceScheme.NOTE, name=name) for name in names)

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
