# Spec Delta

## MODIFIED Requirements

### Requirement: Scheme vocabulary and target types

The `person` scheme SHALL resolve only to reference notes with category `person`; `project` only to `project`; and `note` to `note`, `action`, or an uncategorized `reference`. Scheme names SHALL be matched case-insensitively. Each scheme is a separate namespace: a name is looked up only within its scheme.

#### Scenario: Person reference resolves a person

- **WHEN** `person:Ada` names a reference note with category `person`
- **THEN** the reference resolves to that note

#### Scenario: Document family shares one scheme

- **WHEN** an action note is referenced as `[Call dentist](<note:Call dentist>)`
- **THEN** the reference resolves to the action note

#### Scenario: Uncategorized reference is a document

- **WHEN** an uncategorized reference is referenced as `[Reading](<note:Reading>)`
- **THEN** the reference resolves to the reference note

#### Scenario: Categorized reference is outside the note scheme

- **WHEN** `note:Ada` is resolved and the only note named `Ada` has category `person`
- **THEN** the reference is unresolved

#### Scenario: Namespaces are separate

- **WHEN** `person:Ada` is resolved and the only note named `Ada` is a project
- **THEN** the reference is unresolved and does not resolve to the project

#### Scenario: Unknown scheme is external

- **WHEN** a destination uses `https:`, `mailto:`, or any scheme outside the three internal schemes
- **THEN** the system treats it as an external link and never as an internal reference

### Requirement: Type changes

A note SHALL resolve only under a scheme that covers its current type and category. When a note changes type or category, references that no longer match SHALL become unresolved and be reported; they MUST NOT be retargeted automatically. References within the document family SHALL survive changes between `note`, `action`, and an uncategorized `reference`.

#### Scenario: Note becomes an action

- **WHEN** a note referenced as `note:Prepare report` changes type from `note` to `action`
- **THEN** `note:Prepare report` still resolves to it

#### Scenario: Note becomes an uncategorized reference

- **WHEN** a note referenced as `note:Prepare report` changes type from `note` to an uncategorized `reference`
- **THEN** `note:Prepare report` still resolves to it

#### Scenario: Note gains a category

- **WHEN** a note referenced as `note:Ada` changes to a reference with category `person`
- **THEN** the inbound `note:Ada` reference is reported as unresolved and is not retargeted

#### Scenario: Note leaves the document family

- **WHEN** a note referenced as `note:Prepare report` changes type to `project`
- **THEN** the inbound reference is reported as unresolved and is not retargeted to `project:Prepare report`
