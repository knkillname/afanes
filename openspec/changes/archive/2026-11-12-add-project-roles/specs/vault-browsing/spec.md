# Spec Delta

## MODIFIED Requirements

### Requirement: The browser searches titles, identities, and bodies

The browser SHALL provide a search field that filters entries by display title, identity, prose body
text, step text, and role names (`owner`, `asked_by`, and step `owners`). Matching SHALL ignore case,
Unicode form, and repeated whitespace. Other step metadata and unknown frontmatter keys SHALL NOT be
searched.

#### Scenario: Title match is listed

- **WHEN** the user types part of a page's display title
- **THEN** that page is listed

#### Scenario: Identity match is listed

- **WHEN** the user types part of a page's identity
- **THEN** that page is listed

#### Scenario: Body match is listed

- **WHEN** a search term appears only in a note's prose body
- **THEN** that note is listed

#### Scenario: Step text match names the project

- **WHEN** a search term appears in a step
- **THEN** the project is listed and the matching step is shown with its project

#### Scenario: Owner match names the project

- **WHEN** a search term appears only in a project's `owner` value
- **THEN** that project is listed

#### Scenario: Requester match names the project

- **WHEN** a search term appears only in a project's `asked_by` value
- **THEN** that project is listed

#### Scenario: Step owner match names the project

- **WHEN** a search term appears only in a step's `owners` value
- **THEN** the project is listed

#### Scenario: Metadata is not searched

- **WHEN** a term appears only inside a step's `plan`, `actual`, or `tags` metadata
- **THEN** no result is produced for that term; role names are searched separately

#### Scenario: Matching ignores case and repeated whitespace

- **WHEN** the user types `ada` or `Ada,   Countess of Lovelace`
- **THEN** the matching page is listed
