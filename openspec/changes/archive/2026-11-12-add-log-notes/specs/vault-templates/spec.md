# Spec Delta

## MODIFIED Requirements

### Requirement: A guide note is written into every created vault

Every created vault SHALL contain exactly one guide note at `reference/Getting started.md`
explaining the note model, including the `log` type. The guide SHALL declare `type: reference` with
no category, SHALL NOT be selectable as a template, and SHALL be an ordinary note afterwards.

#### Scenario: Blank creation writes the guide

- **WHEN** a vault is created without a template
- **THEN** `reference/Getting started.md` exists and the vault contains no other note

#### Scenario: Templated creation also writes the guide

- **WHEN** a vault is created from a template
- **THEN** the guide note exists alongside the template's notes

#### Scenario: The guide is a reference note

- **WHEN** the guide note is parsed
- **THEN** it has `type: reference`, no category, no status, and appears in the references section

#### Scenario: The guide name is reserved

- **WHEN** a bundled template declares a note whose stem is `Getting started`
- **THEN** the template is refused as invalid

#### Scenario: The guide can be removed

- **WHEN** the user trashes the guide note
- **THEN** the vault continues to work and nothing recreates the note

#### Scenario: The guide explains the log type

- **WHEN** the guide note is read
- **THEN** it describes the log note type, its editable date, and the Log section

### Requirement: A created vault contains the guide, template cards, and chosen template

Vault creation SHALL write the guide note, the eight template cards under `templates/`, and, when a
starter template is chosen, the notes that template declares. Creation MUST NOT write any other file,
and applying a starter template MUST NOT write outside the new vault.

#### Scenario: Blank vault holds the guide and cards

- **WHEN** a vault is created without a starter template
- **THEN** it contains the guide note and the eight template cards, and no other note

#### Scenario: Templated vault holds the guide, cards, and notes

- **WHEN** a vault is created from a starter template
- **THEN** it contains the guide, the eight cards, and exactly the notes the starter template declares

#### Scenario: Cards land in templates

- **WHEN** a vault is created
- **THEN** the eight cards exist under `templates/` and no card appears as a note

#### Scenario: Opening does not restore cards

- **WHEN** a card is deleted and the vault is reopened
- **THEN** the card is not recreated

#### Scenario: The log card is written

- **WHEN** a vault is created
- **THEN** `templates/daily.md` exists and declares `type: log`
