# note-references Specification

## Purpose

Defines how Afanes expresses, extracts, and resolves references between notes using standard Markdown link syntax with typed schemes, so that references remain readable and stable outside the application.

## Requirements

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

### Requirement: Reference extraction reads body text

References SHALL be extracted from Markdown text content. They SHALL NOT be extracted from fenced code, indented code, inline code, HTML comments, image destinations, or step metadata.

#### Scenario: Fenced code is excluded

- **WHEN** a reference appears inside a fenced code block
- **THEN** the system does not extract it

#### Scenario: Inline code is excluded

- **WHEN** a reference appears inside an inline code span
- **THEN** the system does not extract it

#### Scenario: Images are not references

- **WHEN** a note body contains `![diagram](attachments/diagram.png)`
- **THEN** the destination is not extracted as a note reference

#### Scenario: Step metadata is not a body reference

- **WHEN** a step declares `owners: [Ada]` in its metadata comment
- **THEN** no body reference is extracted from the comment and the owner resolves as a step owner

### Requirement: Name matching

Names SHALL be compared after NFC normalization, case folding, trimming, internal whitespace collapse, and removal of one optional trailing `.md`. Matching SHALL be exact after normalization.

#### Scenario: Case-insensitive match

- **WHEN** `person:ada lovelace` is resolved and the note is named `Ada Lovelace`
- **THEN** the reference resolves

#### Scenario: Unicode forms match

- **WHEN** a reference name and a filename differ only in composed versus decomposed Unicode form
- **THEN** the reference resolves

#### Scenario: Internal whitespace is normalized

- **WHEN** a reference name contains a run of spaces and the filename contains a single space
- **THEN** the reference resolves

#### Scenario: Extension is ignored

- **WHEN** a reference name ends in `.md`
- **THEN** the extension is removed before matching

### Requirement: Resolution outcomes

Resolution SHALL produce exactly one outcome: resolved, unresolved, or ambiguous. Ambiguity SHALL list every candidate and MUST NOT select one. Unresolved references SHALL remain valid and SHALL resolve when a matching note appears. Resolution SHALL use the name catalog and MUST NOT read the filesystem directly.

#### Scenario: Unique match resolves

- **WHEN** exactly one note matches the scheme and name
- **THEN** the reference is bound to that note

#### Scenario: Missing target is retained

- **WHEN** no note matches the scheme and name
- **THEN** the reference is reported as unresolved and is preserved in the note

#### Scenario: Missing target heals

- **WHEN** a note later appears with the missing scheme and name
- **THEN** the previously unresolved reference resolves on the next scan

#### Scenario: Duplicate names are ambiguous

- **WHEN** two notes in the same scheme share the name
- **THEN** the reference is reported as ambiguous with both candidates and is not resolved to either

#### Scenario: Resolution never opens a path

- **WHEN** a reference name contains path separators or traversal segments
- **THEN** the system treats it as a name that matches nothing and does not open any file

### Requirement: Attachment and external distinction

A destination without a scheme SHALL be treated as a relative file or attachment path and MUST NOT resolve as a note reference. Only the three internal schemes SHALL resolve as internal references. Active schemes such as `javascript:` SHALL be classified as unsafe and MUST NOT resolve as an internal reference or become a navigable internal target.

#### Scenario: Relative image is an attachment

- **WHEN** a note body contains `![scan](attachments/scan.png)`
- **THEN** the destination is treated as an attachment and not as a note reference

#### Scenario: External URL is not resolved

- **WHEN** a note body contains `[docs](https://example.com)`
- **THEN** the destination is classified as external and is not resolved as a note

#### Scenario: Active scheme is blocked

- **WHEN** a note body contains a `javascript:` destination
- **THEN** the system classifies it as unsafe and does not resolve it as an internal reference

### Requirement: Type changes between note and project

A note SHALL resolve only under the scheme that covers its current type. When a note changes type
between `note` and `project`, references that no longer match SHALL become unresolved and be
reported; they MUST NOT be retargeted automatically. References within the `note` scheme SHALL
survive changes between `note` and any `reference`, including a category change. When a note changes
type to or from `log`, inbound references SHALL be rewritten to the new scheme and name per
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
