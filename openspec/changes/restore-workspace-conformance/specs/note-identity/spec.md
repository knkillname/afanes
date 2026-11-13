# Spec Delta

## ADDED Requirements

### Requirement: Reference rewrites report affected notes

Every reference rewrite, including rename, type change, date change, and link repair, SHALL report
which notes were updated and which were not. A skipped or failed note SHALL be named with its reason.
Paths SHALL be shown relative to the vault root.

#### Scenario: Rename reports every affected note

- **WHEN** a rename rewrites one note and skips another
- **THEN** the report names the updated note and the skipped note with its reason

#### Scenario: Type change reports every affected note

- **WHEN** a type change rewrites one note and fails on another
- **THEN** the report names the updated note and the failed note with its reason

#### Scenario: Date change reports every affected note

- **WHEN** a date change rewrites one note and skips another
- **THEN** the report names the updated note and the skipped note with its reason

#### Scenario: Repair reports every affected note

- **WHEN** a link repair rewrites one note and fails on another
- **THEN** the report names the updated note and the failed note with its reason
