# Spec Delta

## ADDED Requirements

### Requirement: Trash is immediate and undoable

Moving a page to trash SHALL take effect immediately and SHALL offer an Undo toast. Undo SHALL
restore the just-trashed note to its original path while that path is free. Undo MUST NOT overwrite
an occupied path; it SHALL report the collision and leave the note in trash. The undo opportunity
SHALL belong to the current session and SHALL end when the toast is dismissed or replaced.

#### Scenario: Trash moves immediately

- **WHEN** the user selects Trash for an open page
- **THEN** the page moves to trash without a confirmation surface

#### Scenario: Undo restores the note

- **WHEN** the user selects Undo on the trash toast while the original path is free
- **THEN** the note returns to its original path and the page history no longer points at the trash destination

#### Scenario: An occupied path is not overwritten

- **WHEN** the user selects Undo and the original path now belongs to another note
- **THEN** the application reports the collision, leaves the trashed note in trash, and writes nothing

#### Scenario: The undo opportunity is transient

- **WHEN** the trash toast is dismissed, replaced, or the application restarts
- **THEN** the page no longer offers undo for that trash action

### Requirement: The page offers rename and trash actions

The page SHALL offer Rename for notes, references, and projects, and SHALL hide it for log entries.
The page SHALL offer Trash for every type. Rename SHALL use the existing preview, confirmation,
atomic-write, and inbound-reference rules. Rename SHALL update a level-1 heading only when its text
matches the old identity. After a rename or trash, the page history SHALL be updated so Back never
returns to a path that no longer exists.

#### Scenario: Rename previews affected references

- **WHEN** the user requests a rename from the page
- **THEN** the application reports the affected note and reference counts before asking for
  confirmation

#### Scenario: Matching heading follows the identity

- **WHEN** a note's first heading text equals its old identity and the note is renamed
- **THEN** the heading is updated to the new identity

#### Scenario: Custom heading is preserved

- **WHEN** a note's first heading differs from its old identity and the note is renamed
- **THEN** the heading is unchanged

#### Scenario: Trash does not preview inbound references

- **WHEN** the user requests trash from the page
- **THEN** the application moves the note immediately and does not report the destination or inbound references first

#### Scenario: History skips the removed path

- **WHEN** the current page is renamed or trashed
- **THEN** Back opens the previous page and never the old path

#### Scenario: A log entry has no Rename action

- **WHEN** a log entry is open
- **THEN** the page offers no Rename action

#### Scenario: A log entry can be trashed

- **WHEN** a log entry is open
- **THEN** the page offers the Trash action

## REMOVED Requirements

### Requirement: Rename and trash are available from the page

**Reason**: Trash is now immediate and undoable, so the pre-trash preview scenario no longer applies.
The remaining rename and trash availability rules are preserved under the replacement requirement.

**Migration**: No user action is required. Rename keeps its preview and confirmation; trash moves
immediately and offers Undo.
