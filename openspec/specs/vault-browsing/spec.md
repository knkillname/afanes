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

### Requirement: The browser groups every parsed note

The browser SHALL expose every parsed note under Inbox, Projects, References, Needs attention, or Unreadable notes. A note SHALL appear in exactly one group. References SHALL be grouped by their category label. Captures under `inbox/` SHALL appear only under Inbox, and notes under `trash/` SHALL NOT appear.

#### Scenario: Project appears under Projects

- **WHEN** the vault contains a parsed `type: project` note
- **THEN** the browser lists it under Projects

#### Scenario: A person reference groups by its label

- **WHEN** the vault contains a reference with `category: person`
- **THEN** the browser groups it under the `person` label

#### Scenario: Categorized references group by label

- **WHEN** the vault contains references with `category: person` and `category: place`
- **THEN** the browser groups each under its own label

#### Scenario: Uncategorized reference appears under References

- **WHEN** the vault contains a reference with no category
- **THEN** the browser lists it under References

#### Scenario: Capture appears only under Inbox

- **WHEN** a note is under `inbox/`
- **THEN** it appears under Inbox and in no other group

#### Scenario: Misplaced note needs attention

- **WHEN** a parsed `type: note` exists outside `inbox/`
- **THEN** the browser lists it under Needs attention

#### Scenario: Trashed note is absent

- **WHEN** a note is under `trash/`
- **THEN** it appears in no browser group

#### Scenario: Inbox capture becomes a project

- **WHEN** a capture is processed into a project
- **THEN** it leaves the Inbox group and appears under Projects

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

### Requirement: The browser searches titles, identities, and bodies

The browser SHALL provide a search field that filters entries by display title, identity, prose body text, and step text. Matching SHALL ignore case, Unicode form, and repeated whitespace. Step metadata comments SHALL NOT be searched.

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

#### Scenario: Metadata is not searched

- **WHEN** a term appears only inside a step's metadata comment
- **THEN** no result is produced for that term

#### Scenario: Matching ignores case and repeated whitespace

- **WHEN** the user types `ada` or `Ada,   Countess of Lovelace`
- **THEN** the matching page is listed

### Requirement: The browser reflects vault changes

After a capture, processing apply, page save, rename, trash, or explicit refresh, and after an edit made outside the application, the browser SHALL reflect the resulting vault state from the latest scan. An external change SHALL be reflected without a manual refresh.

#### Scenario: Processing moves the entry

- **WHEN** a capture is processed into a project
- **THEN** it disappears from Inbox and appears under Projects

#### Scenario: Rename updates the entry

- **WHEN** a page is renamed
- **THEN** the browser shows the new identity and title

#### Scenario: Trash removes the entry

- **WHEN** a page is moved to trash
- **THEN** it disappears from the browser

#### Scenario: An external creation appears

- **WHEN** a note is created outside the application
- **THEN** it appears in the browser without the user asking for a refresh

#### Scenario: An external edit updates the row

- **WHEN** a project file changes outside the application
- **THEN** its row shows the new open-step count and next step

#### Scenario: An external trash removes the entry

- **WHEN** a note is moved under `trash/` outside the application
- **THEN** it disappears from the browser without the user asking for a refresh

### Requirement: A background refresh does not interrupt work

A refresh triggered by an external change SHALL be read-only. It MUST NOT write a note file, clear a message the user can see, discard an open draft, or end a processing or review flow, and it SHALL stop when no vault is open.

#### Scenario: A visible message survives

- **WHEN** a background refresh completes while a message from a user command is shown
- **THEN** the message remains visible

#### Scenario: An open draft survives

- **WHEN** a background refresh detects a change while a page draft is open
- **THEN** the draft text and its labels are unchanged

#### Scenario: A focused flow keeps its note

- **WHEN** a background refresh runs during processing or review
- **THEN** the flow remains on the same note

#### Scenario: Background work writes nothing

- **WHEN** a background refresh runs
- **THEN** no note file is created, changed, or removed

#### Scenario: No vault means no scanning

- **WHEN** no vault is open, or the vault was closed
- **THEN** no scan runs in the background

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
