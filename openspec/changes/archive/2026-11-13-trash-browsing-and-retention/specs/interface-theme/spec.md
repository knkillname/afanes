# Spec Delta

## MODIFIED Requirements

### Requirement: Reversible destructive actions offer undo

When an action can be undone without data loss, the interface SHALL offer Undo in a toast instead of
a confirmation. A user-invoked irreversible action SHALL use a confirmation that places Cancel first.
The undo opportunity SHALL be transient and SHALL end when the toast is dismissed or replaced.

#### Scenario: Trash offers Undo instead of a confirmation

- **WHEN** the user moves a note to trash
- **THEN** the move happens without a confirmation surface and a toast offers Undo

#### Scenario: Undo restores the action

- **WHEN** the user selects Undo on the toast for a reversible action
- **THEN** the action is reversed without data loss

#### Scenario: An irreversible action uses a confirmation

- **WHEN** the user invokes an action that cannot be undone
- **THEN** the interface asks for confirmation and places Cancel before the affirmative action

#### Scenario: A dismissed toast ends the undo opportunity

- **WHEN** the toast is dismissed or replaced before the user selects Undo
- **THEN** the reversible action is no longer offered for undo

#### Scenario: Scheduled retention is not user-invoked

- **WHEN** a managed trashed note reaches its 30-day limit
- **THEN** it is deleted without a confirmation dialog because no user action requested the deletion
