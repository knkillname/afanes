# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Centralized user-facing copy for the Afanes interface.

Views and state read text from this module so the interface stays consistent
and can be localized later. No UI copy belongs inline in a view.
"""

from types import MappingProxyType

APP_TITLE = "Afanes"

LAUNCH_DESCRIPTION = "Open Afanes, an offline Markdown vault"
LAUNCH_WEB_HELP = "Serve the interface in a browser instead of a desktop window"
LAUNCH_VAULT_HELP = "Open DIR for this run without replacing the remembered vault"
LAUNCH_PORT_HELP = "Port for the browser presentation. 0 chooses a free port"
LAUNCH_PORT_NOT_NUMBER = "Port must be a whole number"
LAUNCH_PORT_OUT_OF_RANGE = "Port must be between 0 and {limit}"
LAUNCH_MISSING_SDK = (
    'Afanes needs the Flet SDK, which is not installed. Install it with "pip install afanes[desktop]" '
    'or "pip install afanes[web]"'
)
LAUNCH_MISSING_DESKTOP = (
    'The desktop runtime is not installed. Install it with "pip install afanes[desktop]", '
    "or run with --web for the browser presentation"
)
LAUNCH_MISSING_WEB = 'The web runtime is not installed. Install it with "pip install afanes[web]"'
LAUNCH_DESKTOP_FAILED = "The desktop window could not start: {detail}\nRun with --web for the browser presentation"
LAUNCH_VAULT_INVALID = "Cannot open {path}: {detail}"

WELCOME_TITLE = "Welcome to Afanes"
WELCOME_BODY = (
    "Afanes works on a folder of Markdown files called a vault. Open an existing folder, or create a new vault"
)
WELCOME_CHOOSE = "Choose Vault…"
WELCOME_PICKER_TITLE = "Choose Vault"
WELCOME_NOTE = "The vault can be changed later"
WELCOME_PATH_LABEL = "Vault folder path"
WELCOME_PATH_HINT = "Absolute path to a folder of Markdown files"
WELCOME_OPEN = "Open"
NEW_VAULT_ACTION = "New Vault…"
NEW_VAULT_PICKER_TITLE = "New Vault"
NEW_VAULT_DIALOG_TITLE = "New Vault"
NEW_VAULT_DIALOG_BODY = (
    "Choose the folder for the new vault and its starter content. Missing folders in the path are created"
)
NEW_VAULT_PATH_LABEL = "New vault folder path"
NEW_VAULT_BROWSE = "Choose Folder…"
NEW_VAULT_TEMPLATE_LABEL = "Starter content"
NEW_VAULT_TEMPLATE_NONE = "No Starter Content"
NEW_VAULT_TEMPLATE_OPTION = "{label} - {description}"
NEW_VAULT_TEMPLATE_UNAVAILABLE = "Starter content could not be read. A vault can still be created without it"
NEW_VAULT_TEMPLATE_FAILED = "Could not write the starter content: {detail}"
NEW_VAULT_PREVIEW_GUIDE = "Creates: {folders} and afanes.yaml. Writes the guide note"
NEW_VAULT_PREVIEW_TEMPLATE = "Creates: {folders} and afanes.yaml. Writes {notes} and the guide note"
NEW_VAULT_CREATE = "Create"
CANCEL_ACTION = "Cancel"
CLOSE_ACTION = "Close"
UNDO_ACTION = "Undo"
SESSION_ACTIVE_TITLE = "Afanes Is Open in Another Window"
SESSION_ACTIVE_BODY = "Only one window can use the vault at a time. Close the other window and try again"
SESSION_RETRY = "Try Again"
CHANGE_VAULT_DIALOG_TITLE = "Change Vault"
CHANGE_VAULT_DIALOG_BODY = "Enter the folder path for the vault to open"
CHANGE_VAULT_OPEN = "Open Another Vault…"
CHANGE_VAULT_CREATE = "Create a New Vault…"
CLOSE_VAULT_ACTION = "Close Vault"
MAIN_MENU = "Main Menu"
WORKSPACE_NAVIGATION = "Navigation"
CLOSE_NAVIGATION = "Close Navigation"
ABOUT_ACTION = "About Afanes"
ABOUT_TITLE = "About Afanes"
ABOUT_VERSION = "Version {version}"
ABOUT_LICENSE = "Licensed under the GNU Affero General Public License, version 3 or later"
VAULT_CLOSE_NOT_FORGOTTEN = "The vault was closed, but it could not be forgotten and may reopen next launch: {detail}"
VAULT_SCHEMA_ADOPT_TITLE = "This Folder Can Be Adopted"
VAULT_SCHEMA_ADOPT_BODY = (
    "Afanes found no afanes.yaml settings file in {path}. Creating it will not change any note, folder, "
    "guide, or template card"
)
VAULT_SCHEMA_ADOPT_ACTION = "Create afanes.yaml and Open"
VAULT_SCHEMA_ADOPT_MESSAGE = "This folder needs an afanes.yaml settings file before Afanes can open it"
VAULT_SCHEMA_UNAVAILABLE = (
    "This folder is not an Afanes vault. To adopt it, the folder needs an afanes.yaml settings file, "
    "the five default folders, and write access"
)
VAULT_SCHEMA_NOT_ADOPTABLE = "The folder cannot be adopted: {detail}"
VAULT_SCHEMA_ADOPTED_NOT_REMEMBERED = "The vault was adopted but could not be remembered: {detail}"

INBOX_TITLE = "Inbox"
REVIEW_TITLE = "Review"
REVIEW_PENDING_ONE = "1 Pending"
REVIEW_PENDING_MANY = "{count} Pending"
REVIEW_ZERO_TITLE = "Nothing Needs Review"
REVIEW_ZERO_BODY = "No inbox captures or projects are waiting for a next step"
REVIEW_START_ACTION = "Start Review"
REVIEW_COMPLETE_TITLE = "Review Complete"
REVIEW_COMPLETE_BODY = "Reviewed {reviewed} and skipped {skipped}"
REVIEW_BACK_TO_BROWSER = "Back to Browser"
REVIEW_CAPTURE_TITLE = "Capture"
REVIEW_PROCESS_ACTION = "Process Capture…"
REVIEW_NEXT = "Next"
REVIEW_SKIP = "Skip"
REVIEW_OPEN_PROJECT = "Open Project"
REVIEW_OPEN_ACTION = "Open"
REVIEW_NEXT_STEP = "Next Step"
REVIEW_NO_NEXT_STEP = "This project has no next step yet"
REVIEW_OTHER_STEPS = "Other Open Steps"
REVIEW_CREATE_STEP = "Add Next Step…"
REVIEW_STEP_TITLE_LABEL = "Next step"
REVIEW_STEP_TITLE_HINT = "What is the next step?"
REVIEW_STEP_CONFIRM = "Add Step"
REVIEW_STEP_CANCEL = "Cancel"
REVIEW_TITLE_REQUIRED = "Enter text for the next step"
REVIEW_MARK_DONE = "Mark Project Done…"
REVIEW_DEFER = "Defer to Later…"
REVIEW_CONFIRM_DONE = "Confirm Done"
REVIEW_CONFIRM_DEFER = "Confirm Later"
REVIEW_CANCEL = "Cancel"
REVIEW_STEP_CREATED = "Next step added to {path}"
REVIEW_STEP_FAILED = "Could not update this step: {detail}"
REVIEW_PROJECT_FAILED = "Could not update this project: {detail}"
REVIEW_CAPTURE_READ_FAILED = "Could not read this capture: {detail}"
REVIEW_DUE = "Due {date}"
REVIEW_CURRENT = "Current"
REVIEW_KIND_LABELS = MappingProxyType(
    {
        "inbox": "Capture",
        "due_step": "Due Step",
        "waiting_step": "Waiting Step",
        "project": "Project",
    }
)
WORKSPACE_SECTION_LABELS = MappingProxyType(
    {
        "inbox": "Inbox",
        "projects": "Projects",
        "references": "References",
        "log": "Log",
        "needs_attention": "Needs Attention",
    }
)
BROWSER_SEARCH_HINT = "Search all notes"
BROWSER_SEARCH_TITLE = "Search Results"
BROWSER_SEARCH_CLEAR = "Clear Search"
BROWSER_EMPTY = "No notes in this section"
BROWSER_NO_MATCH = "No notes match this search"
BROWSER_NO_MATCH_QUERY = "No notes match “{query}”"
BROWSER_FAILURES = "Unreadable Notes"
NEW_CAPTURE_ACTION = "New Capture"
BROWSER_NEW_REFERENCE = "New Reference…"
BROWSER_NEW_REFERENCE_TITLE = "New Reference"
BROWSER_NEW_REFERENCE_BODY = "Give the reference a name and choose a template card, or Empty"
BROWSER_NAME_LABEL = "Name"
BROWSER_NAME_REQUIRED = "Enter a name for the reference"
BROWSER_CREATE_ACTION = "Create"
BROWSER_CREATE_FAILED = "Could not create this reference: {detail}"
BROWSER_TEMPLATE_LABEL = "Template"
BROWSER_TEMPLATE_EMPTY = "Empty - General Category, No Starter Body"
BROWSER_TEMPLATE_OPTION = "{title} - {description}"
BROWSER_TEMPLATE_OPTION_PLAIN = "{title}"
BROWSER_TEMPLATE_OPTION_DUPLICATE = "{title} - {description} ({path})"
BROWSER_TEMPLATE_OPTION_DUPLICATE_PLAIN = "{title} ({path})"
BROWSER_TEMPLATE_DESCRIPTION_EMPTY = "Empty creates a reference in the general category with no starter body"
BROWSER_TEMPLATE_NO_DESCRIPTION = "No description"
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
PROJECT_STATUS = "Status: {status}"
PROJECT_META_SEPARATOR = " · "
PROCESS_ACTION = "Process…"
PROCESSING_TITLE = "Process Capture"
PROCESSING_CAPTURE = "Capture"
PROCESSING_OUTCOME_LABEL = "Outcome"
PROCESSING_STATUS_LABEL = "Status"
PROCESSING_DUE_DATE_LABEL = "Due date (YYYY-MM-DD)"
PROCESSING_PROJECT_LABEL = "Project"
PROCESSING_TEMPLATE_LABEL = "Template"
PROCESSING_TEMPLATE_EMPTY = "Empty - General Category, No Starter Body"
PROCESSING_TEMPLATE_OPTION = "{title} - {description}"
PROCESSING_TEMPLATE_OPTION_PLAIN = "{title}"
PROCESSING_TEMPLATE_OPTION_DUPLICATE = "{title} - {description} ({path})"
PROCESSING_TEMPLATE_OPTION_DUPLICATE_PLAIN = "{title} ({path})"
PROCESSING_TEMPLATE_DESCRIPTION_EMPTY = "Empty creates a reference in the general category with no starter body"
PROCESSING_TEMPLATE_NO_DESCRIPTION = "No description"
PROCESSING_TEMPLATE_INVALID = "Some template cards could not be read and will be skipped: {paths}"
PROCESSING_PLAN_CATEGORY = "Category: {category}"
PROCESSING_PLAN_OWNER = "Owner: {name}"
PROCESSING_PLAN_ASKED_BY = "Asked by: {name}"
PROCESSING_PLAN_SCAFFOLD = "A starter body will be added"
PROCESSING_PREVIEW_ACTION = "Preview"
PROCESSING_CONFIRM_ACTION = "Confirm"
PROCESSING_CANCEL_ACTION = "Cancel"
PROCESSING_DONE_ACTION = "Done"
PROCESSING_DESTINATION = "Destination: {path}"
PROCESSING_PLAN_TITLE = "Ready to Apply"
PROCESSING_SUCCESS_TITLE = "Capture Processed"
PROCESSING_SUCCESS_BODY = "The note was moved to {path}"
PROCESSING_UNRESOLVED = "Unresolved references: {names}"
PROCESSING_SCHEME_WARNING = "{count} inbound references will become unresolved because the note changes scheme"
PROCESSING_REFERENCE_WARNING = "{count} inbound references point to this capture and will become unresolved"
PROCESSING_EMPTY_OUTCOME = "Choose an outcome before previewing"
PROCESSING_INVALID_DATE = "Enter a due date as YYYY-MM-DD or leave it empty"
PROCESSING_READ_FAILED = "Could not read this capture: {detail}"
PROCESSING_PLAN_FAILED = "Could not prepare the processing preview: {detail}"
PROCESSING_FAILED = "Could not process the capture: {detail}"
PROCESSING_REFRESH_FAILED = "The capture was processed, but the Inbox could not be refreshed: {detail}"
PROCESSING_MISSING = "This capture is no longer in the Inbox"
NOTE_COUNT_ONE = "1 note"
NOTE_COUNT_MANY = "{count} notes"
COMPOSER_LABEL = "Capture a Thought"
COMPOSER_HINT = "The first line becomes the title"
CAPTURE_ACTION = "Capture"
REFRESH_ACTION = "Refresh"
EMPTY_TITLE = "Nothing Captured Yet"
EMPTY_BODY = "Write a thought above. The first line becomes the title"
PREVIEW_TITLE = "Preview"
PREVIEW_EMPTY = "Select a note to read it"
WORKING = "Working"

PROCESSING_OUTCOME_LABELS = MappingProxyType(
    {
        "trash": "Trash",
        "later": "Later",
        "reference": "Reference",
        "project": "Project",
        "log": "Log Entry",
        "append_step": "Append Step",
        "done_now": "Done Now",
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

CAPTURE_EMPTY = "Write a thought before capturing"
CAPTURE_FAILED = "Could not capture the thought: {detail}"
VAULT_SELECTION_FAILED = "Could not save the vault selection: {detail}"
REFRESH_FAILED = "Could not refresh the inbox: {detail}"
PREVIEW_FAILED = "Could not read this note: {detail}"
SETTINGS_UNREADABLE = "Saved preferences could not be read. Choose a vault to continue"
VAULT_MISSING = "That folder does not exist. Choose a vault to continue"
VAULT_NOT_DIRECTORY = "That path is not a folder. Choose a vault to continue"
VAULT_UNREADABLE = "That folder cannot be read. Choose a vault to continue"
VAULT_NOT_EMPTY = "That folder is not empty. Choose an empty folder or an existing vault"
VAULT_CREATED_NOT_REMEMBERED = "The vault was created, but it could not be remembered: {detail}"
LOG_MODE_NOT_REMEMBERED = "The Log view was changed, but the preference could not be saved: {detail}"
LOG_PLACEHOLDER = "The Log calendar and date tree appear here"
LOG_MONTH_ENTRY_MARK = "This month has an entry"
LOG_YEAR_ENTRY_MARK = "This year has an entry"
LOG_PREVIOUS_MONTH = "Previous Month"
LOG_NEXT_MONTH = "Next Month"
LOG_EMPTY = "No entries yet"
LOG_UNDATED = "Undated"
LOG_NEW_MONTH_ENTRY = "Write an entry for {period}"
LOG_NEW_YEAR_ENTRY = "Write an entry for {year}"
LOG_OPEN_MONTH_ENTRY = "Open the {period} entry"
LOG_OPEN_YEAR_ENTRY = "Open the {year} entry"
LOG_CREATE_FAILED = "The log entry could not be created: {detail}"
LOG_ENTRY_TITLE = "Log Entry"
LOG_ENTRY_BODY = "Write a dated entry for {date}"
LOG_TITLE_LABEL = "Title"
LOG_TITLE_REQUIRED = "Enter a title for the log entry"
LOG_CARD_LABEL = "Starter"
LOG_CARD_EMPTY = "Empty - No Starter Body"
LOG_CARD_DESCRIPTION_EMPTY = "No starter body"
LOG_CREATE_ACTION = "Write Entry"
LOG_TODAY_ENTRY = "Today’s Entry"
LOG_MODE_ENTRIES = "Entries"
LOG_MODE_EVERYTHING = "Everything"


VAULT_PATH_REQUIRED = "Enter the folder path for the vault"

PAGE_BACK = "Back"
PAGE_EDIT = "Edit"
PAGE_DONE = "Done"
PAGE_ACTIONS = "Page Actions"
PAGE_RENAME = "Rename…"
PAGE_TRASH = "Move to Trash"
PAGE_EMPTY = "Select a note to open it"
PAGE_IDENTITY_LABEL = "Identity"
PAGE_PATH_LABEL = "Path"
PAGE_BODY_LABEL = "Body (Markdown)"
PAGE_TYPE_LABEL = "Type"
PAGE_CATEGORY_LABEL = "Category"
PAGE_STATUS_LABEL = "Status"
PAGE_DUE_DATE_LABEL = "Due date"
PAGE_DATE_LABEL = "Date"
PAGE_DATE = "Date: {date}"
PAGE_NO_DATE = "No date"
PAGE_LOG_DATE_REQUIRED = "A log entry needs a date"
PAGE_DATE_CHANGE_FAILED = "The date could not be changed: {detail}"
PAGE_DATE_CHANGE_PARTIAL = "The date changed. {report}"
PAGE_TYPE_CHANGE_FAILED = "The note type could not be changed: {detail}"
PAGE_TYPE_CHANGE_PARTIAL = "The note type changed. {report}"
PAGE_REWRITE_UPDATED = "Updated: {paths}"
PAGE_REWRITE_NOT_UPDATED = "Not updated: {paths}"
PAGE_REWRITE_NONE = "none"
PAGE_REWRITE_CHANGED_ON_DISK = "Changed on disk after planning"
PAGE_REWRITE_PROBLEM = "{path} ({reason})"
PAGE_ASKED_BY_LABEL = "Asked by"
PAGE_ASKED_BY_HINT = "Person or group that requested it"
PAGE_OWNER_LABEL = "Owner"
PAGE_OWNER_HINT = "Person or team accountable for it"
ROLE_REFERENCE_TITLE = "Create Reference"
ROLE_REFERENCE_BODY = "Create a reference for {name}. Choose a category, or no category"
ROLE_REFERENCE_CATEGORY_LABEL = "Category"
ROLE_REFERENCE_CATEGORY_HINT = "Existing category or a new one"
ROLE_REFERENCE_NO_CATEGORY = "No Category"
ROLE_REFERENCE_CREATE = "Create Reference"
ROLE_NAME_OWNER_TITLE = "Set Owner"
ROLE_NAME_ASKED_BY_TITLE = "Set Asked By"
ROLE_NAME_BODY = "Enter a name, or pick one from this vault"
ROLE_NAME_LABEL = "Name"
ROLE_NAME_HINT = "Note name"
ROLE_NAME_CLEAR = "Clear"
ROLE_NAME_SAVE = "Save"
PAGE_OWNER_SET = "Set Owner…"
PAGE_ASKED_BY_SET = "Set Asked By…"
ROLE_LINK_MISSING = "No page matches this name. Create one"
ROLE_LINK_AMBIGUOUS = "More than one page matches this name. Choose one"
PAGE_RAW_WARNING = "This page’s metadata cannot be read. Edit the text directly; labels return once it parses"
PAGE_RAW_SAVE = "Save Text"
PAGE_SAVING = "Saving"
PAGE_SAVED = "Saved"
PAGE_UNSAVED = "Unsaved Changes"
PAGE_OPEN_FAILED = "Could not open this page: {detail}"
PAGE_SAVE_FAILED = "Could not save this page: {detail}"
PAGE_CONFLICT_CHANGED = "This page changed on disk. Reload it or overwrite it with the draft"
PAGE_CONFLICT_MISSING = "This page no longer exists at its path. Recreate it or discard the draft"
PAGE_CONFLICT_LEAVE = "Resolve the disk conflict before leaving this page"
PAGE_PENDING_DIALOG = "Confirm or cancel the open page action before leaving this page"
PAGE_CONFLICT_TITLE = "This Page Changed on Disk"
PAGE_CONFLICT_RELOAD = "Reload from Disk"
PAGE_CONFLICT_OVERWRITE = "Overwrite with Draft"
PAGE_CONFLICT_RECREATE = "Recreate Page"
PAGE_CONFLICT_DISCARD = "Discard Draft"
PAGE_AMBIGUOUS_TITLE = "Choose a Page"
PAGE_AMBIGUOUS_BODY = "More than one page matches this reference"
PAGE_REPAIR_PENDING = "Choose how to handle the old link names before leaving this page"
PAGE_REPAIR_TITLE = "Repair Link Names"
PAGE_REPAIR_BODY = "The name “{old}” cannot be a filename. The page was created as “{new}”"
PAGE_REPAIR_COUNT = "{detail} still use the old name"
PAGE_REPAIR_REWRITE = "Rewrite Links"
PAGE_REPAIR_KEEP = "Keep Old Links"
PAGE_REPAIR_CANCEL = "Cancel Creation"
PAGE_REPAIR_FAILED = "Some links could not be repaired: {detail}"
PAGE_REPAIR_PARTIAL = "The links were repaired. {report}"
PAGE_TYPE_CHANGE_TITLE = "Change Page Type?"
PAGE_TYPE_CHANGE_BODY = "{detail} will become unresolved"
PAGE_TYPE_CHANGE_CONFIRM = "Change Type"
PAGE_RENAME_TITLE = "Rename Page"
PAGE_RENAME_LABEL = "New name"
PAGE_RENAME_PREVIEW = "{detail} will be updated"
PAGE_RENAME_PREVIEW_ACTION = "Preview"
PAGE_RENAME_CONFIRM = "Rename"
PAGE_RENAME_FAILED = "Could not rename this page: {detail}"
PAGE_RENAME_PARTIAL = "The page was renamed. {report}"
PAGE_TRASH_FAILED = "Could not move this page to trash: {detail}"
PAGE_TRASH_MOVED = "Moved to Trash"
PAGE_TRASH_RESTORED = "Restored from Trash"
PAGE_TRASH_RESTORE_FAILED = "Could not restore this page: {detail}"
PAGE_CANCEL = "Cancel"
PAGE_RAW_UPGRADED = "The page now parses; labels are available"
PAGE_TYPE_CHANGE_LEAVE = "Confirm or cancel the type change before leaving this page"
PAGE_NONE = "None"
PAGE_NEW = "New Page"
PAGE_CATEGORY_HINT = "Any label, such as person or place"
PAGE_CATEGORY_INVALID = "A category must be one non-empty folder name without path separators"
PAGE_CATEGORY_MOVE_TITLE = "Move This Page?"
PAGE_CATEGORY_MOVE_BODY = "The page will move to {path}. Its name and references stay the same"
PAGE_CATEGORY_MOVE_CONFIRM = "Move Page"
PAGE_CATEGORY_MOVE_FAILED = "Could not move this page to its category folder: {detail}"
PAGE_STEP_TICK = "Mark Complete"
PAGE_STEP_UNTICK = "Reopen"
PAGE_STEP_OWNERS = "Owners: {owners}"
PAGE_STEP_OWNERS_LABEL = "Owners: "
PAGE_STEP_PLAN = "Plan: {date}"
PAGE_STEP_ACTUAL = "Done: {date}"
PAGE_STEP_TAGS = "Tags: {tags}"
PAGE_STEP_WAITING = "Waiting"
PAGE_STEP_FAILED = "Could not update this step: {detail}"
PAGE_STEP_PLAN_ACTION = "Set Plan Date…"
PAGE_STEP_CLEAR_PLAN = "Clear Plan Date"
PAGE_STEP_OWNER_ACTION = "Edit Owners…"
PAGE_STEP_OWNER_TITLE = "Owners"
PAGE_STEP_OWNER_ADD = "Add Owner"
PAGE_STEP_OWNER_HINT = "Note name"
PAGE_STEP_OWNER_DUPLICATE = "{owner} is already an owner"
PAGE_STEP_OWNER_REMOVE = "Remove {owner}"
PAGE_PROJECT_NO_STATUS = "No status"
PAGE_PROJECT_DUE_ADD = "Add Due Date…"
PAGE_PROJECT_DUE_CLEAR = "Clear Due Date"
PAGE_PROJECT_NO_DUE = "No due date"
PAGE_PROJECT_EMPTY_BODY = "This project has no body yet"
PAGE_CONNECTIONS_TITLE = "Connections"
PAGE_CONNECTIONS_LINKED_FROM = "Linked From"
PAGE_CONNECTIONS_OWNED_PROJECTS = "Owned Projects"
PAGE_CONNECTIONS_OWNED_STEPS = "Owned Steps"
PAGE_CONNECTIONS_REQUESTED_PROJECTS = "Requested Projects"
PAGE_CONNECTIONS_SHOW_COMPLETED_STEPS = "Show Completed Steps"
PAGE_CONNECTIONS_SHOW_FINISHED_PROJECTS = "Show Finished Projects"
REVIEW_DUE_STEP_TITLE = "Due Step"
REVIEW_WAITING_STEP_TITLE = "Waiting Step"
REVIEW_DO_NOW = "Do It Now"
REVIEW_POSTPONE = "Postpone…"
REVIEW_DELEGATE = "Delegate…"
REVIEW_REASSIGN = "Reassign…"
REVIEW_OWNER_LABEL = "Owner"
REVIEW_OWNER_REQUIRED = "Enter an owner before confirming"
REVIEW_POSTPONE_LABEL = "New plan date (YYYY-MM-DD)"
REVIEW_INVALID_DATE = "Enter the plan date as YYYY-MM-DD"
REVIEW_CONFIRM = "Confirm"
REVIEW_STEP_OWNERS = "Owners: {owners}"
REVIEW_LAUNCH_DIGEST_ONE = "1 due step needs attention"
REVIEW_LAUNCH_DIGEST_MANY = "{count} due steps need attention"
REVIEW_LAUNCH_DIGEST_ACTION = "Start Review"

PAGE_TYPE_LABELS = MappingProxyType(
    {
        "note": "Note",
        "project": "Project",
        "reference": "Reference",
        "log": "Log",
    }
)


class CopyFormatter:
    """Format user-facing counts and labels for the interface.

    Notes
    -----
    The copy constants remain the single catalog; this class owns the
    formatting rules. Call the classmethods directly.
    """

    @classmethod
    def log_entry_count(cls, count: int) -> str:
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

    @classmethod
    def log_day_tooltip(cls, day: int, count: int) -> str:
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

    @classmethod
    def reference_count(cls, count: int, notes: int) -> str:
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

    @classmethod
    def note_count(cls, count: int) -> str:
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

    @classmethod
    def open_step_count(cls, count: int) -> str:
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

    @classmethod
    def review_pending(cls, count: int) -> str:
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
