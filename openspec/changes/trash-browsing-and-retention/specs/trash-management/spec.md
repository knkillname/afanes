# Spec Delta

## Purpose

Defines durable trash storage, metadata, restoration, permanent deletion, and retention so discarded notes remain recoverable for a fixed period without becoming active vault notes.

## ADDED Requirements

### Requirement: Trashing stores an entry under a unique identity

Moving a note to trash SHALL write its trash metadata into the note frontmatter and SHALL store it under `trash/` with a pure UUID filename. The operation SHALL preserve the body and every unknown frontmatter key, SHALL choose another UUID when the first one is taken, and SHALL NOT overwrite an existing trash entry.

#### Scenario: Trashing records metadata and a UUID filename

- **WHEN** the user moves an active note to Trash
- **THEN** the note is stored as `trash/<uuid>.md` with its birthplace and trashed day in the frontmatter

#### Scenario: A taken UUID is not overwritten

- **WHEN** the selected UUID filename already exists in `trash/`
- **THEN** a different UUID is selected and the existing file is unchanged

#### Scenario: Trashing preserves the body and unknown keys

- **WHEN** a note with custom frontmatter keys and a Markdown body is moved to Trash
- **THEN** the custom keys and the body are unchanged

#### Scenario: An unwritable note is not trashed

- **WHEN** the trash metadata cannot be written to the note
- **THEN** the note stays at its active path and the failure is reported

### Requirement: Trash metadata records birthplace and day

A managed trash entry SHALL carry `trashed_from` as a vault-relative note path and `trashed_on` as a local calendar date. A restore SHALL remove both keys from the frontmatter.

#### Scenario: A trashed note records both values

- **WHEN** a note at `projects/Build shed.md` is moved to Trash on 2026-11-13
- **THEN** its frontmatter records `trashed_from: projects/Build shed.md` and `trashed_on: 2026-11-13`

#### Scenario: Restore removes the trash metadata

- **WHEN** a managed entry is restored
- **THEN** neither `trashed_from` nor `trashed_on` remains in the restored note

#### Scenario: Other frontmatter survives a restore

- **WHEN** a trashed note with unknown frontmatter keys is restored
- **THEN** those keys remain in the restored note

### Requirement: Unmanaged trash files are ignored

A file under `trash/` without a valid `trashed_from` SHALL NOT appear in the Trash destination, global search, or the Trash count. The application MUST NOT restore, permanently delete, or expire it; it SHALL remain on disk.

#### Scenario: A file without a birthplace is hidden

- **WHEN** `trash/Old note.md` has no `trashed_from`
- **THEN** it does not appear in Trash or search and its count is unchanged

#### Scenario: Empty Trash leaves an unmanaged file

- **WHEN** the user empties the Trash while an unmanaged file is present
- **THEN** the managed entries are removed and the unmanaged file remains

#### Scenario: Retention leaves an unmanaged file

- **WHEN** an unmanaged file is older than 30 days
- **THEN** it is not deleted by retention

### Requirement: An unsafe birthplace makes an entry unmanaged

An entry whose `trashed_from` is absolute, escapes the vault, points under `trash/` or `templates/`, points through a hidden folder, or otherwise cannot be a scanned note path SHALL be treated as unmanaged.

#### Scenario: Ancestor traversal is ignored

- **WHEN** an entry records `trashed_from: ../Outside.md`
- **THEN** the entry is hidden and is never restored or expired

#### Scenario: A trash birthplace is ignored

- **WHEN** an entry records `trashed_from: trash/Ada.md`
- **THEN** the entry is hidden and remains on disk

#### Scenario: A template birthplace is ignored

- **WHEN** an entry records `trashed_from: templates/Ada.md`
- **THEN** the entry is hidden and remains on disk

### Requirement: A missing trashed day starts the retention clock

When a managed entry has a valid birthplace but no usable `trashed_on`, the application SHALL write the current local calendar day as its trashed day. Retention SHALL then start from that day. If the write fails, the entry SHALL remain visible and SHALL NOT expire.

#### Scenario: A missing day is stamped once

- **WHEN** an entry with a valid birthplace and no trashed day is loaded
- **THEN** the current local day is written as its trashed day

#### Scenario: A malformed day is replaced

- **WHEN** an entry has a valid birthplace and an unreadable trashed day
- **THEN** the current local day replaces the unusable value

#### Scenario: A failed stamp keeps the entry visible

- **WHEN** the trashed day cannot be written because the vault is read-only
- **THEN** the entry remains visible and is not expired

### Requirement: The trash UUID is never shown to the user

The interface SHALL identify a managed trash entry by its title and birthplace and MUST NOT display its UUID in navigation, browser rows, page chrome, search results, success messages, processing previews, notices, or dialogs.

#### Scenario: The page identifies the birthplace

- **WHEN** a managed trash entry is open
- **THEN** its page chrome shows the birthplace rather than the UUID filename

#### Scenario: The processing preview names Trash

- **WHEN** a processing plan selects the Trash outcome
- **THEN** the plan names Trash without showing a UUID path

#### Scenario: A trash failure hides the UUID

- **WHEN** a trash, restore, or delete operation fails
- **THEN** the message describes the failure without displaying the UUID filename

### Requirement: A trashed note opens read-only

Selecting a managed entry SHALL open its content read-only with its birthplace and trashed day visible. The page SHALL offer Restore and Delete Permanently. Editing, renaming, and step changes MUST NOT be available for a trashed note.

#### Scenario: A trashed note opens read-only

