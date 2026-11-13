# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The browser searches titles, identities, and bodies`
- TO: `### Requirement: The browser searches titles, identities, bodies, steps, and role names`

## MODIFIED Requirements

### Requirement: The browser searches titles, identities, bodies, steps, and role names

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
- **THEN** the project is listed

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

## ADDED Requirements

### Requirement: A page change starts at the top

Whenever the page pane switches to a page, including browser selection, a link, a connection entry, or
Back, the new page SHALL start at the top.

#### Scenario: Browser selection starts at the top

- **WHEN** the user selects a page while the previous page is scrolled
- **THEN** the new page starts at the top

#### Scenario: A link starts at the top

- **WHEN** the user follows a link while the previous page is scrolled
- **THEN** the linked page starts at the top

#### Scenario: A connection starts at the top

- **WHEN** the user selects a connection entry while the page is scrolled
- **THEN** the connection target starts at the top

#### Scenario: Back starts at the top

- **WHEN** the user chooses Back while the current page is scrolled
- **THEN** the previous page starts at the top
