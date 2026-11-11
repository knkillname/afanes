# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Note vocabulary used by the reference engine, the parser, and the vault."""

from enum import StrEnum


class NoteType(StrEnum):
    """Kinds of notes a vault can contain.

    Attributes
    ----------
    NOTE : str
        Free-form document note, also the unprocessed capture type.
    ACTION : str
        Single actionable unit.
    PROJECT : str
        Outcome that groups related actions.
    REFERENCE : str
        Non-actionable knowledge kept for later consultation.
    """

    NOTE = "note"
    ACTION = "action"
    PROJECT = "project"
    REFERENCE = "reference"


class ReferenceCategory(StrEnum):
    """Categories that group reference notes.

    Attributes
    ----------
    PERSON : str
        Reference notes about people.
    """

    PERSON = "person"


class Status(StrEnum):
    """Workflow states for actionable notes and references.

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
ACTION_STATUSES: frozenset[Status] = frozenset(
    {
        Status.ACTIVE,
        Status.WAITING,
        Status.DONE,
        Status.CANCELLED,
        Status.ARCHIVED,
        Status.LATER,
    }
)
PROJECT_STATUSES: frozenset[Status] = ACTION_STATUSES
REFERENCE_STATUSES: frozenset[Status] = frozenset({Status.LATER, Status.ARCHIVED})
NOTE_STATUSES: frozenset[Status] = frozenset()


def allowed_statuses(note_type: NoteType) -> frozenset[Status]:
    """Return the statuses valid for a note type.

    Parameters
    ----------
    note_type : NoteType
        Declared note type.

    Returns
    -------
    frozenset[Status]
        Statuses allowed when a status key is present. An absent status is
        always allowed and is not represented in the result.
    """
    if note_type is NoteType.ACTION:
        return ACTION_STATUSES
    if note_type is NoteType.PROJECT:
        return PROJECT_STATUSES
    if note_type is NoteType.REFERENCE:
        return REFERENCE_STATUSES
    return NOTE_STATUSES