- **WHEN** the user selects a managed entry in Trash
- **THEN** the page shows its body without an edit mode

#### Scenario: The page names the origin and day

- **WHEN** a managed entry is open
- **THEN** the page shows its birthplace and trashed day

#### Scenario: The page offers the trash actions

- **WHEN** a managed entry is open
- **THEN** Restore is available and Delete Permanently is available from the secondary menu

### Requirement: Restore returns a note to its birthplace

Restoring a managed entry SHALL publish it at its recorded birthplace, create missing parent folders, remove its trash metadata, and remove the trash entry. A free birthplace SHALL restore immediately.

#### Scenario: A free birthplace restores immediately

- **WHEN** the user restores an entry whose birthplace does not exist
- **THEN** the note is written there without a confirmation surface

#### Scenario: Missing parents are created

- **WHEN** a note whose birthplace is `reference/people/Ada.md` is restored and `reference/people/` is missing
- **THEN** the folder is created and the note is written inside it

#### Scenario: A restored note leaves Trash

- **WHEN** a restore succeeds
- **THEN** the UUID file disappears from `trash/` and the note appears in its active group

#### Scenario: A restore removes the trash metadata

- **WHEN** a restore succeeds
- **THEN** the restored file has neither `trashed_from` nor `trashed_on`

### Requirement: An occupied birthplace is overwritten only after confirmation

When the birthplace is occupied by a file, restore SHALL warn that the existing file will be permanently overwritten and SHALL write nothing unless the user confirms. The confirmation SHALL place Cancel before the affirmative action. On confirmation, the existing file SHALL be permanently replaced by the restored note.

#### Scenario: An occupied birthplace warns

- **WHEN** the birthplace of the selected entry belongs to another file
- **THEN** a confirmation names the file that will be overwritten

#### Scenario: Cancel writes nothing

- **WHEN** the user cancels the overwrite confirmation
- **THEN** the existing file and the trash entry are unchanged

#### Scenario: Confirmation overwrites permanently

- **WHEN** the user confirms the overwrite
- **THEN** the existing file is replaced by the restored note and is not recoverable

#### Scenario: A directory is not overwritten

- **WHEN** the birthplace belongs to a directory
- **THEN** the restore fails without deleting the directory

### Requirement: Undo does not overwrite an occupied birthplace

The Undo action on the trash toast SHALL restore the just-trashed note only while its birthplace is free. When the birthplace is occupied, Undo SHALL leave the note in Trash and report that the birthplace is taken.

#### Scenario: Undo restores a free birthplace

- **WHEN** the user selects Undo and the birthplace is free
- **THEN** the note returns to its birthplace

#### Scenario: Undo reports a collision

- **WHEN** the user selects Undo and another file occupies the birthplace
- **THEN** the note stays in Trash and the collision is reported

#### Scenario: Undo writes nothing on collision

- **WHEN** Undo reports a collision
- **THEN** neither the trashed note nor the occupying file is changed

### Requirement: Managed notes can be permanently deleted

The Trash destination SHALL offer Delete Permanently for one managed entry and Empty Trash for all managed entries. Each action SHALL require confirmation with Cancel before the affirmative action. Empty Trash SHALL delete only managed entries and SHALL leave unmanaged files on disk.

#### Scenario: One entry is deleted after confirmation

- **WHEN** the user confirms Delete Permanently for a managed entry
- **THEN** that UUID file is removed and no other file changes

#### Scenario: Empty Trash removes managed entries

- **WHEN** the user confirms Empty Trash
- **THEN** every managed entry is removed and the Trash count becomes zero

#### Scenario: Empty Trash leaves unmanaged files

- **WHEN** Empty Trash completes while unmanaged files are present
- **THEN** those files remain on disk

#### Scenario: Cancel keeps every entry

- **WHEN** the user cancels either deletion confirmation
- **THEN** no trashed file is removed

### Requirement: Managed notes expire after 30 days

A managed entry SHALL be permanently deleted when its trashed day is 30 or more days before the current local day. Retention SHALL run when the vault opens and every time Trash is selected. It SHALL be silent and MUST NOT require confirmation or offer undo. Expired deletion MUST NOT remove unmanaged files.

#### Scenario: An entry expires at 30 days

- **WHEN** a managed entry was trashed 30 days before the current local day
- **THEN** it is deleted when retention next runs

#### Scenario: A younger entry remains

- **WHEN** a managed entry was trashed 29 days before the current local day
- **THEN** it remains in Trash

#### Scenario: Opening the vault runs retention

- **WHEN** the vault opens with an expired managed entry
- **THEN** the entry is deleted before the Trash count is shown

#### Scenario: Selecting Trash runs retention

- **WHEN** the user selects Trash with an expired managed entry
- **THEN** the entry is deleted before the Trash list is shown

#### Scenario: Retention is silent

- **WHEN** retention deletes an expired entry
- **THEN** no confirmation, undo, or destructive dialog is shown

### Requirement: Trash remains usable when maintenance fails

If retention or day stamping cannot write, the vault SHALL still open and Trash SHALL still list every managed entry. The failure SHALL be reported in a persistent banner owned by the trash state.

#### Scenario: A read-only vault still lists Trash

- **WHEN** a read-only vault contains managed entries
- **THEN** the vault opens and the Trash destination lists them

#### Scenario: A cleanup failure is reported

- **WHEN** retention cannot delete an expired entry
- **THEN** the entry remains and a banner reports the failure

#### Scenario: A later success clears the banner

- **WHEN** a later cleanup succeeds
- **THEN** the trash banner is cleared
