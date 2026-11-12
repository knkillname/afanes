# Spec Delta

## REMOVED Requirements

### Requirement: A created vault contains exactly the guide and the chosen template

**Reason**: Vault creation now also seeds the seven reference template cards under `templates/`.

**Migration**: Existing vaults are unchanged. New vaults contain the guide note, the seven template cards, and any notes declared by the chosen starter template.

## ADDED Requirements

### Requirement: The templates folder holds non-note content

The vault root SHALL reserve `templates/` for reference template cards. Files under it MUST NOT be scanned as notes, appear in the browser, participate in name uniqueness, or resolve as references. The folder name SHALL be matched case-insensitively. Opening or scanning a vault MUST NOT create the folder.

#### Scenario: A card is not scanned

- **WHEN** `templates/person.md` exists
- **THEN** it does not appear in the scanned note set

#### Scenario: A card name can belong to a note

- **WHEN** `templates/Ada.md` exists and a note named `Ada` is created
- **THEN** the note is accepted and the two do not collide

#### Scenario: A reference to a card name is unresolved

- **WHEN** a body links to `note:person` and only `templates/person.md` exists
- **THEN** the reference is unresolved

#### Scenario: Case variants are excluded

- **WHEN** the vault contains `Templates/person.md`
- **THEN** it is excluded from the note set

#### Scenario: Opening creates nothing

- **WHEN** a vault without `templates/` is opened or scanned
- **THEN** the folder is not created

#### Scenario: The browser does not list cards

- **WHEN** the browser groups references
- **THEN** no card appears in any group
