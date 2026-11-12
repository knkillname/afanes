# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""User-facing copy for the headless command surface.

Command modules read text from this module so messages stay consistent with the
interface and can be localized later. No command writes user-facing text inline.
"""

PROGRAM = "afanes"
DESCRIPTION = "Work with Afanes vaults without opening the interface."
VAULT_COMMAND = "vault"
VAULT_HELP = "Create and manage vault directories."
CREATE_COMMAND = "create"
CREATE_HELP = "Create and seed a new vault directory."
CREATE_DIRECTORY_HELP = "Vault directory. Missing folders in the path are created."
NO_REMEMBER_HELP = "Do not make the new vault the one Afanes opens next launch."
TEMPLATE_OPTION_HELP = "Bundled starter content to write into the new vault."
TEMPLATES_COMMAND = "templates"
TEMPLATES_HELP = "List the bundled starter content without opening a vault."
CREATED_VAULT = "Created vault {path}"
CREATED_PARENTS = "Parent folders created: {paths}"
SEEDED_FOLDERS = "Seeded: {folders}"
TEMPLATE_USED = "Template: {template}"
WRITTEN_NOTES = "Notes written: {notes}"
TEMPLATE_NONE = "none"
TEMPLATE_LINE = "{identifier}: {label} - {description} ({notes})"
TEMPLATE_NOTES_ONE = "1 note"
TEMPLATE_NOTES_MANY = "{count} notes"
TEMPLATES_FAILED = "Could not read the bundled starter content: {detail}"
REMEMBERED = "Remembered as the vault to open next launch."
NOT_REMEMBERED = "Not remembered; use --vault to open it on the next run."
CREATE_FAILED = "Could not create the vault: {detail}"
REMEMBER_FAILED = "The vault was created at {path} but could not be remembered: {detail}"
