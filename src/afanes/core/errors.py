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


class VaultSchemaError(VaultError):
    """Base class for vault settings-file failures.

    Notes
    -----
    The settings file records the on-disk vault schema. Every failure here is
    a vault refusal, and the existing file is preserved byte for byte.
    """


class VaultSchemaMissingError(VaultSchemaError):
    """Raised when a folder has no ``afanes.yaml`` settings file."""


class VaultSchemaInvalidError(VaultSchemaError):
    """Raised when the settings file does not match the current schema shape.

    Notes
    -----
    The file may be a symlink, a directory, oversized, invalid UTF-8 or YAML,
    or contain extra or duplicate keys. The application never repairs or
    rewrites it.
    """


class VaultSchemaUnsupportedError(VaultSchemaError):
    """Raised when the settings file declares a different schema version.

    Notes
    -----
    Before 1.0, older schemas may be refused without a migration. A newer
    schema is always refused. The message distinguishes the two cases.
    """


class VaultSchemaWriteError(VaultSchemaError):
    """Raised when the settings file cannot be written."""


class VaultSchemaNotAdoptableError(VaultSchemaError):
    """Raised when adoption targets an ineligible folder."""


class ContentChangedError(VaultError):
    """Raised when a note changed on disk after it was read for editing."""


class TemplateError(VaultError):
    """Base class for failures in bundled starter content.

    Notes
    -----
    Every template failure is a vault creation refusal, so the interface and
    the command line report it with the same path as an unseeded directory.
    """


class UnknownTemplateError(TemplateError):
    """Raised when a requested template identifier is not in the catalog.

    Notes
    -----
    The message lists the valid identifiers so a mistyped command can be
    corrected without opening the interface.
    """


class TemplateContentError(TemplateError):
    """Raised when bundled content violates the vault format.

    Notes
    -----
    The message names the offending template and note. Nothing is written when
    this error is raised.
    """


class TemplateWriteError(TemplateError):
    """Raised when a bundled note cannot be written into a new vault.

    Notes
    -----
    Notes written before the failure remain in place, and the message names
    both the failing note and the notes already written.
    """


class TemplateCardError(TemplateError):
    """Base class for failures in reference template cards.

    Notes
    -----
    Template cards participate in vault creation, so their failures are vault
    creation refusals and share the same interface message as broken starter
    content.
    """


class TemplateCardContentError(TemplateCardError):
    """Raised when a bundled template card violates the card format.

    Notes
    -----
    The message names the offending card. Nothing is written when this error is
    raised, so a broken bundle cannot seed a partial vault.
    """


class TemplateCardWriteError(TemplateCardError):
    """Raised when a bundled template card cannot be written into a new vault.

    Notes
    -----
    Cards written before the failure remain in place, and the message names
    both the failing card and the cards already written.
    """


class NoteParseError(AfanesError):
    """Raised when a note's frontmatter or metadata cannot be parsed."""


class RetiredValueError(NoteParseError):
    """Raised when a note uses a value retired by the three-note model.

    Notes
    -----
    The message names the retired value and its replacement so an old note can
    be repaired by hand in raw rescue mode. The file is never rewritten.
    """


class StepMetadataError(AfanesError):
    """Raised when step metadata cannot be written as one valid HTML comment."""


class StepEditError(AfanesError):
    """Raised when a step line cannot be rewritten safely."""


class ProcessingError(VaultError):
    """Raised when a processing plan is invalid or cannot be applied."""


class EmptyCaptureError(AfanesError):
    """Raised when a capture contains no non-blank text."""


class InvalidReferenceError(AfanesError):
    """Raised when a value is not a valid internal note reference."""


class RetiredReferenceSchemeError(InvalidReferenceError):
    """Raised when a destination uses the retired ``person`` scheme.

    Notes
    -----
    The message names ``note:`` as the replacement so a hand repair is
    obvious. No link is resolved or rewritten automatically.
    """


class NameCollisionError(AfanesError):
    """Raised when a note name is already used within its scheme."""


class ReferenceRewriteError(AfanesError):
    """Raised when a rename cannot rewrite a referring note safely."""
