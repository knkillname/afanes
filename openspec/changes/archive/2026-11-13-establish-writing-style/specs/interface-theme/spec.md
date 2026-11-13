# Spec Delta

## ADDED Requirements

### Requirement: Interface copy follows the GNOME writing style

All user-facing copy SHALL follow the GNOME writing style: header capitalization
for headings and short control labels, sentence capitalization for field labels
and prose, neutral tone, no final period, typographic apostrophes, and
one-character ellipses.

#### Scenario: A heading uses header capitalization

- **WHEN** a view title, section heading, or destination title renders
- **THEN** it capitalizes the first and last word, every word of four or more letters, every verb and noun, and both parts of a hyphenated word

#### Scenario: A short control label uses header capitalization

- **WHEN** a button, menu item, tooltip, or other short control label renders
- **THEN** it uses header capitalization rather than sentence capitalization

#### Scenario: A field label uses sentence capitalization

- **WHEN** a text field, drop-down, or other field label renders
- **THEN** it uses sentence capitalization and keeps its own wording short

#### Scenario: Prose uses sentence capitalization

- **WHEN** a hint, banner, dialog body, or other explanatory text renders
- **THEN** it uses sentence capitalization

#### Scenario: No copy ends with a period

- **WHEN** any user-facing copy renders
- **THEN** it does not end with a period, even when it is written as a complete sentence, while internal periods in multi-sentence text remain

#### Scenario: Tone stays neutral

- **WHEN** copy refers to the person using the application
- **THEN** it uses neutral phrasing and does not use the first- or second-person pronouns I, me, my, we, us, our, you, your, or yours

#### Scenario: Apostrophes are typographic

- **WHEN** copy contains a contraction or a possessive
- **THEN** it uses the typographic apostrophe U+2019 rather than the straight apostrophe

#### Scenario: Ellipses are one character

- **WHEN** copy ends with an ellipsis
- **THEN** it uses the single character U+2026 rather than three periods

#### Scenario: The command line follows the same style

- **WHEN** the command line prints help, a report, or an error
- **THEN** that copy follows the same capitalization, tone, period, apostrophe, and ellipsis rules

### Requirement: An ellipsis marks an action that needs further input

A control label SHALL end with an ellipsis only when activating it opens a
dialog, form, or confirmation before the action completes. A control that
carries out its action immediately MUST NOT end with an ellipsis.

#### Scenario: An action that opens a form carries an ellipsis

- **WHEN** a control opens a dialog or form that collects further input
- **THEN** its label ends with an ellipsis

#### Scenario: An action that opens a confirmation carries an ellipsis

- **WHEN** a control opens a confirmation before it can complete
- **THEN** its label ends with an ellipsis

#### Scenario: An immediate action carries no ellipsis

- **WHEN** a control carries out its action without further input or confirmation
- **THEN** its label does not end with an ellipsis

#### Scenario: The affirmative control inside the dialog carries no ellipsis

- **WHEN** the dialog opened by an ellipsis action shows its affirmative control
- **THEN** that control does not end with an ellipsis because it completes the action immediately

#### Scenario: A navigation destination carries no ellipsis

- **WHEN** a destination opens a view rather than collecting input
- **THEN** its label does not end with an ellipsis

### Requirement: The copy gate enforces the writing style

An automated gate SHALL scan the interface and command-line copy catalogs and
fail on any writing-style violation. The gate SHALL declare the capitalization
style of every copy constant and MUST NOT carry a baseline of allowed
violations.

#### Scenario: A straight apostrophe fails the gate

- **WHEN** a catalog string contains a straight apostrophe
- **THEN** the copy gate fails and names the string

#### Scenario: A three-dot ellipsis fails the gate

- **WHEN** a catalog string contains three periods instead of U+2026
- **THEN** the copy gate fails and names the string

#### Scenario: A trailing period fails the gate

- **WHEN** a catalog string ends with a period
- **THEN** the copy gate fails and names the string

#### Scenario: A first- or second-person pronoun fails the gate

- **WHEN** a catalog string contains a banned pronoun as a whole word
- **THEN** the copy gate fails and names the string

#### Scenario: A misplaced ellipsis fails the gate

- **WHEN** a catalog string ends with an ellipsis but is not declared as an action that needs further input
- **THEN** the copy gate fails and names the string

#### Scenario: Unclassified copy fails the gate

- **WHEN** a copy constant has no declared capitalization style
- **THEN** the copy gate fails and names the constant

#### Scenario: The gate has no baseline

- **WHEN** the copy gate runs
- **THEN** it requires zero violations and offers no ledger of allowed exceptions

#### Scenario: Both catalogs are scanned

- **WHEN** the copy gate runs
- **THEN** it checks the interface catalog and the command-line catalog
