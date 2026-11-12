# Spec Delta

## MODIFIED Requirements

### Requirement: Bundled templates are partial vaults

Afanes SHALL ship starter content as bundled Markdown trees. A template SHALL consist only of notes
and the folders that hold them, and applying it SHALL reproduce the same relative paths inside a
newly created vault. Applied notes SHALL be ordinary notes with no marker, provenance key, or
special status.

#### Scenario: Notes reproduce their relative paths

- **WHEN** a template containing `projects/Home projects.md` is applied
- **THEN** the created vault contains `projects/Home projects.md`

#### Scenario: Applied notes are ordinary notes

- **WHEN** a note from a template is opened after creation
- **THEN** it is renamed, edited, and trashed by the same actions as any other note

#### Scenario: No provenance is recorded

- **WHEN** a templated vault is created
- **THEN** no template marker file is written, no settings entry records which notes came from a
  template, and no note carries a key identifying its origin

#### Scenario: The schema file is not template provenance

- **WHEN** a templated vault is created
- **THEN** `afanes.yaml` records only the vault schema version and names no template or note

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
- **THEN** `afanes.yaml` exists at its root with `schema_version: 1`

#### Scenario: Cards land in templates

- **WHEN** a vault is created
- **THEN** the eight cards exist under `templates/` and no card appears as a note

#### Scenario: Opening does not restore cards

- **WHEN** a card is deleted and the vault is reopened
- **THEN** the card is not recreated

#### Scenario: The log card is written

- **WHEN** a vault is created
- **THEN** `templates/daily.md` exists and declares `type: log`
