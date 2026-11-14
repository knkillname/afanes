# Spec Delta

## ADDED Requirements

### Requirement: The active locale is resolved before interface copy loads

Before any interface copy loads, Afanes SHALL resolve the active locale from the saved override or
the system locale. Resolution SHALL cover the desktop and browser presentations, MUST work without a
vault, and MUST NOT contact the network.

#### Scenario: Desktop startup resolves the locale first

- **WHEN** the desktop presentation starts under a Spanish preference
- **THEN** the first rendered interface is Spanish

#### Scenario: Browser startup uses the process locale

- **WHEN** the browser presentation starts
- **THEN** it resolves the locale from the process environment and the saved preference

#### Scenario: No vault is required

- **WHEN** the application starts at the welcome state
- **THEN** the locale is already resolved and the welcome copy uses it

#### Scenario: Corrupt settings fall back to the system locale

- **WHEN** the settings file cannot be read
- **THEN** the application resolves the system locale and reports the settings problem in that locale

#### Scenario: Resolution stays offline

- **WHEN** the locale is resolved at startup
- **THEN** no network request is made and no translation package is downloaded
