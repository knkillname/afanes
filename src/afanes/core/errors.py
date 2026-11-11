# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Domain exceptions raised by Afanes core services.

Every public failure in ``core/`` and ``models/`` is expressed through this
hierarchy so the UI and CLI can translate errors at their boundary. The names
deliberately avoid reusing built-in exception names.
"""


class AfanesError(Exception):
    """Base class for every Afanes domain error.

    Notes
    -----
    Callers at the UI and CLI boundary translate these errors into concise,
    actionable messages. Library code never prints them.
    """


class VaultError(AfanesError):
    """Base class for vault discovery, containment, and write failures."""


class VaultPathError(VaultError):
    """Raised when a path escapes the vault root or is not a regular note."""


class NoteParseError(AfanesError):
    """Raised when a note's frontmatter or metadata cannot be parsed."""


class InvalidReferenceError(AfanesError):
    """Raised when a value is not a valid internal note reference."""


class NameCollisionError(AfanesError):
    """Raised when a note name is already used within its scheme."""


class ReferenceRewriteError(AfanesError):
    """Raised when a rename cannot rewrite a referring note safely."""
