# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""English source messages for the headless command surface.

Every public constant is a gettext source message. The constant name is the
message context, so identical English values can translate independently.
Command identifiers stay untranslated and live in the command parser.
"""

PROGRAM = "afanes"
DESCRIPTION = "Work with Afanes vaults without opening the interface"
VAULT_COMMAND = "vault"
VAULT_HELP = "Create and manage vault directories"
CREATE_COMMAND = "create"
CREATE_HELP = "Create and seed a new vault directory"
CREATE_DIRECTORY_HELP = "Vault directory. Missing folders in the path are created"
NO_REMEMBER_HELP = "Do not make the new vault the one Afanes opens next launch"
TEMPLATE_OPTION_HELP = "Bundled starter content to write into the new vault"
TEMPLATES_COMMAND = "templates"
TEMPLATES_HELP = "List the bundled starter content without opening a vault"
ADOPT_COMMAND = "adopt"
ADOPT_HELP = "Add the vault settings file to an existing folder"
ADOPT_DIRECTORY_HELP = "Existing folder with the five default folders"
ADOPT_NO_REMEMBER_HELP = "Do not make the adopted vault the one Afanes opens next launch"
CREATED_VAULT = "Created vault {path}"
ADOPTED_VAULT = "Adopted vault {path}"
ALREADY_VAULT = "{path} is already a vault with schema version {version}; nothing changed"
CREATED_PARENTS = "Parent folders created: {paths}"
SEEDED_FOLDERS = "Seeded: {folders}"
SETTINGS_FILE = "Settings file: {path} (schema version {version})"
TEMPLATE_USED = "Template: {template}"
WRITTEN_NOTES = "Notes written: {notes}"
TEMPLATE_NONE = "none"
TEMPLATE_LINE = "{identifier}: {label} - {description} ({notes})"
TEMPLATE_NOTES_ONE = "1 note"
TEMPLATE_NOTES_MANY = "{count} notes"
TEMPLATES_FAILED = "Could not read the bundled starter content: {detail}"
REMEMBERED = "Remembered as the vault to open next launch"
NOT_REMEMBERED = "Not remembered; use --vault to open it on the next run"
CREATE_FAILED = "Could not create the vault: {detail}"
REMEMBER_FAILED = "The vault was created at {path} but could not be remembered: {detail}"
ADOPT_FAILED = "Could not adopt the vault: {detail}"
ADOPT_REMEMBER_FAILED = "The vault at {path} was adopted but could not be remembered: {detail}"

HELP_OPTION = "Show this help message and exit"
USAGE_ERROR = "Invalid command-line arguments"

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
