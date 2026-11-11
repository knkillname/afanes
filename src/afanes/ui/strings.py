# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Centralized user-facing copy for the Afanes interface.

Views and state read text from this module so the interface stays consistent
and can be localized later. No UI copy belongs inline in a view.
"""

from types import MappingProxyType

APP_TITLE = "Afanes"

WELCOME_TITLE = "Welcome to Afanes"
WELCOME_BODY = "Afanes works on a folder of Markdown files called a vault. Choose an existing folder to get started."
WELCOME_CHOOSE = "Choose vault"
WELCOME_NOTE = "You can change the vault later."

INBOX_TITLE = "Inbox"
PROCESS_ACTION = "Process"
PROCESSING_TITLE = "Process capture"
PROCESSING_CAPTURE = "Capture"
PROCESSING_OUTCOME_LABEL = "Outcome"
PROCESSING_STATUS_LABEL = "Status"
PROCESSING_DUE_DATE_LABEL = "Due date (YYYY-MM-DD)"
PROCESSING_PEOPLE_LABEL = "People (comma-separated)"
PROCESSING_PROJECT_LABEL = "Project"
PROCESSING_PREVIEW_ACTION = "Preview"
PROCESSING_CONFIRM_ACTION = "Confirm"
PROCESSING_CANCEL_ACTION = "Cancel"
PROCESSING_DONE_ACTION = "Done"
PROCESSING_DESTINATION = "Destination: {path}"
PROCESSING_PLAN_TITLE = "Ready to apply"
PROCESSING_SUCCESS_TITLE = "Capture processed"
PROCESSING_SUCCESS_BODY = "The note was moved to {path}."
PROCESSING_UNRESOLVED = "Unresolved references: {names}"
PROCESSING_SCHEME_WARNING = "{count} inbound references will become unresolved because the note changes scheme."
PROCESSING_REFERENCE_WARNING = "{count} inbound references point to this capture and will become unresolved."
PROCESSING_EMPTY_OUTCOME = "Choose an outcome before previewing."
PROCESSING_INVALID_DATE = "Enter a due date as YYYY-MM-DD or leave it empty."
PROCESSING_READ_FAILED = "Could not read this capture: {detail}"
PROCESSING_PLAN_FAILED = "Could not prepare the processing preview: {detail}"
PROCESSING_FAILED = "Could not process the capture: {detail}"
PROCESSING_REFRESH_FAILED = "The capture was processed, but the Inbox could not be refreshed: {detail}"
PROCESSING_MISSING = "This capture is no longer in the Inbox."
NOTE_COUNT_ONE = "1 note"
NOTE_COUNT_MANY = "{count} notes"
COMPOSER_LABEL = "Capture a thought"
COMPOSER_HINT = "The first line becomes the title."
CAPTURE_ACTION = "Capture"
REFRESH_ACTION = "Refresh"
CHANGE_VAULT_ACTION = "Change vault"
EMPTY_TITLE = "Nothing captured yet"
EMPTY_BODY = "Write a thought above. The first line becomes the title."
PREVIEW_TITLE = "Preview"
PREVIEW_EMPTY = "Select a note to read it."
WORKING = "Working"

PROCESSING_OUTCOME_LABELS = MappingProxyType(
    {
        "trash": "Trash",
        "later": "Later",
        "reference": "Reference",
        "action": "Action",
        "project": "Project",
    }
)
PROCESSING_STATUS_LABELS = MappingProxyType(
    {
        "active": "Active",
        "waiting": "Waiting",
        "done": "Done",
        "cancelled": "Cancelled",
        "archived": "Archived",
        "later": "Later",
    }
)

CAPTURE_EMPTY = "Write a thought before capturing."
CAPTURE_FAILED = "Could not capture the thought: {detail}"
VAULT_SELECTION_FAILED = "Could not save the vault selection: {detail}"
REFRESH_FAILED = "Could not refresh the inbox: {detail}"
PREVIEW_FAILED = "Could not read this note: {detail}"
SETTINGS_UNREADABLE = "Saved preferences could not be read. Choose a vault to continue."
VAULT_MISSING = "The saved vault folder no longer exists. Choose a vault to continue."
VAULT_NOT_DIRECTORY = "The saved vault path is not a folder. Choose a vault to continue."
VAULT_UNREADABLE = "The saved vault folder cannot be read. Choose a vault to continue."
SCAN_WARNING_ONE = "1 note could not be read: {paths}"
SCAN_WARNING_MANY = "{count} notes could not be read: {paths}"


def note_count(count: int) -> str:
    """Return the note-count label for the Inbox heading.

    Parameters
    ----------
    count : int
        Number of notes currently shown.

    Returns
    -------
    str
        Singular or plural count label.
    """
    return NOTE_COUNT_ONE if count == 1 else NOTE_COUNT_MANY.format(count=count)


def scan_warning(count: int, paths: str) -> str:
    """Return the unreadable-note banner text.

    Parameters
    ----------
    count : int
        Number of notes that could not be parsed.
    paths : str
        Comma-separated vault-relative paths.

    Returns
    -------
    str
        Singular or plural warning with the affected paths.
    """
    template = SCAN_WARNING_ONE if count == 1 else SCAN_WARNING_MANY
    return template.format(count=count, paths=paths)
