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
    PERSON : str
        Namespace for notes of type ``person``.
    PROJECT : str
        Namespace for notes of type ``project``.
    NOTE : str
        Namespace for the document family: ``note``, ``action``, and
        ``reference``.
    """

    PERSON = "person"
    PROJECT = "project"
    NOTE = "note"

    @classmethod
    def for_note(cls, note_type: str, category: str | None = None) -> "ReferenceScheme":
        """Map a note type and optional category to the scheme that addresses it.

        Parameters
        ----------
        note_type : str
            Declared note type value, normally a :class:`afanes.models.note.NoteType`
            member. Accepting the plain value keeps ``models.link`` independent
            of ``models.note``, so the model package stays a standard-library
            leaf.
        category : str | None
            Reference category value when the note is a reference. ``None``
            means an uncategorized reference or a non-reference note.

        Returns
        -------
        ReferenceScheme
            ``person`` for a reference with category ``person``, ``project``
            for a project note, and ``note`` for the document family.

        Notes
        -----
        A note belongs to exactly one scheme. A categorized reference is not
        also addressable through the ``note`` scheme.
        """
        if note_type == "project":
            return cls.PROJECT
        if note_type == "reference" and category == "person":
            return cls.PERSON
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
