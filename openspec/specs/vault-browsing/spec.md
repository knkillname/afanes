# vault-browsing Specification

## Purpose

Defines the persistent workspace shell and browser that make every parsed note reachable, grouped by type, searchable by title and identity, and openable in the shared page pane.

## Requirements

### Requirement: The workspace keeps the browser visible

While browsing a vault, the application SHALL show a persistent navigation browser beside the main workspace area. The main area SHALL show the page pane during browsing and MAY temporarily show a processing or review flow; the browser SHALL remain visible.

#### Scenario: Browser and page are visible together

- **WHEN** a vault is open and a note is selected
- **THEN** the browser and the page pane are both visible

#### Scenario: Switching sections keeps the page

- **WHEN** the user switches from Inbox to Projects
- **THEN** the browser lists projects and the currently open page remains visible

#### Scenario: Focused flow keeps the browser

- **WHEN** the user starts a processing or review flow
- **THEN** the browser remains visible while the main area shows that flow

#### Scenario: Browsing performs no write

- **WHEN** the user expands a group, switches sections, or searches
- **THEN** no note file is created, changed, or removed

### Requirement: The browser groups every parsed note by type

The browser SHALL expose every parsed note under Inbox, Projects, Actions, People, References, or Notes. A note SHALL appear in exactly one group. Captures under `inbox/` SHALL appear only under Inbox, and notes under `trash/` SHALL NOT appear.

#### Scenario: Project appears under Projects

- **WHEN** the vault contains a parsed `type: project` note
- **THEN** the browser lists it under Projects

#### Scenario: Person appears under People

- **WHEN** the vault contains a parsed reference with `category: person`
- **THEN** the browser lists it under People

#### Scenario: Uncategorized reference appears under References

- **WHEN** the vault contains a parsed reference with no category
- **THEN** the browser lists it under References

#### Scenario: Capture appears only under Inbox

- **WHEN** a note is under `inbox/`
- **THEN** it appears under Inbox and not under Notes

#### Scenario: Trashed note is absent

- **WHEN** a note is under `trash/`
- **THEN** it appears in no browser group

#### Scenario: Inbox capture becomes an action

- **WHEN** a capture is processed into an action
- **THEN** it leaves the Inbox group and appears under Actions

### Requirement: Selecting a browser entry opens it in the page pane

Selecting any browser entry SHALL open that note in the page pane with its display title, vault-relative path, and rendered body. The selection SHALL use the existing page history and conflict rules.

#### Scenario: Project opens from the browser

- **WHEN** the user selects a project under Projects
- **THEN** the page pane shows that project

#### Scenario: Back returns to the previous page

- **WHEN** the user selects a project after reading a reference and then chooses Back
- **THEN** the reference page is shown again

#### Scenario: Dirty draft is committed before selection

- **WHEN** the user selects another browser entry while the current page has unsaved changes
- **THEN** the current draft is saved before the page changes

#### Scenario: Conflict blocks selection

- **WHEN** the current page has an unresolved disk conflict
- **THEN** selecting another browser entry does not change the page until the conflict is resolved

### Requirement: The browser searches titles and identities

The browser SHALL provide a search field that filters entries by display title or identity. Matching SHALL ignore case, Unicode form, and repeated whitespace. Search in this capability SHALL NOT read note bodies.

#### Scenario: Title match is listed

- **WHEN** the user types part of a page's display title
- **THEN** that page is listed

#### Scenario: Identity match is listed

- **WHEN** the user types part of a page's identity
- **THEN** that page is listed

#### Scenario: Matching ignores case and repeated whitespace

- **WHEN** the user types `ada` or `Ada,   Countess of Lovelace`
- **THEN** the matching page is listed

#### Scenario: Body-only term is not matched

- **WHEN** a search term appears only in a note body
- **THEN** the browser does not list that note in this capability

### Requirement: The browser reflects vault changes

After a capture, processing apply, page save, rename, trash, or explicit refresh, the browser SHALL reflect the resulting vault state from the latest scan.

#### Scenario: Processing moves the entry

- **WHEN** a capture is processed into a project
- **THEN** it disappears from Inbox and appears under Projects

#### Scenario: Rename updates the entry

- **WHEN** a page is renamed
- **THEN** the browser shows the new identity and title

#### Scenario: Trash removes the entry

- **WHEN** a page is moved to trash
- **THEN** it disappears from the browser

### Requirement: Unparseable notes remain reachable

The browser SHALL list notes that the scan could not parse in a separate failures section. Selecting one SHALL open it in raw rescue mode.

#### Scenario: Broken note is listed

- **WHEN** a note has malformed frontmatter
- **THEN** it appears in the failures section rather than a type group

#### Scenario: Broken note opens in rescue mode

- **WHEN** the user selects a failure entry
- **THEN** the page pane opens the complete file text in raw rescue mode

#### Scenario: Repairing the note clears the failure

- **WHEN** a raw rescue save produces a parseable note
- **THEN** the next scan lists it under its type group and removes it from failures
