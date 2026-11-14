# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Planned-operation value objects for renames, moves, repairs, and trash.

The dataclasses live apart from the service that produces and applies them so
the planning and applying modules can share the shapes without importing each
other's behavior.
"""

import dataclasses
import datetime
from pathlib import Path
from typing import Self

import afanes.core.errors
from afanes.core.vault.snapshot import ReferenceSite
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType


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
    new_date : NoteDate | None
        Replacement note date for a log date change, or ``None`` for an
        ordinary rename.
    new_scheme : ReferenceScheme | None
        Replacement reference scheme for a cross-scheme type change, or
        ``None`` when the scheme is unchanged.
    new_type : NoteType | None
        Replacement note type written before the move, or ``None`` for an
        ordinary rename.
    new_heading : str | None
        Replacement level-1 heading written in the same atomic conversion,
        or ``None`` to preserve the current heading.
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
    new_date: NoteDate | None = None
    new_scheme: ReferenceScheme | None = None
    new_type: NoteType | None = None
    new_heading: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class RewriteFailure:
    """A referring note that could not be rewritten.

    Attributes
    ----------
    path : Path
        Absolute path to the note.
    message : afanes.core.errors.DomainMessage
        Structured failure reason rendered by the active catalog.
    """

    path: Path
    message: afanes.core.errors.DomainMessage

    @classmethod
    def from_error(cls, path: Path, error: BaseException) -> Self:
        """Build the structured report for one rewrite failure.

        Parameters
        ----------
        path : Path
            Note that could not be rewritten.
        error : BaseException
            Domain error or wrapped technical failure.

        Returns
        -------
        RewriteFailure
            Failure carrying the error's domain message or a technical detail.
        """
        if isinstance(error, afanes.core.errors.AfanesError):
            return cls(path=path, message=error.domain_message)
        message = afanes.core.errors.DomainMessage.of(
            afanes.core.errors.MessageCode.TECHNICAL_FAILURE, detail=str(error)
        )
        return cls(path=path, message=message)


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
    trashed_on : datetime.date | None
        Local calendar day recorded in the note frontmatter, or ``None`` for a
        preview that was not applied.
    source_hash : str | None
        SHA-256 digest of the note captured at planning time, or ``None`` for
        a preview built without a scan.
    """

    note_path: Path
    trash_path: Path
    reference_count: int
    affected_notes: tuple[Path, ...]
    trashed_on: datetime.date | None = None
    source_hash: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class CategoryMovePreview:
    """A reference note's category change and its destination.

    Attributes
    ----------
    note_path : Path
        Absolute path to the reference before the change.
    target_path : Path
        Absolute destination inside ``reference/<label>/`` or ``reference/``.
    category : CategoryLabel | None
        Category to write, or ``None`` to remove it.
    """

    note_path: Path
    target_path: Path
    category: CategoryLabel | None
