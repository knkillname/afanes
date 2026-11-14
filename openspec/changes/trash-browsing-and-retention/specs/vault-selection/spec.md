# Spec Delta

## MODIFIED Requirements

### Requirement: Opening a vault is read-only

Opening or scanning a vault SHALL NOT create or modify any vault file. After a vault opens,
scheduled trash retention MAY delete expired managed trash entries before the workspace is shown.
The `inbox/` directory SHALL be created only by a capture.

#### Scenario: Opening does not create the inbox

- **WHEN** a vault without an `inbox/` directory is opened
- **THEN** no `inbox/` directory is created

#### Scenario: Scanning changes nothing

- **WHEN** the application scans a vault
- **THEN** no note content or modification time changes

#### Scenario: Unreadable notes are not repaired

- **WHEN** the scan finds a note it cannot parse
- **THEN** the note is left exactly as it was

#### Scenario: Opening runs trash retention

- **WHEN** a vault opens with a managed trash entry that is 30 or more days old
- **THEN** the entry may be deleted after opening validation and before the workspace is shown

#### Scenario: A failed retention still opens the vault

- **WHEN** trash retention cannot delete an expired entry
- **THEN** the vault still opens, the entry remains, and the failure is reported
