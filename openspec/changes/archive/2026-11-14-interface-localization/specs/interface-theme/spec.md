# Spec Delta

## MODIFIED Requirements

### Requirement: Interface copy follows the GNOME writing style

All user-facing copy SHALL follow the GNOME writing style: English headings and short control labels
use header capitalization; English field labels and prose use sentence capitalization; Spanish
follows Spanish capitalization conventions. Neutral tone, no final period, typographic apostrophes,
and one-character ellipses apply in every locale.

#### Scenario: A heading uses header capitalization

- **WHEN** an English view title, section heading, or destination title renders
- **THEN** it capitalizes the first and last word, every word of four or more letters, every verb and noun, and both parts of a hyphenated word

#### Scenario: A short control label uses header capitalization

- **WHEN** an English button, menu item, tooltip, or other short control label renders
- **THEN** it uses header capitalization rather than sentence capitalization

#### Scenario: A field label uses sentence capitalization

- **WHEN** a text field, drop-down, or other field label renders
- **THEN** it uses sentence capitalization and keeps its own wording short

#### Scenario: Prose uses sentence capitalization

- **WHEN** a hint, banner, dialog body, or other explanatory text renders
- **THEN** it uses sentence capitalization

#### Scenario: Spanish copy follows Spanish capitalization

- **WHEN** a Spanish heading, control label, field label, or prose line renders
- **THEN** it uses Spanish sentence-style capitalization and does not copy English header capitalization

#### Scenario: No copy ends with a period

- **WHEN** any user-facing copy renders in either locale
- **THEN** it does not end with a period, even when it is written as a complete sentence, while internal periods in multi-sentence text remain

#### Scenario: Tone stays neutral

- **WHEN** copy refers to the person using the application in either locale
- **THEN** it uses neutral phrasing and avoids the first- and second-person pronouns of that language

#### Scenario: Apostrophes are typographic

- **WHEN** copy contains a contraction or a possessive in either locale
- **THEN** it uses the typographic apostrophe U+2019 rather than the straight apostrophe

#### Scenario: Ellipses are one character

- **WHEN** copy ends with an ellipsis in either locale
- **THEN** it uses the single character U+2026 rather than three periods

#### Scenario: The command line follows the same style

- **WHEN** the command line prints help, a report, or an error in either locale
- **THEN** that copy follows the same capitalization, tone, period, apostrophe, and ellipsis rules

### Requirement: The copy gate enforces the writing style

An automated gate SHALL scan every English source module, Spanish `.po` catalog, and compiled `.mo`
catalog and fail on any writing-style violation. It SHALL require every English message to have a
context-matching `.po` entry with the same interpolation placeholders, declare the capitalization
style of every English copy constant, apply the capitalization rules of each language, and MUST NOT
carry a baseline of allowed violations.

#### Scenario: A straight apostrophe fails the gate

- **WHEN** a catalog string in any locale contains a straight apostrophe
- **THEN** the copy gate fails and names the string

#### Scenario: A three-dot ellipsis fails the gate

- **WHEN** a catalog string in any locale contains three periods instead of U+2026
- **THEN** the copy gate fails and names the string

#### Scenario: A trailing period fails the gate

- **WHEN** a catalog string in any locale ends with a period
- **THEN** the copy gate fails and names the string

#### Scenario: A first- or second-person pronoun fails the gate

- **WHEN** a catalog string contains a banned pronoun for its language as a whole word
- **THEN** the copy gate fails and names the string

#### Scenario: A misplaced ellipsis fails the gate

- **WHEN** a catalog string ends with an ellipsis but is not declared as an action that needs further input
- **THEN** the copy gate fails and names the string

#### Scenario: Unclassified copy fails the gate

- **WHEN** a copy constant has no declared capitalization style
- **THEN** the copy gate fails and names the constant

#### Scenario: A missing key fails the gate

- **WHEN** one locale lacks a key present in its counterpart
- **THEN** the copy gate fails and names the key

#### Scenario: An extra key fails the gate

- **WHEN** one locale declares a key its counterpart lacks
- **THEN** the copy gate fails and names the key

#### Scenario: A placeholder mismatch fails the gate

- **WHEN** the same key uses different interpolation placeholders across locales
- **THEN** the copy gate fails and names the key

#### Scenario: Spanish capitalization is accepted

- **WHEN** a Spanish heading uses Spanish sentence-style capitalization
- **THEN** the copy gate accepts it

#### Scenario: The gate has no baseline

- **WHEN** the copy gate runs
- **THEN** it requires zero violations and offers no ledger of allowed exceptions

#### Scenario: Both catalogs are scanned

- **WHEN** the copy gate runs
- **THEN** it checks every interface locale catalog and every command-line locale catalog

#### Scenario: The gettext sources and compiled catalogs are scanned

- **WHEN** the copy gate runs
- **THEN** it checks every English source module, Spanish `.po` catalog, and compiled `.mo` catalog

#### Scenario: A stale compiled catalog fails the gate

- **WHEN** a `.po` source changes without recompiling its `.mo` file
- **THEN** the copy gate fails and names the stale catalog
