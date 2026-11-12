# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Centralized user-facing copy for the Afanes interface.

Views and state read text from this module so the interface stays consistent
and can be localized later. No UI copy belongs inline in a view.
"""

from types import MappingProxyType

APP_TITLE = "Afanes"

LAUNCH_DESCRIPTION = "Open Afanes, an offline Markdown vault."
LAUNCH_WEB_HELP = "Serve the interface in a browser instead of a desktop window."
LAUNCH_VAULT_HELP = "Open DIR for this run without replacing the remembered vault."
LAUNCH_PORT_HELP = "Port for the browser presentation. 0 chooses a free port."
LAUNCH_PORT_NOT_NUMBER = "port must be a whole number"
LAUNCH_PORT_OUT_OF_RANGE = "port must be between 0 and {limit}"
LAUNCH_MISSING_SDK = (
    'Afanes needs the Flet SDK, which is not installed. Install it with "pip install afanes[desktop]" '
    'or "pip install afanes[web]".'
)
LAUNCH_MISSING_DESKTOP = (
    'The desktop runtime is not installed. Install it with "pip install afanes[desktop]", '
    "or run with --web for the browser presentation."
)
LAUNCH_MISSING_WEB = 'The web runtime is not installed. Install it with "pip install afanes[web]".'
LAUNCH_DESKTOP_FAILED = "The desktop window could not start: {detail}\nRun with --web for the browser presentation."
LAUNCH_VAULT_INVALID = "Cannot open {path}: {detail}"

WELCOME_TITLE = "Welcome to Afanes"
WELCOME_BODY = (
    "Afanes works on a folder of Markdown files called a vault. Open an existing folder, or create a new vault."
)
WELCOME_CHOOSE = "Choose vault"
WELCOME_NOTE = "You can change the vault later."
WELCOME_PATH_LABEL = "Vault folder path"
WELCOME_PATH_HINT = "Absolute path to a folder of Markdown files."
WELCOME_OPEN = "Open"
NEW_VAULT_ACTION = "New vault"
NEW_VAULT_DIALOG_TITLE = "New vault"
NEW_VAULT_DIALOG_BODY = (
    "Choose the folder for the new vault and its starter content. Missing folders in the path are created."
)
NEW_VAULT_PATH_LABEL = "New vault folder path"
NEW_VAULT_BROWSE = "Choose folder"
NEW_VAULT_TEMPLATE_LABEL = "Starter content"
NEW_VAULT_TEMPLATE_NONE = "No starter content"
NEW_VAULT_TEMPLATE_OPTION = "{label} - {description}"
NEW_VAULT_TEMPLATE_UNAVAILABLE = "Starter content could not be read. You can still create a vault without it."
NEW_VAULT_TEMPLATE_FAILED = "Could not write the starter content: {detail}"
NEW_VAULT_PREVIEW_GUIDE = "Creates: {folders} and afanes.yaml. Writes the guide note."
NEW_VAULT_PREVIEW_TEMPLATE = "Creates: {folders} and afanes.yaml. Writes {notes} and the guide note."
NEW_VAULT_CREATE = "Create"
CANCEL_ACTION = "Cancel"
SESSION_ACTIVE_TITLE = "Afanes is open in another window"
SESSION_ACTIVE_BODY = "Only one window can use the vault at a time. Close the other window, then try again."
SESSION_RETRY = "Try again"
CHANGE_VAULT_DIALOG_TITLE = "Change vault"
CHANGE_VAULT_DIALOG_BODY = "Enter the folder path for the vault to open."
CHANGE_VAULT_OPEN = "Open another vault"
CHANGE_VAULT_CREATE = "Create a new vault"
CLOSE_VAULT_ACTION = "Close vault"
VAULT_CLOSE_NOT_FORGOTTEN = "The vault was closed, but it could not be forgotten and may reopen next launch: {detail}"
VAULT_SCHEMA_ADOPT_TITLE = "This folder can be adopted"
VAULT_SCHEMA_ADOPT_BODY = (
    "Afanes found no afanes.yaml settings file in {path}. Creating it will not change any note, folder, "
    "guide, or template card."
)
VAULT_SCHEMA_ADOPT_ACTION = "Create afanes.yaml and open"
VAULT_SCHEMA_ADOPT_MESSAGE = "This folder needs an afanes.yaml settings file before Afanes can open it."
VAULT_SCHEMA_UNAVAILABLE = (
    "This folder is not an Afanes vault. To adopt it, the folder needs an afanes.yaml settings file, "
    "the five default folders, and write access."
)
VAULT_SCHEMA_NOT_ADOPTABLE = "The folder cannot be adopted: {detail}"
VAULT_SCHEMA_ADOPTED_NOT_REMEMBERED = "The vault was adopted but could not be remembered: {detail}"

INBOX_TITLE = "Inbox"
REVIEW_TITLE = "Review"
REVIEW_PENDING_ONE = "1 pending"
REVIEW_PENDING_MANY = "{count} pending"
REVIEW_ZERO_TITLE = "Nothing needs review"
REVIEW_ZERO_BODY = "No inbox captures or projects are waiting for a next step."
REVIEW_START_ACTION = "Start review"
REVIEW_COMPLETE_TITLE = "Review complete"
REVIEW_COMPLETE_BODY = "Reviewed {reviewed} and skipped {skipped}."
REVIEW_BACK_TO_BROWSER = "Back to browser"
REVIEW_CAPTURE_TITLE = "Capture"
REVIEW_PROCESS_ACTION = "Process capture"
REVIEW_NEXT = "Next"
REVIEW_SKIP = "Skip"
REVIEW_OPEN_PROJECT = "Open project"
REVIEW_OPEN_ACTION = "Open"
REVIEW_NEXT_STEP = "Next step"
REVIEW_NO_NEXT_STEP = "This project has no next step yet."
REVIEW_OTHER_STEPS = "Other open steps"
REVIEW_CREATE_STEP = "Add next step"
REVIEW_STEP_TITLE_LABEL = "Next step"
REVIEW_STEP_TITLE_HINT = "What is the next step?"
REVIEW_STEP_CONFIRM = "Add step"
REVIEW_STEP_CANCEL = "Cancel"
REVIEW_TITLE_REQUIRED = "Enter text for the next step."
REVIEW_MARK_DONE = "Mark project done"
REVIEW_DEFER = "Defer to later"
REVIEW_CONFIRM_DONE = "Confirm done"
REVIEW_CONFIRM_DEFER = "Confirm later"
REVIEW_CANCEL = "Cancel"
REVIEW_STEP_CREATED = "Next step added to {path}"
REVIEW_STEP_FAILED = "Could not update this step: {detail}"
REVIEW_PROJECT_FAILED = "Could not update this project: {detail}"
REVIEW_CAPTURE_READ_FAILED = "Could not read this capture: {detail}"
REVIEW_DUE = "Due {date}"
WORKSPACE_SECTION_LABELS = MappingProxyType(
    {
        "inbox": "Inbox",
        "projects": "Projects",
        "references": "References",
        "log": "Log",
        "needs_attention": "Needs attention",
    }
)
BROWSER_SEARCH_LABEL = "Search"
BROWSER_SEARCH_HINT = "Title, identity, or text"
BROWSER_EMPTY = "No notes in this section."
BROWSER_NO_MATCH = "No notes match this search."
BROWSER_FAILURES = "Unreadable notes"
BROWSER_NEW_REFERENCE = "New reference"
BROWSER_NEW_REFERENCE_TITLE = "New reference"
BROWSER_NEW_REFERENCE_BODY = "Give the reference a name and choose a template card, or Empty."
BROWSER_NAME_LABEL = "Name"
BROWSER_NAME_REQUIRED = "Enter a name for the reference."
BROWSER_CREATE_ACTION = "Create"
BROWSER_CREATE_FAILED = "Could not create this reference: {detail}"
BROWSER_TEMPLATE_LABEL = "Template"
BROWSER_TEMPLATE_EMPTY = "Empty - general category, no starter body"
BROWSER_TEMPLATE_OPTION = "{title} - {description}"
BROWSER_TEMPLATE_OPTION_PLAIN = "{title}"
BROWSER_TEMPLATE_OPTION_DUPLICATE = "{title} - {description} ({path})"
BROWSER_TEMPLATE_OPTION_DUPLICATE_PLAIN = "{title} ({path})"
BROWSER_TEMPLATE_DESCRIPTION_EMPTY = "Empty creates a reference in the general category with no starter body."
BROWSER_TEMPLATE_NO_DESCRIPTION = "No description."
BROWSER_TEMPLATE_INVALID = "Some template cards could not be read and will be skipped: {paths}"
PROJECT_GROUP_LABELS = MappingProxyType(
    {
        "active": "Active",
        "waiting": "Waiting",
        "later": "Later",
        "closed": "Closed",
    }
)
PROJECT_OPEN_STEPS_ONE = "1 open step"
PROJECT_OPEN_STEPS_MANY = "{count} open steps"
PROJECT_NEXT_STEP = "Next: {title}"
PROJECT_NO_NEXT_STEP = "No next step"
PROJECT_DUE = "Due {date}"
PROJECT_ASKED_BY = "Asked by {name}"
PROJECT_STATUS = "Status: {status}"
PROCESS_ACTION = "Process"
PROCESSING_TITLE = "Process capture"
PROCESSING_CAPTURE = "Capture"
PROCESSING_OUTCOME_LABEL = "Outcome"
PROCESSING_STATUS_LABEL = "Status"
PROCESSING_DUE_DATE_LABEL = "Due date (YYYY-MM-DD)"
PROCESSING_PROJECT_LABEL = "Project"
PROCESSING_TEMPLATE_LABEL = "Template"
PROCESSING_TEMPLATE_EMPTY = "Empty - general category, no starter body"
PROCESSING_TEMPLATE_OPTION = "{title} - {description}"
PROCESSING_TEMPLATE_OPTION_PLAIN = "{title}"
PROCESSING_TEMPLATE_OPTION_DUPLICATE = "{title} - {description} ({path})"
PROCESSING_TEMPLATE_OPTION_DUPLICATE_PLAIN = "{title} ({path})"
PROCESSING_TEMPLATE_DESCRIPTION_EMPTY = "Empty creates a reference in the general category with no starter body."
PROCESSING_TEMPLATE_NO_DESCRIPTION = "No description."
PROCESSING_TEMPLATE_INVALID = "Some template cards could not be read and will be skipped: {paths}"
PROCESSING_PLAN_CATEGORY = "Category: {category}"
PROCESSING_PLAN_SCAFFOLD = "A starter body will be added."
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
        "project": "Project",
        "append_step": "Append step",
        "done_now": "Done now",
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
VAULT_MISSING = "That folder does not exist. Choose a vault to continue."
VAULT_NOT_DIRECTORY = "That path is not a folder. Choose a vault to continue."
VAULT_UNREADABLE = "That folder cannot be read. Choose a vault to continue."
VAULT_NOT_EMPTY = "That folder is not empty. Choose an empty folder or an existing vault."
VAULT_CREATED_NOT_REMEMBERED = "The vault was created, but it could not be remembered: {detail}"
LOG_MODE_NOT_REMEMBERED = "The Log view was changed, but the preference could not be saved: {detail}"
LOG_PLACEHOLDER = "The Log calendar and date tree appear here."
LOG_MONTH_ENTRY_MARK = "This month has an entry."
LOG_YEAR_ENTRY_MARK = "This year has an entry."
LOG_PREVIOUS_MONTH = "Previous month"
LOG_NEXT_MONTH = "Next month"
LOG_EMPTY = "No entries yet."
LOG_UNDATED = "Undated"
LOG_NEW_MONTH_ENTRY = "Write an entry for {period}"
LOG_NEW_YEAR_ENTRY = "Write an entry for {year}"
LOG_OPEN_MONTH_ENTRY = "Open the {period} entry"
LOG_OPEN_YEAR_ENTRY = "Open the {year} entry"
LOG_CREATE_FAILED = "The log entry could not be created: {detail}"
LOG_ENTRY_TITLE = "Log entry"
LOG_ENTRY_BODY = "Write a dated entry for {date}."
LOG_TITLE_LABEL = "Title"
LOG_TITLE_REQUIRED = "Enter a title for the log entry."
LOG_CARD_LABEL = "Starter"
LOG_CARD_DESCRIPTION_EMPTY = "No starter body."
LOG_CREATE_ACTION = "Write entry"
LOG_TODAY_ENTRY = "Today's entry"
LOG_MODE_ENTRIES = "Entries"
LOG_MODE_EVERYTHING = "Everything"


def log_entry_count(count: int) -> str:
    """Return a compact entry count for a tree row.

    Parameters
    ----------
    count : int
        Number of notes at or below the row.

    Returns
    -------
    str
        Parenthesized count.
    """
    return f"({count})"


def log_day_tooltip(day: int, count: int) -> str:
    """Return the calendar day tooltip for an entry count.

    Parameters
    ----------
    day : int
        Calendar day.
    count : int
        Number of entries on that day.

    Returns
    -------
    str
        Tooltip naming the date and entry count.
    """
    if count == 0:
        return f"{day}: no entries"
    if count == 1:
        return f"{day}: 1 entry"
    return f"{day}: {count} entries"


VAULT_PATH_REQUIRED = "Enter the folder path for the vault."
SCAN_WARNING_ONE = "1 note could not be read: {paths}"
SCAN_WARNING_MANY = "{count} notes could not be read: {paths}"

PAGE_BACK = "Back"
PAGE_EDIT = "Edit"
PAGE_DONE = "Done"
PAGE_RENAME = "Rename"
PAGE_TRASH = "Move to trash"
PAGE_EMPTY = "Select a note to open it."
PAGE_IDENTITY_LABEL = "Identity"
PAGE_PATH_LABEL = "Path"
PAGE_BODY_LABEL = "Body (Markdown)"
PAGE_TYPE_LABEL = "Type"
PAGE_CATEGORY_LABEL = "Category"
PAGE_STATUS_LABEL = "Status"
PAGE_DUE_DATE_LABEL = "Due date (YYYY-MM-DD)"
PAGE_DATE_LABEL = "Date (YYYY, YYYY-MM, or YYYY-MM-DD)"
PAGE_DATE = "Date: {date}"
PAGE_NO_DATE = "No date"
PAGE_LOG_DATE_REQUIRED = "A log entry needs a date."
PAGE_DATE_CHANGE_FAILED = "The date could not be changed: {detail}"
PAGE_TYPE_CHANGE_FAILED = "The note type could not be changed: {detail}"
PAGE_ASKED_BY_LABEL = "Asked by"
PAGE_ASKED_BY_HINT = "Person or group that requested it"
PAGE_RAW_WARNING = "This page's metadata cannot be read. Edit the text directly; labels return once it parses."
PAGE_RAW_SAVE = "Save text"
PAGE_SAVING = "Saving"
PAGE_SAVED = "Saved"
PAGE_UNSAVED = "Unsaved changes"
PAGE_OPEN_FAILED = "Could not open this page: {detail}"
PAGE_SAVE_FAILED = "Could not save this page: {detail}"
PAGE_CONFLICT_CHANGED = "This page changed on disk. Reload it or overwrite it with your version."
PAGE_CONFLICT_MISSING = "This page no longer exists at its path. Recreate it or discard the draft."
PAGE_CONFLICT_LEAVE = "Resolve the disk conflict before leaving this page."
PAGE_PENDING_DIALOG = "Confirm or cancel the open page action before leaving this page."
PAGE_CONFLICT_TITLE = "This page changed on disk"
PAGE_CONFLICT_RELOAD = "Reload from disk"
PAGE_CONFLICT_OVERWRITE = "Overwrite with my version"
PAGE_CONFLICT_RECREATE = "Recreate page"
PAGE_CONFLICT_DISCARD = "Discard draft"
PAGE_AMBIGUOUS_TITLE = "Choose a page"
PAGE_AMBIGUOUS_BODY = "More than one page matches this reference."
PAGE_REPAIR_PENDING = "Choose how to handle the old link names before leaving this page."
PAGE_REPAIR_TITLE = "Repair link names"
PAGE_REPAIR_BODY = 'The name "{old}" cannot be a filename. The page was created as "{new}".'
PAGE_REPAIR_COUNT = "{detail} still use the old name."
PAGE_REPAIR_REWRITE = "Rewrite links"
PAGE_REPAIR_KEEP = "Keep old links"
PAGE_REPAIR_CANCEL = "Cancel creation"
PAGE_REPAIR_FAILED = "Some links could not be repaired: {detail}"
PAGE_TYPE_CHANGE_TITLE = "Change page type?"
PAGE_TYPE_CHANGE_BODY = "{detail} will become unresolved."
PAGE_TYPE_CHANGE_CONFIRM = "Change type"
PAGE_RENAME_TITLE = "Rename page"
PAGE_RENAME_LABEL = "New name"
PAGE_RENAME_PREVIEW = "{detail} will be updated."
PAGE_RENAME_CONFIRM = "Rename"
PAGE_RENAME_FAILED = "Could not rename this page: {detail}"
PAGE_TRASH_TITLE = "Move to trash?"
PAGE_TRASH_BODY = "The page will move to {path}. {detail} will become unresolved."
PAGE_TRASH_CONFIRM = "Move to trash"
PAGE_TRASH_FAILED = "Could not move this page to trash: {detail}"
PAGE_CANCEL = "Cancel"
PAGE_RAW_UPGRADED = "The page now parses; labels are available."
PAGE_TYPE_CHANGE_LEAVE = "Confirm or cancel the type change before leaving this page."
PAGE_NONE = "None"
PAGE_NEW = "New page"
PAGE_CATEGORY_HINT = "Any label, such as person or place"
PAGE_CATEGORY_INVALID = "A category must be one non-empty folder name without path separators."
PAGE_CATEGORY_MOVE_TITLE = "Move this page?"
PAGE_CATEGORY_MOVE_BODY = "The page will move to {path}. Its name and references stay the same."
PAGE_CATEGORY_MOVE_CONFIRM = "Move page"
PAGE_CATEGORY_MOVE_FAILED = "Could not move this page to its category folder: {detail}"
PAGE_STEP_TICK = "Mark complete"
PAGE_STEP_UNTICK = "Reopen"
PAGE_STEP_OWNERS = "Owners: {owners}"
PAGE_STEP_PLAN = "Plan: {date}"
PAGE_STEP_ACTUAL = "Done: {date}"
PAGE_STEP_TAGS = "Tags: {tags}"
PAGE_STEP_WAITING = "Waiting"
PAGE_STEP_FAILED = "Could not update this step: {detail}"
PAGE_STEP_PLAN_ACTION = "Set plan date"
PAGE_STEP_CLEAR_PLAN = "Clear plan date"
PAGE_STEP_OWNER_ACTION = "Edit owners"
PAGE_STEP_OWNER_TITLE = "Owners"
PAGE_STEP_OWNER_ADD = "Add owner"
PAGE_STEP_OWNER_HINT = "Note name"
PAGE_STEP_OWNER_DUPLICATE = "{owner} is already an owner."
PAGE_STEP_OWNER_REMOVE = "Remove {owner}"
PAGE_PROJECT_NO_STATUS = "No status"
PAGE_PROJECT_DUE_ADD = "Add due date"
PAGE_PROJECT_DUE_CLEAR = "Clear due date"
PAGE_PROJECT_NO_DUE = "No due date"
PAGE_PROJECT_EMPTY_BODY = "This project has no body yet."
PAGE_CONNECTIONS_TITLE = "Connections"
PAGE_CONNECTIONS_LINKED_FROM = "Linked from"
PAGE_CONNECTIONS_OWNED_STEPS = "Owned steps"
PAGE_CONNECTIONS_REQUESTED_PROJECTS = "Requested projects"
PAGE_CONNECTIONS_EMPTY_LINKED_FROM = "No notes link here."
PAGE_CONNECTIONS_EMPTY_STEPS = "No open steps."
PAGE_CONNECTIONS_EMPTY_PROJECTS = "No open projects."
PAGE_CONNECTIONS_SHOW_COMPLETED_STEPS = "Show completed steps"
PAGE_CONNECTIONS_SHOW_FINISHED_PROJECTS = "Show finished projects"
REVIEW_DUE_STEP_TITLE = "Due step"
REVIEW_WAITING_STEP_TITLE = "Waiting step"
REVIEW_DO_NOW = "Do it now"
REVIEW_POSTPONE = "Postpone"
REVIEW_DELEGATE = "Delegate"
REVIEW_REASSIGN = "Reassign"
REVIEW_OWNER_LABEL = "Owner"
REVIEW_OWNER_REQUIRED = "Enter an owner before confirming."
REVIEW_POSTPONE_LABEL = "New plan date (YYYY-MM-DD)"
REVIEW_INVALID_DATE = "Enter the plan date as YYYY-MM-DD."
REVIEW_CONFIRM = "Confirm"
REVIEW_STEP_OWNERS = "Owners: {owners}"
REVIEW_LAUNCH_DIGEST_ONE = "1 due step needs attention"
REVIEW_LAUNCH_DIGEST_MANY = "{count} due steps need attention"
REVIEW_LAUNCH_DIGEST_ACTION = "Start review"

PAGE_TYPE_LABELS = MappingProxyType(
    {
        "note": "Note",
        "project": "Project",
        "reference": "Reference",
        "log": "Log",
    }
)


def reference_count(count: int, notes: int) -> str:
    """Return a short reference-count phrase for a page dialog.

    Parameters
    ----------
    count : int
        Number of references affected.
    notes : int
        Number of notes containing those references.

    Returns
    -------
    str
        Phrase such as ``2 references in 1 note``.
    """
    reference_label = "reference" if count == 1 else "references"
    note_label = "note" if notes == 1 else "notes"
    return f"{count} {reference_label} in {notes} {note_label}"


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


def open_step_count(count: int) -> str:
    """Return the open-step count label for a project row.

    Parameters
    ----------
    count : int
        Number of open steps.

    Returns
    -------
    str
        Singular or plural label.
    """
    return PROJECT_OPEN_STEPS_ONE if count == 1 else PROJECT_OPEN_STEPS_MANY.format(count=count)


def review_pending(count: int) -> str:
    """Return the review badge label.

    Parameters
    ----------
    count : int
        Number of captures and stalled projects awaiting review.

    Returns
    -------
    str
        Singular or plural pending label, including zero.
    """
    return REVIEW_PENDING_ONE if count == 1 else REVIEW_PENDING_MANY.format(count=count)


def scan_warning_title(count: int) -> str:
    """Return the unreadable-note banner heading.

    Parameters
    ----------
    count : int
        Number of notes that could not be parsed.

    Returns
    -------
    str
        Singular or plural heading for the failure list.
    """
    return "1 note could not be read." if count == 1 else f"{count} notes could not be read."


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
