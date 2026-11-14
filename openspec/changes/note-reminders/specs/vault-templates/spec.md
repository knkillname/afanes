# Spec Delta

## MODIFIED Requirements

### Requirement: A created vault contains the guide, template cards, and chosen template

Vault creation SHALL write `afanes.yaml` with the current schema, the guide note, the eight template
cards under `templates/`, and, when a starter template is chosen, the notes that template declares.
Creation MUST NOT write any other file, and applying a starter template MUST NOT write outside the
new vault.

#### Scenario: Blank vault holds the guide and cards

- **WHEN** a vault is created without a starter template
- **THEN** it contains the guide note, the settings file, and the eight template cards, and no other
  note

#### Scenario: Templated vault holds the guide, cards, and notes

- **WHEN** a vault is created from a starter template
- **THEN** it contains the guide, the settings file, the eight cards, and exactly the notes the
  starter template declares

#### Scenario: Created vault is versioned

- **WHEN** a vault is created
- **THEN** `afanes.yaml` exists at its root with `schema_version: 2`

#### Scenario: Cards land in templates

- **WHEN** a vault is created
- **THEN** the eight cards exist under `templates/` and no card appears as a note

#### Scenario: Opening does not restore cards

- **WHEN** a card is deleted and the vault is reopened
- **THEN** the card is not recreated

#### Scenario: The log card is written

- **WHEN** a vault is created
- **THEN** `templates/daily.md` exists and declares `type: log`

## ADDED Requirements

### Requirement: Starter content contains no reminders

Bundled starter content MUST NOT declare a `reminder` key. Applying any template SHALL leave the
Review count at zero, including reminders, and MUST NOT create a due reminder.

#### Scenario: A template with a reminder is refused

- **WHEN** a bundled note declares a `reminder`
- **THEN** the template is refused and creation writes nothing

#### Scenario: A created vault has no reminders

- **WHEN** a vault is created from any bundled template
- **THEN** no written note declares a `reminder`

#### Scenario: The guide and cards carry no reminder

- **WHEN** the guide or a template card is written
- **THEN** it declares no `reminder`

#### Scenario: The new vault reports zero pending reminders

- **WHEN** a vault is created from any bundled template
- **THEN** no reminder is due
