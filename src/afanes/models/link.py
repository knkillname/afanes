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
    must go through ``core.links.parse_reference``.
    """

    scheme: ReferenceScheme
    name: str
    label: str | None = None
