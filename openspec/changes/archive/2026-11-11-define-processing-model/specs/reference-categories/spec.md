# Spec Delta

## Purpose

Defines how reference notes are grouped into categories such as people and places, how a category selects the reference scheme, and how category changes affect existing references.

## ADDED Requirements

### Requirement: Reference categories are optional

The application SHALL accept a reference note with or without a `category` key. The initial category is `person`. Future categories are added by explicit specification changes. An uncategorized reference SHALL remain valid.

#### Scenario: Person category is valid

- **WHEN** a reference note declares `category: person`
- **THEN** the note parses successfully

#### Scenario: Uncategorized reference is valid

- **WHEN** a reference note has no `category` key
- **THEN** the note parses successfully

#### Scenario: Unknown category is rejected

- **WHEN** a reference note declares an unknown category
- **THEN** parsing reports a validation error

### Requirement: People are reference notes

A person page SHALL be a `type: reference` note with `category: person`. `person` SHALL NOT be a standalone note type. The `people` frontmatter key SHALL continue to hold `person:` references.

#### Scenario: Person page has the reference shape

- **WHEN** a person page is created
- **THEN** it has `type: reference` and `category: person`

#### Scenario: Person reference resolves the page

- **WHEN** `person:Ada` is resolved and a reference note named `Ada` has `category: person`
- **THEN** the reference resolves to that note

#### Scenario: Person is not a note type

- **WHEN** a note declares `type: person`
- **THEN** parsing reports a validation error

#### Scenario: People metadata is unchanged

- **WHEN** a note declares `people: ["person:Ada"]`
- **THEN** the value remains a valid person reference

### Requirement: Category selects the scheme

A categorized reference SHALL resolve only under its category's scheme. An uncategorized reference SHALL resolve under the `note` scheme. A note SHALL belong to exactly one scheme.

#### Scenario: Person category selects the person scheme

- **WHEN** a reference note has `category: person`
- **THEN** it is addressable as `person:Name` and not as `note:Name`

#### Scenario: Uncategorized reference selects the note scheme

- **WHEN** a reference note has no category
- **THEN** it is addressable as `note:Name`

#### Scenario: Categorized reference is not a note target

- **WHEN** `note:Ada` is resolved and the only note named `Ada` has `category: person`
- **THEN** the reference is unresolved

#### Scenario: No note belongs to two schemes

- **WHEN** a reference note has `category: person`
- **THEN** it is not also a candidate under the `note` scheme

### Requirement: Category values are validated

The `category` value SHALL be a known category and SHALL be valid only on `type: reference`. Unknown values, empty values, and placement on another type SHALL produce a validation error. Category values SHALL be matched case-insensitively and written in canonical lowercase.

#### Scenario: Empty category is rejected

- **WHEN** a reference declares an empty `category` value
- **THEN** parsing reports a validation error

#### Scenario: Category on an action is rejected

- **WHEN** an action declares `category: person`
- **THEN** parsing reports a validation error

#### Scenario: Category case is normalized

- **WHEN** a reference declares `category: Person`
- **THEN** it parses as the `person` category and serializes as `person`

#### Scenario: Unknown keys are preserved

- **WHEN** a reference declares an unknown key other than `category`
- **THEN** the key and value are preserved

### Requirement: Category changes affect resolution

Changing a reference's category SHALL change its scheme. References under the old scheme SHALL become unresolved and SHALL be reported; they MUST NOT be retargeted. Moving a file between category folders without changing the category MUST NOT change resolution.

#### Scenario: Category is removed

- **WHEN** a reference's `category` key is removed
- **THEN** `person:` references become unresolved and `note:` references resolve to it

#### Scenario: Folder move keeps the scheme

- **WHEN** a person reference moves from `reference/people/` to another active folder without changing its category
- **THEN** `person:` references still resolve

#### Scenario: No automatic retarget

- **WHEN** a category change makes a reference unresolved
- **THEN** the application does not rewrite the reference to the new scheme

### Requirement: Category folders are default destinations

The application SHALL map each category to a default folder under `reference/`. The initial mapping is `person` to `people`. The folder SHALL be a destination hint, not part of identity.

#### Scenario: Person category maps to people

- **WHEN** a person page is created by the application
- **THEN** it is filed under `reference/people/`

#### Scenario: Folder is not identity

- **WHEN** a person page lives outside `reference/people/`
- **THEN** its name remains its identity and `person:` references still resolve

### Requirement: The person scheme is a category filter

The `person` scheme SHALL resolve only to reference notes with `category: person`. It MUST NOT resolve to projects or uncategorized references.

#### Scenario: Person page resolves

- **WHEN** a reference note named `Ada` has `category: person`
- **THEN** `person:Ada` resolves to it

#### Scenario: Project with the same name does not resolve

- **WHEN** `person:Ada` is resolved and the only note named `Ada` is a project
- **THEN** the reference is unresolved

#### Scenario: Uncategorized reference does not resolve

- **WHEN** `person:Ada` is resolved and the only note named `Ada` is an uncategorized reference
- **THEN** the reference is unresolved

### Requirement: Per-scheme uniqueness includes categories

Category notes SHALL participate in per-scheme name uniqueness. Notes in different schemes MAY share a name; two notes in the same scheme MAY NOT.

#### Scenario: Person and uncategorized reference share a name

- **WHEN** a person note and an uncategorized reference are both named `Ada`
- **THEN** both are accepted because their schemes differ

#### Scenario: Duplicate person names are ambiguous

- **WHEN** two person notes are named `Ada`
- **THEN** `person:Ada` is reported as ambiguous

#### Scenario: Case variants are duplicates

- **WHEN** two person notes are named `Ada` and `ada`
- **THEN** `person:Ada` is reported as ambiguous
