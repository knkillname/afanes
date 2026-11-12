# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Note vocabulary used by the reference engine, the parser, and the vault."""

import dataclasses
import typing
from enum import StrEnum


class Status(StrEnum):
    """Workflow states for projects and references.

    Attributes
    ----------
    ACTIVE : str
        Available or currently in progress.
    WAITING : str
        Delegated or blocked on someone else.
    DONE : str
        Completed.
    CANCELLED : str
        Abandoned without completion.
    ARCHIVED : str
        Kept but hidden from active views.
    LATER : str
        Deferred for possible future attention.
    """

    ACTIVE = "active"
    WAITING = "waiting"
    DONE = "done"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    LATER = "later"


# Public per-type status policy. Absence of a status is always allowed; these
# sets constrain a status only when the key is present.
PROJECT_STATUSES: frozenset[Status] = frozenset(
    {
        Status.ACTIVE,
        Status.WAITING,
        Status.DONE,
        Status.CANCELLED,
        Status.ARCHIVED,
        Status.LATER,
    }
)
REFERENCE_STATUSES: frozenset[Status] = frozenset({Status.LATER, Status.ARCHIVED})
NOTE_STATUSES: frozenset[Status] = frozenset()


class NoteType(StrEnum):
    """Kinds of notes a vault can contain.

    Attributes
    ----------
    NOTE : str
        Unclarified capture that still needs an explicit processing outcome.
    REFERENCE : str
        Non-actionable knowledge kept for later consultation.
    PROJECT : str
        Outcome whose body contains the steps that advance it.
    """

    NOTE = "note"
    PROJECT = "project"
    REFERENCE = "reference"

    @property
    def allowed_statuses(self) -> frozenset[Status]:
        """Return the statuses valid for this note type.

        Returns
        -------
        frozenset[Status]
            Statuses allowed when a status key is present. An absent status is
            always allowed and is not represented in the result.
        """
        if self is NoteType.PROJECT:
            return PROJECT_STATUSES
        if self is NoteType.REFERENCE:
            return REFERENCE_STATUSES
        return NOTE_STATUSES


@dataclasses.dataclass(frozen=True, slots=True, eq=False)
class CategoryLabel:
    """Free-form label that groups reference notes and selects a folder.

    Attributes
    ----------
    value : str
        Written label, preserving its original case and spacing.

    Raises
    ------
    ValueError
        If the label is blank, is a traversal segment, or contains a path
        separator. The frontmatter parser converts this into a domain error.

    Notes
    -----
    Labels are not a closed list and do not select a reference scheme. Two
    labels that differ only in case compare equal and produce the same hash, so
    grouping and folder reuse are case-insensitive while the written form is
    preserved.
    """

    value: str

    def __post_init__(self) -> None:
        r"""Validate that the label is one non-empty path segment.

        Raises
        ------
        ValueError
            If the label is blank, is ``.`` or ``..``, or contains ``/`` or
            ``\\``.
        """
        label = self.value.strip()
        if not label:
            message = "A category label must not be empty"
            raise ValueError(message)
        if "/" in label or "\\" in label:
            message = "A category label must be a single path segment"
            raise ValueError(message)
        if label in {".", ".."}:
            message = "A category label must name a folder, not a traversal"
            raise ValueError(message)

    @property
    def key(self) -> str:
        """Return the case-folded comparison key.

        Returns
        -------
        str
            Case-folded label used for grouping and folder reuse.
        """
        return self.value.casefold()

    @typing.override
    def __eq__(self, other: object) -> bool:
        """Compare labels case-insensitively.

        Parameters
        ----------
        other : object
            Value to compare against.

        Returns
        -------
        bool
            ``True`` when ``other`` is a :class:`CategoryLabel` with the same
            case-folded value.
        """
        if not isinstance(other, CategoryLabel):
            return NotImplemented
        return self.key == other.key

    def __hash__(self) -> int:
        """Return a hash consistent with case-insensitive equality.

        Returns
        -------
        int
            Hash of the case-folded label.
        """
        return hash(self.key)
