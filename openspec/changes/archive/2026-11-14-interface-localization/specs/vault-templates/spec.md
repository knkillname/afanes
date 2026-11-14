# Spec Delta

## MODIFIED Requirements

### Requirement: The catalog is fixed and ordered

Afanes SHALL offer a fixed, ordered catalog of bundled templates: Personal, Work, and Study, with
the identifiers `personal`, `work`, and `study`. Each entry SHALL carry a short label and a
one-sentence description in the active locale, with English as the fallback. The catalog MUST be
readable without a vault being open.

#### Scenario: Catalog lists every template

- **WHEN** the catalog is requested
- **THEN** it reports personal, work, and study in that order

#### Scenario: Identifiers are stable

- **WHEN** a template is selected by identifier
- **THEN** the identifier is the kebab-case catalog entry, independent of its label

#### Scenario: Catalog needs no vault

- **WHEN** no vault is open
- **THEN** the catalog and its descriptions are still available

#### Scenario: Labels follow the active locale

- **WHEN** the catalog is requested under Spanish
- **THEN** each label and description is Spanish

#### Scenario: A missing Spanish label falls back

- **WHEN** the Spanish catalog has no label or description for an entry
- **THEN** that entry renders its English label and description

### Requirement: A guide note is written into every created vault

Every created vault SHALL contain exactly one guide note at the guide path of the locale tree that
supplied it, explaining the note model, including the `log` type. The English path is
`reference/Getting started.md`; the Spanish path is `reference/Primeros pasos.md`. The guide SHALL
declare `type: reference` with no category, SHALL NOT be selectable as a template, and SHALL be an
ordinary note afterwards.

#### Scenario: Blank creation writes the guide

- **WHEN** a vault is created without a template
- **THEN** the active locale's guide path exists and the vault contains no other note

#### Scenario: Templated creation also writes the guide

- **WHEN** a vault is created from a template
- **THEN** the guide note exists alongside the template's notes

#### Scenario: Spanish creation writes the Spanish guide

- **WHEN** a vault is created under Spanish
- **THEN** `reference/Primeros pasos.md` exists and its content is Spanish

#### Scenario: A missing Spanish guide falls back to English

- **WHEN** the Spanish guide tree is missing
- **THEN** `reference/Getting started.md` is written with English content and creation succeeds

#### Scenario: The guide is a reference note

- **WHEN** the guide note is parsed
- **THEN** it has `type: reference`, no category, no status, and appears in the references section

#### Scenario: The guide name is reserved

- **WHEN** a bundled template declares a note whose stem matches any supported guide stem
- **THEN** the template is refused as invalid

#### Scenario: The guide can be removed

- **WHEN** the user trashes the guide note
- **THEN** the vault continues to work and nothing recreates the note

#### Scenario: The guide explains the log type

- **WHEN** the guide note is read
- **THEN** it describes the log note type, its editable date, and the Log section
