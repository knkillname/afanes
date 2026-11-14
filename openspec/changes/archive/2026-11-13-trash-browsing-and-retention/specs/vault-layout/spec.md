# Spec Delta

## MODIFIED Requirements

### Requirement: Trash is excluded from the catalog

Notes under `trash/` SHALL be excluded from the active scan, name uniqueness, and reference resolution. Trash matching SHALL be case-insensitive. Trashed notes SHALL remain readable on disk. A managed trashed note MAY be presented by the Trash destination without joining the active note catalog.

#### Scenario: Trashed note is not scanned

- **WHEN** a note is moved to `trash/`
- **THEN** it is absent from the scanned note set

#### Scenario: Reference to a trashed note is unresolved

- **WHEN** a note references a note that is under `trash/`
- **THEN** the reference is reported as unresolved

#### Scenario: Trashed name can be reused

- **WHEN** a note named `Ada` is in `trash/` and a new `Ada` note is created
- **THEN** the new note is accepted without a numeric suffix

#### Scenario: Case variant of trash is excluded

- **WHEN** the vault contains `Trash/Ada.md`
- **THEN** it is excluded from the catalog

#### Scenario: A managed trash entry stays outside the catalog

- **WHEN** the Trash destination lists a managed entry
- **THEN** that entry does not become part of the active note catalog

## REMOVED Requirements

### Requirement: Trash naming and recovery

**Reason**: Replaced by the durable UUID storage, frontmatter metadata, browsing, restore, and retention contract in `trash-management`.

**Migration**: Existing files under `trash/` remain on disk. A file without `trashed_from` and `trashed_on` becomes unmanaged and is not listed, restored, or expired; the user must move or delete it outside the application.
