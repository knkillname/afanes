# Spec Delta

## REMOVED Requirements

### Requirement: Two schemes address the vault

**Reason**: The `log` scheme is introduced for dated log entries.

**Migration**: None before 1.0.0. Existing `note:` and `project:` destinations keep their current
meaning; no automatic conversion is provided.

## MODIFIED Requirements

### Requirement: Internal reference syntax

Afanes SHALL recognize an internal reference only as a Markdown link whose destination is
`scheme:name`, where the scheme is `project`, `note`, or `log`. The label is presentation only.
Angle-bracketed destinations are accepted, and are required when the name contains characters that a
bare Markdown destination cannot carry.

#### Scenario: Simple reference

- **WHEN** a note body contains `[Ada Lovelace](<note:Ada Lovelace>)`
- **THEN** the system reads it as a reference to the note named `Ada Lovelace`

#### Scenario: Bare destination

- **WHEN** a note body contains `[Ada](note:Ada)`
- **THEN** the system reads it as the same reference as `[Ada](<note:Ada>)`

#### Scenario: Label is not identity

- **WHEN** a note body contains `[my colleague](note:Ada)`
- **THEN** the reference targets `Ada` and the label is not part of the name

#### Scenario: Bracket syntax is not recognized

- **WHEN** a note body contains `[[Ada Lovelace]]`
- **THEN** the system does not treat it as a reference and does not resolve it

#### Scenario: A log reference is recognized

- **WHEN** a note body contains `[Tuesday](<log:2025-10-12>)`
- **THEN** the system reads it as a reference to the log entry dated `2025-10-12`

### Requirement: Type changes between note and project

A note SHALL resolve only under the scheme that covers its current type. When a note changes type
between `note` and `project`, references that no longer match SHALL become unresolved and be
reported; they MUST NOT be retargeted automatically. References within the `note` scheme SHALL
survive changes between `note` and any `reference`, including a category change. When a note changes
type to or from `log`, inbound references SHALL be rewritten to the new scheme and name as defined by
`note-identity`.

#### Scenario: Note becomes a reference

- **WHEN** a note referenced as `note:Prepare report` changes type from `note` to `reference`
- **THEN** `note:Prepare report` still resolves to it

#### Scenario: A reference gains a category

- **WHEN** a note referenced as `note:Ada` becomes a reference with `category: person`
- **THEN** `note:Ada` still resolves to it

#### Scenario: Note leaves the note scheme

- **WHEN** a note referenced as `note:Prepare report` changes type to `project`
- **THEN** the inbound reference is reported as unresolved and is not retargeted to
  `project:Prepare report`

#### Scenario: References are not retargeted

- **WHEN** a type change makes a reference unresolved
- **THEN** the application does not rewrite the reference to the new scheme

#### Scenario: A note becomes a log entry

- **WHEN** a note referenced as `note:A quiet Tuesday` changes to `log` and its date is `2025-10-12`
- **THEN** the referring destination becomes `log:2025-10-12`

#### Scenario: A log entry becomes a reference

- **WHEN** a log entry referenced as `log:2025-10-12` changes to `reference`
- **THEN** the referring destination becomes the new `note:` name

## ADDED Requirements

### Requirement: Three schemes address the vault

The `project` scheme SHALL resolve only to `project` notes. The `note` scheme SHALL resolve to `note`
notes and to `reference` notes in any category. The `log` scheme SHALL resolve only to `log` notes.
Scheme names SHALL be matched case-insensitively. Each scheme is a separate namespace: a name is
looked up only within its scheme.

#### Scenario: Project reference resolves a project

- **WHEN** `project:Release 1.0` names a project note
- **THEN** the reference resolves to that project

#### Scenario: Note reference resolves a reference in any category

- **WHEN** `note:Paris` names a reference with `category: place`
- **THEN** the reference resolves to that note

#### Scenario: Notes and references share one scheme

- **WHEN** a note declares `type: note` and a reference declares `type: reference`
- **THEN** both are addressable through the `note` scheme

#### Scenario: A log reference resolves only a log entry

- **WHEN** `log:2025-10-12` names a log entry
- **THEN** the reference resolves to that entry

#### Scenario: A note reference does not resolve a log entry

- **WHEN** `note:2025-10-12` is resolved and the only note with that name is a log entry
- **THEN** the reference is unresolved

#### Scenario: Namespaces are separate

- **WHEN** `note:Ada` is resolved and the only note named `Ada` is a project
- **THEN** the reference is unresolved and does not resolve to the project

#### Scenario: Unknown scheme is external

- **WHEN** a destination uses `https:`, `mailto:`, or any scheme outside the three internal schemes
- **THEN** the system treats it as an external link and never as an internal reference

### Requirement: Log references use the entry's ISO date

A `log:` reference SHALL use the same ISO precision as the entry: `YYYY`, `YYYY-MM`, or
`YYYY-MM-DD`. A reference SHALL NOT accept a human title, a localized date, or a timestamp.

#### Scenario: A day reference

- **WHEN** a note links to `log:2025-10-12`
- **THEN** it resolves to the day entry dated `2025-10-12`

#### Scenario: A month reference

- **WHEN** a note links to `log:2025-10`
- **THEN** it resolves to the month entry dated `2025-10`

#### Scenario: A year reference

- **WHEN** a note links to `log:2025`
- **THEN** it resolves to the year entry dated `2025`

#### Scenario: A title is not a log name

- **WHEN** a note links to `log:A quiet Tuesday`
- **THEN** the reference is unresolved
