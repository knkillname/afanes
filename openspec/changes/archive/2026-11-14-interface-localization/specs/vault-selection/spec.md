# Spec Delta

## ADDED Requirements

### Requirement: The interface language survives vault changes

The application SHALL store the interface language in app-owned preferences outside the vault. The
preference SHALL survive changing or closing the vault, and a missing value SHALL mean the system
locale. A corrupt preferences file SHALL be reported without being overwritten.

#### Scenario: A saved language is remembered

- **WHEN** the user chooses Spanish
- **THEN** the preference is written outside the vault and used on the next launch

#### Scenario: Changing the vault keeps the language

- **WHEN** the user opens another vault
- **THEN** the saved language preference remains in effect

#### Scenario: Closing the vault keeps the language

- **WHEN** the user closes the vault and returns to the welcome state
- **THEN** the saved language preference remains available on the next launch

#### Scenario: A missing preference means the system locale

- **WHEN** no language preference has ever been saved
- **THEN** the application resolves the system locale

#### Scenario: Corrupt preferences are reported and preserved

- **WHEN** the preferences file cannot be read or parsed
- **THEN** the application reports the problem, uses the system locale, and does not overwrite the file

#### Scenario: Preferences leave the vault untouched

- **WHEN** the user chooses a language
- **THEN** no vault note, folder, or settings file is created, changed, or removed
