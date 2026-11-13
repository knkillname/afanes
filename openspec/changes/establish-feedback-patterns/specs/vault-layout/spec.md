# Spec Delta

## MODIFIED Requirements

### Requirement: Trash naming and recovery

Moving a note to trash SHALL preserve its content and SHALL choose a unique filename when the name
is already present. A trashed note MAY be restored by moving it back. The page's undo action MAY
restore the note it just trashed; general trash browsing and automatic restore are outside this
capability.

#### Scenario: Trash preserves content

- **WHEN** a note is moved to `trash/`
- **THEN** its bytes and body are unchanged

#### Scenario: Trash collision is unique

- **WHEN** `trash/Ada.md` already exists and another `Ada` is trashed
- **THEN** the second note receives a distinct trash filename

#### Scenario: Manual restore resolves references

- **WHEN** a trashed note is moved back to an active folder
- **THEN** its inbound references resolve on the next scan

#### Scenario: Undo restores the just-trashed note

- **WHEN** the page's undo action restores a note it just trashed and the original path is free
- **THEN** the note returns to that path and its inbound references resolve on the next scan

#### Scenario: Undo does not overwrite an occupied path

- **WHEN** the page's undo action would restore a note to a path that now exists
- **THEN** the note stays in trash and no file is overwritten
