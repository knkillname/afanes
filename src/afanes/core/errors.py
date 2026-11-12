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


class ConfigurationError(AfanesError):
    """Raised when application settings cannot be read, validated, or saved.

    Notes
    -----
    Settings live outside the vault, so this error never indicates vault
    corruption. The UI translates it into an actionable message and leaves
    the existing settings file untouched.
    """


class VaultError(AfanesError):
    """Base class for vault discovery, containment, and write failures."""


class VaultMissingError(VaultError):
    """Raised when a vault path does not exist."""


class VaultNotDirectoryError(VaultError):
    """Raised when a vault path exists but is not a directory."""


class VaultUnreadableError(VaultError):
    """Raised when a vault directory cannot be read."""


class VaultNotEmptyError(VaultError):
    """Raised when vault creation targets a directory that is not empty."""


class VaultPathError(VaultError):
    """Raised when a path escapes the vault root or is not a regular note."""


class ContentChangedError(VaultError):
    """Raised when a note changed on disk after it was read for editing."""


class NoteParseError(AfanesError):
    """Raised when a note's frontmatter or metadata cannot be parsed."""


class ProcessingError(VaultError):
    """Raised when a processing plan is invalid or cannot be applied."""


class EmptyCaptureError(AfanesError):
    """Raised when a capture contains no non-blank text."""


class InvalidReferenceError(AfanesError):
    """Raised when a value is not a valid internal note reference."""


class NameCollisionError(AfanesError):
    """Raised when a note name is already used within its scheme."""


class ReferenceRewriteError(AfanesError):
    """Raised when a rename cannot rewrite a referring note safely."""
