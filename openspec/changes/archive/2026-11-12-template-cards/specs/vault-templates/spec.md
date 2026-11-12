# Spec Delta

## ADDED Requirements

### Requirement: A created vault contains the guide, template cards, and chosen template

Vault creation SHALL write the guide note, the seven reference template cards under `templates/`, and, when a starter template is chosen, the notes that template declares. Creation MUST NOT write any other file, and applying a starter template MUST NOT write outside the new vault.

#### Scenario: Blank vault holds the guide and cards

- **WHEN** a vault is created without a starter template
- **THEN** it contains the guide note and the seven template cards, and no other note

#### Scenario: Templated vault holds the guide, cards, and notes

- **WHEN** a vault is created from a starter template
- **THEN** it contains the guide, the seven cards, and exactly the notes the starter template declares

#### Scenario: Cards land in templates

- **WHEN** a vault is created
- **THEN** the seven cards exist under `templates/` and no card appears as a note

#### Scenario: Opening does not restore cards

- **WHEN** a card is deleted and the vault is reopened
- **THEN** the card is not recreated
