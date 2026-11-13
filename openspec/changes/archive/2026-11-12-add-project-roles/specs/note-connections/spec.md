# Spec Delta

## ADDED Requirements

### Requirement: Owned-project connections

A page SHALL list the open projects whose `owner` value resolves to it. A project SHALL appear once,
ordered by display title. Finished owned projects SHALL be hidden until the reader enables the
completed view. A value that matches no note or matches more than one note SHALL contribute nothing.

#### Scenario: A project owner is listed

- **WHEN** an open project declares `owner: Sam Rivera` and exactly one note is named `Sam Rivera`
- **THEN** that page lists the project under `Owned projects`

#### Scenario: An unmatched owner stays plain text

- **WHEN** a project declares `owner: Finance team` and no note has that name
- **THEN** no page lists the project under `Owned projects`

#### Scenario: A finished project starts hidden

- **WHEN** a project with a matching owner is done, cancelled, or archived
- **THEN** it is absent until the reader enables the completed view

#### Scenario: A missing or ambiguous owner contributes nothing

- **WHEN** an owner value matches no note or matches two notes
- **THEN** no page lists the project under `Owned projects`

#### Scenario: A project appears once

- **WHEN** a project declares one matching owner
- **THEN** the owner's page lists the project exactly once

#### Scenario: Owned projects are ordered by title

- **WHEN** a page owns two open projects
- **THEN** they appear by display title

### Requirement: Connections are ordered by relationship

The Connections section SHALL present `Linked from`, `Owned projects`, `Owned steps`, and
`Requested projects` in that order. A section SHALL be omitted when it has no item. The completed
views SHALL NOT change the section order.

#### Scenario: All sections are ordered

- **WHEN** a page has every kind of connection
- **THEN** the sections appear in the fixed order

#### Scenario: An empty section does not reorder the others

- **WHEN** a page has no owned steps
- **THEN** the remaining sections keep their relative order

#### Scenario: Toggling completed items does not reorder sections

- **WHEN** the reader enables or hides a completed view
- **THEN** the section order is unchanged

## MODIFIED Requirements

### Requirement: Completed connections are opt-in

The completed view SHALL be presented separately for `Owned steps` and for finished projects. The
finished-project view SHALL reveal both finished owned projects and finished requested projects. Both
views SHALL start hidden when a page opens, and each SHALL reveal only its own completed or finished
items. Changing the open page SHALL return both views to hidden.

#### Scenario: Both views start hidden

- **WHEN** a page with completed steps and finished projects opens
- **THEN** neither completed item is visible

#### Scenario: Each view is independent

- **WHEN** the reader enables the completed view for steps
- **THEN** finished projects remain hidden

#### Scenario: The finished-project view covers both roles

- **WHEN** the reader enables the finished-project view
- **THEN** both finished owned projects and finished requested projects are revealed

#### Scenario: A new page resets the views

- **WHEN** the reader opens another page
- **THEN** both completed views are hidden again

### Requirement: Connections are read-only

The Connections section SHALL be derived from the current snapshot and MUST NOT create, change, move,
or remove a note. Selecting a linked note, an owned-project heading, or a requested-project heading
SHALL open that page through the existing navigation rules. Selecting an owned step SHALL open its
project at the top.

#### Scenario: Selecting a linked note opens it

- **WHEN** the reader selects an entry under `Linked from`
- **THEN** that note opens in the page pane

#### Scenario: Selecting an owned step opens its project

- **WHEN** the reader selects a step under `Owned steps`
- **THEN** the step's project opens at the top

#### Scenario: Selecting an owned project opens it

- **WHEN** the reader selects an entry under `Owned projects`
- **THEN** that project opens

#### Scenario: Reading connections writes nothing

- **WHEN** the section is shown, expanded, or collapsed
- **THEN** no note file is created, changed, moved, or removed

### Requirement: Connections appear only when they exist

The section SHALL be present on every parsed note that has at least one connection and SHALL be
absent when the page has none. It MUST NOT be shown for a note the scan could not parse.

#### Scenario: A connected page shows the section

- **WHEN** a parsed note has an inbound reference, an owned project, an owned step, or a requested
  project
- **THEN** the page shows a Connections section

#### Scenario: An owned project alone shows the section

- **WHEN** a parsed note is named as a project owner and has no other connection
- **THEN** the page shows a Connections section

#### Scenario: A page with no connections hides the section

- **WHEN** a parsed note has no inbound reference, owned project, owned step, or requested project
- **THEN** the page shows no Connections section

#### Scenario: A broken note has no section

- **WHEN** a note opens in raw rescue mode because parsing failed
- **THEN** no Connections section is shown
