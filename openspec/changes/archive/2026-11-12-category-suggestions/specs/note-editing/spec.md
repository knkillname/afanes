# Spec Delta

## ADDED Requirements

### Requirement: Category suggests existing labels while accepting new ones

Edit mode SHALL present the category as an editable combobox. Its suggestions SHALL be the distinct category labels already present on reference notes in the vault, sorted alphabetically and case-insensitively. Selecting a suggestion or typing a label that is not listed SHALL both be valid, and the existing category validation SHALL still apply.

#### Scenario: Existing labels are suggested

- **WHEN** the vault contains references under the `person` and `place` categories and a reference is edited
- **THEN** the category combobox offers `person` and `place`

#### Scenario: Typing filters the suggestions

- **WHEN** the user types part of a category name into the combobox
- **THEN** the suggestions are filtered to the labels that match, ignoring case

#### Scenario: A new label is accepted

- **WHEN** the user types a category that is not in the suggestions and confirms it
- **THEN** the reference receives that category and the note moves to the matching folder as before

#### Scenario: No existing labels yet

- **WHEN** the vault has no categorized reference notes and a reference is edited
- **THEN** the combobox offers no suggestions but still accepts a typed category
