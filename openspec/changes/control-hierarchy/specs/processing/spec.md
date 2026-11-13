# Spec Delta

## MODIFIED Requirements

### Requirement: Processing is explicit and confirmed

Processing SHALL operate only on a note under `inbox/` and SHALL require an explicit user action and confirmation before any write. It MUST NOT run during startup or scan.

#### Scenario: Preview precedes writes

- **WHEN** the user starts processing a capture
- **THEN** the application shows the outcome and destination and writes nothing until the user confirms

#### Scenario: Preview is insensitive without an outcome

- **WHEN** no processing outcome is selected
- **THEN** the Preview action is insensitive

#### Scenario: Preview waits for required input

- **WHEN** the selected outcome requires a project or a date that is missing or invalid
- **THEN** the Preview action is insensitive

#### Scenario: Cancel changes nothing

- **WHEN** the user cancels the processing preview
- **THEN** the note remains unchanged in `inbox/`

#### Scenario: Non-inbox note is rejected

- **WHEN** processing targets a note outside `inbox/`
- **THEN** the application reports an error and changes no file
