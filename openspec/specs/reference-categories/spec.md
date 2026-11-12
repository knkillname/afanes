# reference-categories Specification

## Purpose

Defines how reference notes are grouped into categories such as people and places, how a category selects the reference scheme, and how category changes affect existing references.

## Requirements

### Requirement: Categories are free-form labels

A reference MAY declare any non-empty `category` label. The label is not a closed list and does not select a scheme. Labels SHALL be compared case-insensitively for grouping and folder reuse, and the written form SHALL be preserved. A label MUST be a single path segment.

#### Scenario: Arbitrary label is accepted

- **WHEN** a reference declares `category: place`
- **THEN** the note parses with the `place` label

#### Scenario: Uncategorized reference is valid

- **WHEN** a reference has no `category` key
- **THEN** the note parses

#### Scenario: Empty label is rejected

- **WHEN** a reference declares an empty `category`
- **THEN** parsing reports a validation error

#### Scenario: Path separator is rejected

- **WHEN** a category label contains a path separator
- **THEN** parsing reports a validation error

#### Scenario: Case variants group together

- **WHEN** two references declare `category: Place` and `category: place`
- **THEN** they group under one label and reuse one folder

### Requirement: Category changes move the file

Changing a reference's category SHALL change its default folder. The application SHALL preview the destination and move the file only after confirmation. Identity, name, and inbound references MUST NOT change.

#### Scenario: Adding a category moves the file

- **WHEN** an uncategorized reference gains `category: place`
- **THEN** the confirmation names `reference/place/` as the destination and the file moves only after confirmation

#### Scenario: Removing a category moves the file back

- **WHEN** a reference's category is removed
- **THEN** the confirmation names `reference/` as the destination

#### Scenario: Cancelling changes nothing

- **WHEN** the user cancels the category move
- **THEN** the category and the file location are unchanged

#### Scenario: References survive the move

- **WHEN** a categorized reference moves to its category folder
- **THEN** its inbound references still resolve

### Requirement: People are ordinary references

A person page SHALL be a `type: reference` note carrying a free-form category, conventionally `person`. `person` SHALL NOT be a standalone note type and SHALL NOT own a reference scheme.

#### Scenario: Person page has the reference shape

- **WHEN** a person page is created
- **THEN** it has `type: reference` and a category label

#### Scenario: Person is not a note type

- **WHEN** a note declares `type: person`
- **THEN** parsing reports a validation error

#### Scenario: Person is not a scheme

- **WHEN** a body contains a `person:Ada` destination
- **THEN** parsing reports a validation error

#### Scenario: People are linked as notes

- **WHEN** a body links to a person page named `Ada`
- **THEN** the destination is `note:Ada`

### Requirement: Each label maps to a reference folder

Each category SHALL map to a default folder under `reference/` named from the label through the cross-platform name policy. An uncategorized reference SHALL default to `reference/`. The folder SHALL be a destination hint, not part of identity.

#### Scenario: A label maps to a folder

- **WHEN** a reference has `category: place`
- **THEN** its default destination is `reference/place/`

#### Scenario: Uncategorized reference uses the reference root

- **WHEN** a reference has no category
- **THEN** its default destination is `reference/`

#### Scenario: Existing case variant is reused

- **WHEN** `reference/Place/` already exists
- **THEN** the application uses that folder and does not create `reference/place/`

#### Scenario: Folder is not identity

- **WHEN** a categorized reference lives outside its default folder
- **THEN** its name remains its identity and its references still resolve

### Requirement: Reference names are unique in the note scheme

Every reference SHALL participate in `note` scheme name uniqueness, regardless of category. A categorized reference and a note MUST NOT share a name. A reference and a project MAY share a name.

#### Scenario: Reference and project share a name

- **WHEN** a reference and a project are both named `Ada`
- **THEN** both are accepted because their schemes differ

#### Scenario: Duplicate references are ambiguous

- **WHEN** two references are named `Ada`
- **THEN** `note:Ada` is reported as ambiguous

#### Scenario: Case variants are duplicates

- **WHEN** two references are named `Ada` and `ada`
- **THEN** `note:Ada` is reported as ambiguous

#### Scenario: A categorized and an uncategorized reference collide

- **WHEN** a reference with `category: person` and an uncategorized reference are both named `Ada`
- **THEN** the vault reports duplicate note names
