# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Centralized user-facing copy for the Afanes interface.

Views and state read text from this module so the interface stays consistent
and can be localized later. No UI copy belongs inline in a view.
"""

APP_TITLE = "Afanes"

WELCOME_TITLE = "Welcome to Afanes"
WELCOME_BODY = "Afanes works on a folder of Markdown files called a vault. Choose an existing folder to get started."
WELCOME_CHOOSE = "Choose vault"
WELCOME_NOTE = "You can change the vault later."

INBOX_TITLE = "Inbox"
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
