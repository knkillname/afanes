# Spec Delta

## MODIFIED Requirements

### Requirement: The browser groups every parsed note

The browser SHALL expose every parsed note under Inbox, Projects, References, Log, Needs attention,
or Unreadable notes. A note SHALL appear in exactly one group in normal browsing: log notes under
Log, and every other note under its type group. References SHALL be grouped by their category label.
Captures under `inbox/` SHALL appear only under Inbox, and notes under `trash/` SHALL NOT appear in
these active-note groups; the Trash destination SHALL present managed trashed entries separately.
The Log's Everything mode SHALL be an additional date lens that may show a note beside its type
group.

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
- **THEN** it appears in no active-note group and only a managed entry may appear in Trash

#### Scenario: Inbox capture becomes a project

- **WHEN** a capture is processed into a project
- **THEN** it leaves the Inbox group and appears under Projects

#### Scenario: A log entry appears under Log

- **WHEN** the vault contains a parsed `type: log` note
- **THEN** the browser lists it under Log and in no other type group

#### Scenario: A log entry is not a reference

- **WHEN** the vault contains a log entry and a reference with the same name
- **THEN** the Log lists the log entry and References lists only the reference

#### Scenario: Everything is a lens

- **WHEN** the Log is in Everything mode and the vault contains a project
- **THEN** the project appears under Projects and in the Log date lens

#### Scenario: Entries is not a lens

- **WHEN** the Log is in Entries mode and the vault contains a project
- **THEN** the project appears only under Projects

### Requirement: The workspace keeps the browser visible

While a vault is open, the workspace SHALL show a navigation region of destinations and counts, a
browser region for the active destination, and a detail region for the page or focused flow. The
navigation region SHALL also show the vault identity and the primary menu. The browser region SHALL
show the active destination's search entry, actions, and list, calendar, or queue.

#### Scenario: Browser and page are visible together

- **WHEN** a vault is open, a note is selected, and the window is wide enough for three regions
- **THEN** the navigation, browser, and detail regions are all visible

#### Scenario: Switching sections keeps the page

- **WHEN** the user switches from Inbox to Projects
- **THEN** the browser lists projects and the currently open page remains visible

#### Scenario: Focused flow keeps the browser

- **WHEN** the user starts a processing or review flow
- **THEN** the navigation and browser remain visible while the detail region shows that flow

#### Scenario: Browsing performs no write

- **WHEN** the user expands a group, searches, or switches to a destination other than Trash
- **THEN** no note file is created, changed, or removed

#### Scenario: Selecting Trash may run retention

- **WHEN** the user selects Trash
- **THEN** expired managed trash entries may be removed before the list is shown

#### Scenario: Navigation lists destinations only

- **WHEN** the workspace renders the navigation region
- **THEN** it shows destinations, their counts, the vault identity, and the primary menu, and does not show a note list or the search entry

#### Scenario: The browser belongs to the active destination

- **WHEN** the user selects Projects
- **THEN** the browser region shows the project groups rather than the Inbox list

## ADDED Requirements

### Requirement: The navigation includes a Trash destination

The workspace navigation SHALL include a Trash destination with a managed-entry count. Its browser
SHALL list each managed entry by title and birthplace. The browser header SHALL offer Empty Trash
when managed entries exist. Selecting an entry SHALL open its read-only trashed page.

#### Scenario: Trash appears in the navigation

- **WHEN** a vault is open
- **THEN** the navigation shows a Trash destination and its managed-entry count

#### Scenario: A row names the title and birthplace

- **WHEN** a managed entry is listed
- **THEN** its row shows the note title and its birthplace

#### Scenario: Selecting an entry opens the trashed page

- **WHEN** the user selects a Trash row
- **THEN** the detail region opens that note read-only

#### Scenario: Empty Trash is available from the browser header

- **WHEN** Trash is active and managed entries exist
- **THEN** the browser header offers Empty Trash

#### Scenario: An empty Trash is explained

- **WHEN** no managed entries exist
- **THEN** the browser shows an empty Trash state instead of rows

### Requirement: Global search includes managed trashed notes

A non-empty global search query SHALL include matching managed trashed notes in a separate Trash
group assembled with the active-note groups. Selecting a Trash result SHALL open the note read-only.
Unmanaged files MUST NOT appear in search.

#### Scenario: A trashed note is found

- **WHEN** the user searches for text that appears only in a managed trashed note
- **THEN** the results include a Trash group with that note

#### Scenario: The Trash group does not mix with active notes

- **WHEN** a search matches both active and trashed notes
- **THEN** the trashed matches appear under Trash and the active matches under their own groups

#### Scenario: A trashed result opens read-only

- **WHEN** the user selects a result from the Trash group
- **THEN** the note opens read-only with its Restore action

#### Scenario: An unmanaged file is not searchable

- **WHEN** a file in `trash/` has no valid birthplace metadata
- **THEN** its text does not appear in search results

#### Scenario: Searching from Trash stays global

- **WHEN** the user types a query while Trash is active
- **THEN** the browser shows matching active notes and managed trashed notes, not only the Trash rows
