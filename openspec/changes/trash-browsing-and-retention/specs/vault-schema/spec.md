# Spec Delta

## MODIFIED Requirements

### Requirement: A vault requires a valid settings file

Opening a folder without `afanes.yaml` SHALL be refused. Opening MUST NOT create the file. A vault
with a valid file SHALL pass schema validation without modifying any vault file, including when the
vault is read-only.

#### Scenario: A missing settings file is refused

- **WHEN** a folder has no `afanes.yaml`
- **THEN** the application refuses to open it as a vault

#### Scenario: Opening does not create the file

- **WHEN** an unversioned folder is opened
- **THEN** no `afanes.yaml` is created

#### Scenario: Opening a valid vault writes nothing

- **WHEN** a vault with a valid settings file passes schema validation
- **THEN** validation creates, modifies, or deletes no vault file

#### Scenario: Scanning writes nothing

- **WHEN** a versioned vault is scanned or refreshed
- **THEN** no vault file is created, modified, or deleted

#### Scenario: A read-only vault with a valid file opens

- **WHEN** a read-only folder contains a valid `afanes.yaml`
- **THEN** the vault opens for browsing

#### Scenario: A read-only vault without a file is refused

- **WHEN** a read-only folder has no `afanes.yaml`
- **THEN** the application refuses to open it as a vault
