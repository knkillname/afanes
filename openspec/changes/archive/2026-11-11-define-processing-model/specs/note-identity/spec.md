# Spec Delta

## ADDED Requirements

### Requirement: Trashed notes are outside the catalog

Notes under `trash/` SHALL be excluded from identity and name uniqueness. Their names MAY be reused by active notes. A reference to a trashed note SHALL be unresolved.

#### Scenario: Trashed note is not in the catalog

- **WHEN** a note is moved to `trash/`
- **THEN** it is not part of the active note catalog

#### Scenario: Trashed name can be reused

- **WHEN** a note named `Ada` is in `trash/` and a new `Ada` note is created
- **THEN** the new note is accepted without a numeric suffix

#### Scenario: Reference to a trashed note is unresolved

- **WHEN** a note references a note that is under `trash/`
- **THEN** the reference is reported as unresolved

#### Scenario: Restored note resolves references

- **WHEN** a trashed note is moved back to an active folder
- **THEN** its inbound references resolve on the next scan

#### Scenario: Trash is excluded case-insensitively

- **WHEN** the vault contains `Trash/Ada.md`
- **THEN** it is excluded from identity and resolution

#### Scenario: Trashing does not rewrite notes

- **WHEN** a note is moved to `trash/`
- **THEN** no referring note is modified
