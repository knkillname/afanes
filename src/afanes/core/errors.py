# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Domain exceptions raised by Afanes core services.

Every public failure in ``core/`` and ``models/`` is expressed through this
hierarchy so the UI and CLI can translate errors at their boundary. The names
deliberately avoid reusing built-in exception names.
"""

import dataclasses
from enum import StrEnum
from typing import Self


class MessageCode(StrEnum):
    """Stable identity of one domain message.

    Notes
    -----
    Each member names one stable failure family. The English template lives in
    ``afanes.i18n.messages.en`` and the Spanish translation in the
    ``afanes-messages`` catalog.
    """

    TECHNICAL_FAILURE = "technical-failure"
    UI_VAULT_MISSING = "ui-vault-missing"
    UI_VAULT_NOT_DIRECTORY = "ui-vault-not-directory"
    UI_VAULT_UNREADABLE = "ui-vault-unreadable"
    UI_VAULT_NOT_EMPTY = "ui-vault-not-empty"
    UI_NEW_VAULT_TEMPLATE_FAILED = "ui-new-vault-template-failed"
    UI_VAULT_NOT_OPEN = "ui-vault-not-open"
    SETTINGS_NOT_OBJECT = "settings-not-object"
    SETTINGS_VERSION_UNSUPPORTED = "settings-version-unsupported"
    SETTINGS_VAULT_MISSING = "settings-vault-missing"
    SETTINGS_VAULT_RELATIVE = "settings-vault-relative"
    SETTINGS_LOG_MODES_NOT_OBJECT = "settings-log-modes-not-object"
    SETTINGS_LOG_MODES_INVALID = "settings-log-modes-invalid"
    SETTINGS_READ_FAILED = "settings-read-failed"
    SETTINGS_JSON_INVALID = "settings-json-invalid"
    SETTINGS_DIRECTORY_FAILED = "settings-directory-failed"
    SETTINGS_VAULT_NOT_DIRECTORY = "settings-vault-not-directory"
    SETTINGS_WRITE_FAILED = "settings-write-failed"
    SETTINGS_REMOVE_FAILED = "settings-remove-failed"
    PREFERENCES_NOT_OBJECT = "preferences-not-object"
    PREFERENCES_VERSION_UNSUPPORTED = "preferences-version-unsupported"
    PREFERENCES_LANGUAGE_INVALID = "preferences-language-invalid"
    PREFERENCES_READ_FAILED = "preferences-read-failed"
    PREFERENCES_JSON_INVALID = "preferences-json-invalid"
    PREFERENCES_DIRECTORY_FAILED = "preferences-directory-failed"
    PREFERENCES_WRITE_FAILED = "preferences-write-failed"
    DESTINATION_DIRECTORY_MISSING = "destination-directory-missing"
    NOTE_MISSING = "note-missing"
    NOT_A_NOTE_FILE = "not-a-note-file"
    NOTE_NOT_IN_VAULT = "note-not-in-vault"
    DESTINATION_EXISTS = "destination-exists"
    NOTE_NAME_EXISTS = "note-name-exists"
    NOTE_CHANGED_ON_DISK = "note-changed-on-disk"
    NOTE_ALREADY_HAS_TYPE = "note-already-has-type"
    LOG_DATE_REQUIRED = "log-date-required"
    LOG_ENTRY_DATE_REQUIRED = "log-entry-date-required"
    ONLY_REFERENCE_CATEGORIES = "only-reference-categories"
    NOTE_DIRECTORY_NOT_DIRECTORY = "note-directory-not-directory"
    NOTE_ALREADY_EXISTS = "note-already-exists"
    NOTE_TEXT_MISMATCH = "note-text-mismatch"
    LOG_TEXT_TYPE = "log-text-type"
    LOG_TEXT_DATE = "log-text-date"
    LOG_TITLE_REQUIRED = "log-title-required"
    LOG_ENTRY_EXISTS = "log-entry-exists"
    ONLY_PROJECT_STEPS = "only-project-steps"
    STEP_LINE_MISSING = "step-line-missing"
    STEP_CONFIRMATION_REQUIRED = "step-confirmation-required"
    STATUS_CONFIRMATION_REQUIRED = "status-confirmation-required"
    CAPTURE_EMPTY = "capture-empty"
    VAULT_PATH_NOT_DIRECTORY = "vault-path-not-directory"
    VAULT_PATH_NOT_EMPTY = "vault-path-not-empty"
    VAULT_INSPECT_FAILED = "vault-inspect-failed"
    VAULT_CREATE_FAILED = "vault-create-failed"
    VAULT_SEED_FAILED = "vault-seed-failed"
    TEMPLATE_WRITE_FAILED = "template-write-failed"
    TEMPLATE_CARD_WRITE_FAILED = "template-card-write-failed"
    VAULT_PATH_ESCAPES = "vault-path-escapes"
    VAULT_ROOT_MISSING = "vault-root-missing"
    VAULT_ROOT_NOT_DIRECTORY = "vault-root-not-directory"
    VAULT_ROOT_UNREADABLE = "vault-root-unreadable"
    LOG_DIRECTORY_SELECTED = "log-directory-selected"
    NOTE_HAS_NO_TYPE = "note-has-no-type"
    STATUS_INVALID_FOR_NOTE = "status-invalid-for-note"
    NOTE_NO_TITLE = "note-no-title"
    NOTE_PARSE_FAILED = "note-parse-failed"
    NOTE_READ_FAILED = "note-read-failed"
    SCHEMA_VERSION_POSITIVE = "schema-version-positive"
    SCHEMA_INSPECT_FAILED = "schema-inspect-failed"
    SCHEMA_SYMLINK = "schema-symlink"
    SCHEMA_NOT_FILE = "schema-not-file"
    SCHEMA_TOO_LARGE = "schema-too-large"
    SCHEMA_READ_FAILED = "schema-read-failed"
    SCHEMA_MISSING = "schema-missing"
    SCHEMA_WRITE_FAILED = "schema-write-failed"
    SCHEMA_INVALID_UTF8 = "schema-invalid-utf8"
    SCHEMA_INVALID_YAML = "schema-invalid-yaml"
    SCHEMA_VERSION_NOT_INT = "schema-version-not-int"
    SCHEMA_SHAPE = "schema-shape"
    SCHEMA_NEWER = "schema-newer"
    SCHEMA_OLDER = "schema-older"
    SCHEMA_NOT_WRITABLE = "schema-not-writable"
    SCHEMA_MISSING_FOLDERS = "schema-missing-folders"
    NOTE_DATE_FORMAT = "note-date-format"
    NOTE_DATE_TIMESTAMP = "note-date-timestamp"
    INVALID_NOTE_DATE = "invalid-note-date"
    FRONTMATTER_UNCLOSED = "frontmatter-unclosed"
    FRONTMATTER_INVALID_YAML = "frontmatter-invalid-yaml"
    FRONTMATTER_NOT_MAPPING = "frontmatter-not-mapping"
    FRONTMATTER_KEYS_NOT_STRINGS = "frontmatter-keys-not-strings"
    RETIRED_PEOPLE_KEY = "retired-people-key"
    RETIRED_PROJECT_KEY = "retired-project-key"
    FRONTMATTER_TYPE_NOT_STRING = "frontmatter-type-not-string"
    RETIRED_ACTION_TYPE = "retired-action-type"
    RETIRED_PERSON_TYPE = "retired-person-type"
    UNKNOWN_NOTE_TYPE = "unknown-note-type"
    FRONTMATTER_CATEGORY_NOT_STRING = "frontmatter-category-not-string"
    FRONTMATTER_CATEGORY_ONLY_REFERENCE = "frontmatter-category-only-reference"
    INVALID_CATEGORY = "invalid-category"
    FRONTMATTER_STATUS_NOT_STRING = "frontmatter-status-not-string"
    UNKNOWN_NOTE_STATUS = "unknown-note-status"
    FRONTMATTER_STATUS_WITHOUT_TYPE = "frontmatter-status-without-type"
    STATUS_INVALID_FOR_TYPE = "status-invalid-for-type"
    FRONTMATTER_DUE_ONLY_PROJECT = "frontmatter-due-only-project"
    FRONTMATTER_ASSIGNMENT_NOT_STRING = "frontmatter-assignment-not-string"
    FRONTMATTER_ASSIGNMENT_EMPTY = "frontmatter-assignment-empty"
    FRONTMATTER_ASSIGNMENT_ONLY_PROJECT = "frontmatter-assignment-only-project"
    DUE_DATE_NOT_TIMESTAMP = "due-date-not-timestamp"
    DUE_DATE_INPUT_INVALID = "due-date-input-invalid"
    INVALID_DUE_DATE = "invalid-due-date"
    DUE_DATE_NOT_DATE = "due-date-not-date"
    NOT_SCHEME_REFERENCE = "not-scheme-reference"
    RETIRED_PERSON_SCHEME = "retired-person-scheme"
    UNKNOWN_REFERENCE_SCHEME = "unknown-reference-scheme"
    REFERENCE_NAME_EMPTY = "reference-name-empty"
    REWRITE_INVALID_MARKDOWN = "rewrite-invalid-markdown"
    REWRITE_OLD_REFERENCE = "rewrite-old-reference"
    LOG_DATE_CHANGE_VIA_FIELD = "log-date-change-via-field"
    STEP_TEXT_REQUIRED = "step-text-required"
    STEP_LINE_CHANGED = "step-line-changed"
    STEP_METADATA_INVALID_YAML = "step-metadata-invalid-yaml"
    STEP_VALUE_DOUBLE_DASH = "step-value-double-dash"
    PROCESSING_PLAN_INVALID = "processing-plan-invalid"
    PROCESSING_PROJECT_ASSIGNMENT = "processing-project-assignment"
    APPEND_PLAN_INVALID = "append-plan-invalid"
    PROCESSING_CARD_ONLY = "processing-card-only"
    PROCESSING_CARD_REQUIRED = "processing-card-required"
    PROCESSING_CAPTURE_REQUIRED = "processing-capture-required"
    PROCESSING_DUE_ONLY_PROJECT = "processing-due-only-project"
    PROCESSING_PROJECT_REQUIRED = "processing-project-required"
    PROCESSING_PROJECT_UNKNOWN = "processing-project-unknown"
    PROCESSING_PROJECT_AMBIGUOUS = "processing-project-ambiguous"
    PROCESSING_CONFIRMATION = "processing-confirmation"
    PROCESSING_CAPTURE_GONE = "processing-capture-gone"
    PROCESSING_TRASH_FAILED = "processing-trash-failed"
    PROCESSING_SOURCE_CHANGED = "processing-source-changed"
    PROCESSING_TARGET_GONE = "processing-target-gone"
    PROCESSING_TARGET_CHANGED = "processing-target-changed"
    PROCESSING_PARTIAL_TRASH = "processing-partial-trash"
    PROCESSING_NOTE_MISMATCH = "processing-note-mismatch"
    PROCESSING_MOVE_FAILED = "processing-move-failed"
    PROCESSING_INBOX_ONLY = "processing-inbox-only"
    UNKNOWN_TEMPLATE = "unknown-template"
    TEMPLATE_NO_LABEL = "template-no-label"
    TEMPLATE_LOCALES_MISSING = "template-locales-missing"
    TEMPLATE_NOTE_READ_FAILED = "template-note-read-failed"
    TEMPLATE_NOTE_BRACE = "template-note-brace"
    TEMPLATE_NOTE_PARSE_FAILED = "template-note-parse-failed"
    TEMPLATE_NO_LOCALE_FOLDER = "template-no-locale-folder"
    TEMPLATE_LOCALE_SHAPE = "template-locale-shape"
    TEMPLATE_INVALID = "template-invalid"
    CARD_INVALID = "card-invalid"
    CARD_READ_FAILED = "card-read-failed"
    CARD_FOLDER_READ_FAILED = "card-folder-read-failed"
    CARDS_MISSING = "cards-missing"
    CARD_LOCALE_SHAPE = "card-locale-shape"
    CARD_FRONTMATTER_PARSE = "card-frontmatter-parse"
    CARD_TYPE_REQUIRED = "card-type-required"
    CARD_CATEGORY_REQUIRED = "card-category-required"
    CARD_LOG_NO_CATEGORY = "card-log-no-category"
    CARD_BODY_HEADING = "card-body-heading"
    CARD_STATUS_NOT_ALLOWED = "card-status-not-allowed"
    CARD_DUE_NOT_ALLOWED = "card-due-not-allowed"
    CARD_TITLE_NOT_STRING = "card-title-not-string"
    CARD_DESCRIPTION_NOT_STRING = "card-description-not-string"
    TRASH_CONFIRMATION = "trash-confirmation"
    TRASH_METADATA_WRITE_FAILED = "trash-metadata-write-failed"
    TRASH_MOVE_FAILED = "trash-move-failed"
    TRASH_RESTORE_CONFIRMATION = "trash-restore-confirmation"
    TRASH_DELETE_FAILED = "trash-delete-failed"
    TRASH_RESTORE_UNSUPPORTED = "trash-restore-unsupported"
    TRASH_ENTRY_MISSING = "trash-entry-missing"
    TRASH_METADATA_UNREADABLE = "trash-metadata-unreadable"
    TRASH_BIRTHPLACE_NOT_FILE = "trash-birthplace-not-file"
    TRASH_RESTORE_FAILED = "trash-restore-failed"
    TRASH_RESTORE_PARTIAL = "trash-restore-partial"
    TRASH_NO_BIRTHPLACE = "trash-no-birthplace"
    TRASH_NOT_MANAGED = "trash-not-managed"
    TRASH_NOT_REGULAR = "trash-not-regular"
    LOG_DATE_IDENTITY_ONLY = "log-date-identity-only"
    LOG_NAME_EXISTS = "log-name-exists"
    DIRECTORY_MOVE_CONFIRMATION = "directory-move-confirmation"
    MOVE_DESTINATION_NOT_DIRECTORY = "move-destination-not-directory"
    MOVE_NAME_CONFLICT = "move-name-conflict"
    CATEGORY_ONLY_REFERENCE = "category-only-reference"
    CATEGORY_MOVE_CONFIRMATION = "category-move-confirmation"
    CATEGORY_MOVE_FAILED = "category-move-failed"
    RENAME_CONFIRMATION = "rename-confirmation"
    RENAME_DIRECTORY_FAILED = "rename-directory-failed"
    RENAME_NOTE_GONE = "rename-note-gone"
    RENAME_INSPECT_FAILED = "rename-inspect-failed"
    REFERENCE_REPAIR_SCHEME = "reference-repair-scheme"
    REFERENCE_REPAIR_CONFIRMATION = "reference-repair-confirmation"


@dataclasses.dataclass(frozen=True, slots=True)
class DomainMessage:
    """A stable domain-message identity with ordered interpolation values.

    Attributes
    ----------
    code : MessageCode
        Message identity translated at the interface or command-line boundary.
    values : tuple[tuple[str, str], ...]
        Ordered placeholder names and written values. Order is preserved so a
        technical rendering is deterministic.

    Notes
    -----
    Core code never renders this value into user-facing copy. The active
    catalog renders it at the boundary.
    """

    code: MessageCode
    values: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        """Validate the code and interpolation values.

        Raises
        ------
        TypeError
            If the code is not a :class:`MessageCode`.
        ValueError
            If a placeholder name is empty, a value is not text, or a
            placeholder name repeats.
        """
        if not isinstance(self.code, MessageCode):
            message = f"DomainMessage code must be a MessageCode: {self.code!r}"
            raise TypeError(message)
        seen: set[str] = set()
        for name, value in self.values:
            if not name:
                message = "DomainMessage placeholder names must not be empty"
                raise ValueError(message)
            if not isinstance(value, str):
                message = f"DomainMessage value for {name!r} must be text"
                raise TypeError(message)
            if name in seen:
                message = f"DomainMessage placeholder repeats: {name!r}"
                raise ValueError(message)
            seen.add(name)

    @classmethod
    def of(cls, code: MessageCode, /, **values: str) -> Self:
        """Build a message from a code and keyword values.

        Parameters
        ----------
        code : MessageCode
            Message identity.
        **values : str
            Placeholder values in call order.

        Returns
        -------
        DomainMessage
            Immutable message carrying the values in keyword order.
        """
        return cls(code=code, values=tuple(values.items()))

    def __str__(self) -> str:
        """Return a stable technical rendering for logs and tests.

        Returns
        -------
        str
            Message code followed by ordered placeholder pairs, never the
            translated user-facing sentence.
        """
        if not self.values:
            return self.code.value
        rendered = ", ".join(f"{name}={value}" for name, value in self.values)
        return f"{self.code.value}: {rendered}"


class AfanesError(Exception):
    """Base class for every Afanes domain error.

    Parameters
    ----------
    message : DomainMessage
        Structured domain message. The active catalog renders it at the user
        boundary.

    Attributes
    ----------
    domain_message : DomainMessage
        Structured message carried by this error.

    Notes
    -----
    Callers at the UI and CLI boundary render these errors into concise,
    actionable messages. Library code never prints them.
    """

    def __init__(self, message: DomainMessage) -> None:
        """Store the structured domain message.

        Parameters
        ----------
        message : DomainMessage
            Structured domain message.

        Raises
        ------
        TypeError
            If the message is not a :class:`DomainMessage`.
        """
        if not isinstance(message, DomainMessage):
            technical = f"AfanesError requires a DomainMessage: {message!r}"
            raise TypeError(technical)
        super().__init__(message)
        self.domain_message = message


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
