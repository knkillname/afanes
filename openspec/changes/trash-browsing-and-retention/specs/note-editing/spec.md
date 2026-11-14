# Spec Delta

## MODIFIED Requirements

### Requirement: The page offers rename and trash actions

The page SHALL offer Rename for active notes, references, and projects, and SHALL hide it for log
entries. For an active note, the page SHALL offer Trash for every type. A trashed note is read-only
and offers Restore and Delete Permanently instead. Rename SHALL use the existing preview,
confirmation, atomic-write, and inbound-reference rules. Rename SHALL update a level-1 heading only
when its text matches the old identity. After a rename or trash, the page history SHALL be updated so
Back never returns to a path that no longer exists.

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

#### Scenario: A trashed note is not an active page

- **WHEN** a trashed note is open
- **THEN** the page offers Restore and Delete Permanently instead of Rename and Move to Trash
