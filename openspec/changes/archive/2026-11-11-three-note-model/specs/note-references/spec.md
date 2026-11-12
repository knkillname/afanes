# Spec Delta

## ADDED Requirements

### Requirement: Two schemes address the vault

The `project` scheme SHALL resolve only to `project` notes. The `note` scheme SHALL resolve to `note` notes and to `reference` notes in any category. Scheme names SHALL be matched case-insensitively. Each scheme is a separate namespace: a name is looked up only within its scheme.

#### Scenario: Project reference resolves a project

- **WHEN** `project:Release 1.0` names a project note
- **THEN** the reference resolves to that project

#### Scenario: Note reference resolves a reference in any category

- **WHEN** `note:Paris` names a reference with `category: place`
- **THEN** the reference resolves to that note

#### Scenario: Notes and references share one scheme

- **WHEN** a note declares `type: note` and a reference declares `type: reference`
- **THEN** both are addressable through the `note` scheme

#### Scenario: Namespaces are separate

- **WHEN** `note:Ada` is resolved and the only note named `Ada` is a project
- **THEN** the reference is unresolved and does not resolve to the project

#### Scenario: Unknown scheme is external

- **WHEN** a destination uses `https:`, `mailto:`, or any scheme outside the two internal schemes
- **THEN** the system treats it as an external link and never as an internal reference

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

### Requirement: Type changes between note and project

A note SHALL resolve only under the scheme that covers its current type. When a note changes type, references that no longer match SHALL become unresolved and be reported; they MUST NOT be retargeted automatically. References within the `note` scheme SHALL survive changes between `note` and any `reference`, including a category change.

#### Scenario: Note becomes a reference

- **WHEN** a note referenced as `note:Prepare report` changes type from `note` to `reference`
- **THEN** `note:Prepare report` still resolves to it

#### Scenario: A reference gains a category

- **WHEN** a note referenced as `note:Ada` becomes a reference with `category: person`
- **THEN** `note:Ada` still resolves to it

#### Scenario: Note leaves the note scheme

- **WHEN** a note referenced as `note:Prepare report` changes type to `project`
- **THEN** the inbound reference is reported as unresolved and is not retargeted to `project:Prepare report`

#### Scenario: References are not retargeted

- **WHEN** a type change makes a reference unresolved
- **THEN** the application does not rewrite the reference to the new scheme

## MODIFIED Requirements

### Requirement: Internal reference syntax

Afanes SHALL recognize an internal reference only as a Markdown link whose destination is `scheme:name`, where the scheme is `project` or `note`. The label is presentation only. Angle-bracketed destinations are accepted, and are required when the name contains characters that a bare Markdown destination cannot carry.

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

## REMOVED Requirements

### Requirement: Scheme vocabulary and target types

**Reason**: The `person` scheme is removed and every reference shares the `note` scheme. The behavior is restated under the new requirement.

**Migration**: Rewrite `person:Name` destinations to `note:Name`.

### Requirement: Reference extraction scope

**Reason**: Frontmatter no longer holds references; extraction reads the body only. The behavior is restated under the new requirement.

**Migration**: Move `people` and `project` values into the body as links or step owners.

### Requirement: Type changes

**Reason**: `action` is not a type and `person` is not a scheme, so the old scenarios no longer apply. The behavior is restated under the new requirement.

**Migration**: None; references follow the new type rules automatically.

### Requirement: Frontmatter reference values

**Reason**: The `people` and `project` keys are retired. Relations are body links, and step owners use the step metadata object.

**Migration**: Replace `people: ["person:Ada"]` with a body link `[Ada](<note:Ada>)` or a step `owners` entry. Replace `project: "project:X"` by moving the work into that project's body as a step.
