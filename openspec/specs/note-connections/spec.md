# note-connections Specification

## Purpose

Derives and presents the relationships that point at a note from the current vault snapshot, so a reader can move
backwards through references and see where a person is involved.

## Requirements

### Requirement: Linked-from connections

A page SHALL list every parsed note whose body reference uniquely resolves to it. Each referring note SHALL appear
once, by display title. References that are missing or ambiguous SHALL NOT be attributed to any page, the page SHALL
NOT list itself, and notes under `trash/` or notes that could not be parsed SHALL NOT contribute.

#### Scenario: A note that links here is listed

- **WHEN** a note body contains `[Launch](<project:Release 1.0>)` and the project page is open
- **THEN** `Linked from` lists that note by its display title

#### Scenario: Repeated links list the note once

- **WHEN** one note links to the same page three times
- **THEN** `Linked from` lists that note exactly once

#### Scenario: An unresolved reference is not listed

- **WHEN** a note links to a name that matches no note
- **THEN** the open page does not list that note in `Linked from`

#### Scenario: An ambiguous reference is not listed

- **WHEN** two notes share the referenced name and the reference is ambiguous
- **THEN** neither candidate page lists the referring note in `Linked from`

#### Scenario: A page does not list itself

- **WHEN** the open page links to its own name
- **THEN** `Linked from` does not list the open page

#### Scenario: A trashed note does not contribute

- **WHEN** a note under `trash/` links to the open page
- **THEN** `Linked from` does not list it

### Requirement: Owned-step connections

A page SHALL list the open steps of open projects whose owner name resolves to it. Steps SHALL be grouped by project,
and within a project they SHALL keep document order. Completed steps SHALL be hidden until the reader enables the
completed view.

#### Scenario: A person page lists an owned step

- **WHEN** an open project has an unchecked step with `owners: [Ada]` and exactly one note is named `Ada`
- **THEN** the `Ada` page lists that step under the project's heading

#### Scenario: Steps are grouped by project

- **WHEN** a person owns steps in two projects
- **THEN** each project appears once as a heading with its own steps beneath it

#### Scenario: Document order is preserved

- **WHEN** a project has two owned open steps
- **THEN** they appear in the order they have in the project body

#### Scenario: Completed steps start hidden

- **WHEN** a project has a checked step owned by the person
- **THEN** the step is absent until the reader enables the completed view

#### Scenario: Closed projects do not contribute

- **WHEN** a project is done, cancelled, or archived
- **THEN** its steps do not appear in `Owned steps`

### Requirement: Requested-project connections

A page SHALL list the open projects whose `asked_by` value resolves to it. A project SHALL appear once. A value
that matches no note SHALL remain plain text on the project and SHALL NOT appear in any Connections section. A
finished project SHALL be hidden until the reader enables the completed view.

#### Scenario: A matching asked-by lists the project

- **WHEN** an open project declares `asked_by: Ada Lovelace` and exactly one note is named `Ada Lovelace`
- **THEN** that page lists the project under `Requested projects`

#### Scenario: An unmatched asked-by stays plain text

- **WHEN** a project declares `asked_by: Finance team` and no note has that name
- **THEN** no page lists the project under `Requested projects`

#### Scenario: A finished project starts hidden

- **WHEN** a project with a matching `asked_by` is done
- **THEN** it is absent until the reader enables the completed view

### Requirement: Completed connections are opt-in

The completed view SHALL be presented separately for `Owned steps` and `Requested projects`. Both views SHALL start
hidden when a page opens, and each SHALL reveal only its own completed or finished items. Changing the open page
SHALL return both views to hidden.

#### Scenario: Both views start hidden

- **WHEN** a page with completed steps and finished projects opens
- **THEN** neither completed item is visible

#### Scenario: Each view is independent

- **WHEN** the reader enables the completed view for steps
- **THEN** finished projects remain hidden

#### Scenario: A new page resets the views

- **WHEN** the reader opens another page
- **THEN** both completed views are hidden again

### Requirement: Connections are read-only

The Connections section SHALL be derived from the current snapshot and MUST NOT create, change, move, or remove a
note. Selecting a linked note or a project heading SHALL open that page through the existing navigation rules.
Selecting an owned step SHALL open its project at the top.

#### Scenario: Selecting a linked note opens it

- **WHEN** the reader selects an entry under `Linked from`
- **THEN** that note opens in the page pane

#### Scenario: Selecting an owned step opens its project

- **WHEN** the reader selects a step under `Owned steps`
- **THEN** the step's project opens at the top

#### Scenario: Reading connections writes nothing

- **WHEN** the section is shown, expanded, or collapsed
- **THEN** no note file is created, changed, moved, or removed

### Requirement: Connections appear only when they exist

The section SHALL be present on every parsed note that has at least one connection and SHALL be absent when the page
has none. It MUST NOT be shown for a note the scan could not parse.

#### Scenario: A connected page shows the section

- **WHEN** a parsed note has an inbound reference, an owned step, or a requested project
- **THEN** the page shows a Connections section

#### Scenario: A page with no connections hides the section

- **WHEN** a parsed note has no inbound reference, owned step, or requested project
- **THEN** the page shows no Connections section

#### Scenario: A broken note has no section

- **WHEN** a note opens in raw rescue mode because parsing failed
- **THEN** no Connections section is shown
