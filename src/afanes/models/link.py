# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Immutable value objects for name-based internal references."""

import dataclasses
from enum import StrEnum


class ReferenceScheme(StrEnum):
    """Namespaces that an internal reference destination can address.

    Attributes
    ----------
    PROJECT : str
        Namespace for notes of type ``project``.
    NOTE : str
        Namespace for the document family: ``note`` and ``reference`` notes in
        any category.
    """

    PROJECT = "project"
    NOTE = "note"

    @classmethod
    def for_note(cls, note_type: str) -> "ReferenceScheme":
        """Map a note type to the scheme that addresses it.

        Parameters
        ----------
        note_type : str
            Declared note type value, normally a :class:`afanes.models.note.NoteType`
            member. Accepting the plain value keeps ``models.link`` independent
            of ``models.note``, so the model package stays a standard-library
            leaf.

        Returns
        -------
        ReferenceScheme
            ``project`` for a project note and ``note`` for every other note
            type.

        Notes
        -----
        A note belongs to exactly one scheme. Categories never select a
        namespace, so every reference shares the ``note`` scheme.
        """
        if note_type == "project":
            return cls.PROJECT
        return cls.NOTE


@dataclasses.dataclass(frozen=True, slots=True)
class NoteReference:
    """A reference to a note by scheme and name.

    Attributes
    ----------
    scheme : ReferenceScheme
        Namespace that determines which note types the reference can resolve.
    name : str
        Name as written in the source. Matching normalizes this value in
        ``core.links``; the stored form is preserved for display and rewriting.
    label : str | None
        Markdown link label, or ``None`` for a frontmatter value. Labels are
        presentation only and never participate in resolution.

    Notes
    -----
    The value object performs no validation. Construction from untrusted text
    must go through ``core.links.ReferenceParser``.
    """

    scheme: ReferenceScheme
    name: str
    label: str | None = None
