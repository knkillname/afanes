# Spec Delta

## ADDED Requirements

### Requirement: Steps are not notes

Steps SHALL NOT be notes. A step has no filename, no identity, and no entry in the name catalog. A reference MUST NOT resolve to a step, and a step is reachable only through its project page.

#### Scenario: Steps are absent from the catalog

- **WHEN** a vault is scanned
- **THEN** project steps do not appear as notes and do not join name uniqueness

#### Scenario: A link cannot target a step

- **WHEN** a reference name matches a step's text
- **THEN** the reference does not resolve to the step

#### Scenario: Renaming a project does not rename its steps

- **WHEN** a project is renamed
- **THEN** its steps keep their text and are still reached through the project

## MODIFIED Requirements

### Requirement: Names are unique per scheme

Within a scheme, one name SHALL identify exactly one note across the vault, using the same normalization as reference matching. Two notes with the same name in different directories SHALL be duplicates. The `note` and `project` schemes MAY reuse a name. Every reference shares the `note` scheme, regardless of its category.

#### Scenario: Duplicate in different directories

- **WHEN** two reference notes are named `Ada` in different directories
- **THEN** the vault is reported as having duplicate note names

#### Scenario: Cross-scheme reuse is allowed

- **WHEN** a reference note and a project note are both named `Ada`
- **THEN** `note:Ada` and `project:Ada` resolve to their respective notes

#### Scenario: Categorized reference shares the note scheme

- **WHEN** a reference with `category: person` and an uncategorized note are both named `Ada`
- **THEN** the vault is reported as having duplicate note names

#### Scenario: External duplicate is ambiguous

- **WHEN** a duplicate name is introduced outside the application
- **THEN** references to that name are reported as ambiguous and are not resolved to either note
