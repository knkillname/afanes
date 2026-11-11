# note-references Specification

## Purpose

Defines how Afanes expresses, extracts, and resolves references between notes using standard Markdown link syntax with typed schemes, so that references remain readable and stable outside the application.

## Requirements

### Requirement: Internal reference syntax

Afanes SHALL recognize an internal reference only as a Markdown link whose destination is `scheme:name`, where the scheme is `person`, `project`, or `note`. The label is presentation only. Angle-bracketed destinations are accepted, and are required when the name contains characters that a bare Markdown destination cannot carry.

#### Scenario: Simple reference

- **WHEN** a note body contains `[Ada Lovelace](<person:Ada Lovelace>)`
- **THEN** the system reads it as a reference to the person named `Ada Lovelace`

#### Scenario: Bare destination

- **WHEN** a note body contains `[Ada](person:Ada)`
- **THEN** the system reads it as the same reference as `[Ada](<person:Ada>)`

#### Scenario: Label is not identity

- **WHEN** a note body contains `[my colleague](person:Ada)`
- **THEN** the reference targets `Ada` and the label is not part of the name

#### Scenario: Bracket syntax is not recognized

- **WHEN** a note body contains `[[Ada Lovelace]]`
- **THEN** the system does not treat it as a reference and does not resolve it

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

### Requirement: Reference extraction scope

References SHALL be extracted from Markdown text content and from the `people` and `project` frontmatter values. They SHALL NOT be extracted from fenced code, indented code, inline code, HTML comments, or image destinations.

#### Scenario: Fenced code is excluded

- **WHEN** a reference appears inside a fenced code block
- **THEN** the system does not extract it

#### Scenario: Inline code is excluded

- **WHEN** a reference appears inside an inline code span
- **THEN** the system does not extract it

#### Scenario: Frontmatter values are references

- **WHEN** frontmatter contains `people: ["person:Ada"]`
- **THEN** the system extracts a person reference from the note's metadata

#### Scenario: Images are not references

- **WHEN** a note body contains `![diagram](attachments/diagram.png)`
- **THEN** the destination is not extracted as a note reference

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

### Requirement: Frontmatter reference values

The `people` key SHALL hold zero or more `person:name` references. The `project` key SHALL hold at most one `project:name` reference. A value that is not a scheme reference SHALL produce a validation error and MUST NOT be coerced or silently reinterpreted.

#### Scenario: Valid people list

- **WHEN** a note declares `people: ["person:Ada", "person:Grace"]`
- **THEN** both person references are extracted

#### Scenario: Bare name is rejected

- **WHEN** a note declares `people: ["Ada"]`
- **THEN** the value produces a validation error rather than being resolved as a person

#### Scenario: Project value is validated

- **WHEN** a note declares a `project` value that is not a `project:name` reference
- **THEN** the value produces a validation error

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
