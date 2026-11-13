# Spec Delta

## ADDED Requirements

### Requirement: Trashing leaves inbound references unresolved

Trashing a note SHALL NOT report or rewrite its inbound references before the move. After the move,
those references SHALL be unresolved and remain in the referring notes. The page's undo action SHALL
restore the note so the references resolve on the next scan.

#### Scenario: Trashing does not report a count

- **WHEN** the user trashes a note that has inbound references
- **THEN** the application moves the note without reporting a reference count first

#### Scenario: References become unresolved

- **WHEN** a referenced note is moved to trash
- **THEN** its inbound references are reported as unresolved and remain in the referring notes

#### Scenario: Undo resolves the references

- **WHEN** a just-trashed note is restored by the page's undo action
- **THEN** its inbound references resolve on the next scan

#### Scenario: Role names remain after trashing

- **WHEN** a trashed note is named as a project owner, requester, or step owner
- **THEN** the project keeps the plain-text value and the connection becomes unresolved

#### Scenario: No referring note is rewritten

- **WHEN** a note is moved to trash
- **THEN** no referring note is modified

## REMOVED Requirements

### Requirement: Deletion reports inbound references

**Reason**: Trashing is now immediate and undoable, so the pre-trash reference report is removed.
The unresolved references remain visible in the referring notes, and Undo restores them.

**Migration**: No user action is required. A note moved to trash remains recoverable through the
trash toast for the current session; permanent deletion will define its own reference report in the
trash-room change.
