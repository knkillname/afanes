# Spec Delta

## ADDED Requirements

### Requirement: Metadata role references

A project's `owner` and `asked_by` values and a step's `owners` values SHALL resolve through the
`note:` catalog as metadata references. They SHALL NOT be Markdown links, SHALL NOT use scheme
syntax in the file, and SHALL NOT be extracted as body references. A missing or ambiguous value
SHALL remain valid and SHALL contribute no connection.

#### Scenario: An owner name resolves

- **WHEN** a project declares `owner: Sam Rivera` and exactly one note is named `Sam Rivera`
- **THEN** the owner resolves to that note

#### Scenario: A requester name resolves

- **WHEN** a project declares `asked_by: Priya Nair` and exactly one note is named `Priya Nair`
- **THEN** the requester resolves to that note

#### Scenario: A step owner name resolves

- **WHEN** a step declares `owners: [Ada]` and exactly one note is named `Ada`
- **THEN** the owner resolves to that note

#### Scenario: No scheme syntax is required

- **WHEN** a project declares `owner: Sam Rivera`
- **THEN** the stored value is `Sam Rivera`, not `note:Sam Rivera`

#### Scenario: A missing role name remains valid

- **WHEN** a project declares `owner: Finance team` and no note has that name
- **THEN** the value remains and the project parses

#### Scenario: An ambiguous role name resolves to nothing

- **WHEN** two notes are named `Sam Rivera`
- **THEN** the owner value is reported as ambiguous and is attributed to neither note

## MODIFIED Requirements

### Requirement: Reference extraction reads body text

References SHALL be extracted from Markdown text content. They SHALL NOT be extracted from fenced code, indented code, inline code, HTML comments, image destinations, or step metadata. Frontmatter role names (`owner`, `asked_by`, and step `owners`) SHALL resolve as metadata references but SHALL NOT be extracted as body references.

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

#### Scenario: Frontmatter role names are not body references

- **WHEN** a project declares `owner: Sam Rivera` and `asked_by: Priya Nair`
- **THEN** no body reference is extracted from either value; both resolve only as metadata references
