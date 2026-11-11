# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Note type vocabulary used by the reference engine and the vault."""

from enum import StrEnum


class NoteType(StrEnum):
    """Kinds of notes a vault can contain.

    Attributes
    ----------
    NOTE : str
        Free-form document note.
    ACTION : str
        Single actionable unit.
    PROJECT : str
        Outcome that groups related actions.
    REFERENCE : str
        Non-actionable knowledge kept for later consultation.
    PERSON : str
        Contact page referenced by people links.
    """

    NOTE = "note"
    ACTION = "action"
    PROJECT = "project"
    REFERENCE = "reference"
    PERSON = "person"
