# vault-browsing Specification

## Purpose

Defines the persistent workspace shell and browser that make every parsed note reachable, grouped by type with a date-based Log lens, searchable by title and identity, and openable in the shared page pane.

## Requirements

### Requirement: The workspace keeps the browser visible

While a vault is open, the workspace SHALL show a navigation region of destinations and counts, a browser region for the active destination, and a detail region for the page or focused flow. The navigation region SHALL also show the vault identity and the primary menu. The browser region SHALL show the active destination's search entry, actions, and list, calendar, or queue.

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

- **WHEN** the user expands a group, switches sections, or searches
- **THEN** no note file is created, changed, or removed

#### Scenario: Navigation lists destinations only

- **WHEN** the workspace renders the navigation region
- **THEN** it shows destinations, their counts, the vault identity, and the primary menu, and does not show a note list or the search entry

#### Scenario: The browser belongs to the active destination

- **WHEN** the user selects Projects
- **THEN** the browser region shows the project groups rather than the Inbox list

### Requirement: The browser groups every parsed note

The browser SHALL expose every parsed note under Inbox, Projects, References, Log, Needs attention,
or Unreadable notes. A note SHALL appear in exactly one group in normal browsing: log notes under
Log, and every other note under its type group. References SHALL be grouped by their category label.
Captures under `inbox/` SHALL appear only under Inbox, and notes under `trash/` SHALL NOT appear. The
Log's Everything mode SHALL be an additional date lens that may show a note beside its type group.

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

### Requirement: Selecting a browser entry opens it in the page pane

Selecting any browser entry SHALL open that note in the detail region with its display title, vault-relative path, and rendered body. The selection SHALL use the page history and conflict rules. When the layout shows one region at a time, the browser SHALL be the root of that history, so Back returns from a note to the browser.

#### Scenario: Project opens from the browser

- **WHEN** the user selects a project under Projects
- **THEN** the detail region shows that project

#### Scenario: Back returns to the previous page

- **WHEN** the user selects a project after reading a reference and then chooses Back
- **THEN** the reference page is shown again

#### Scenario: Back returns to the browser when one region is shown

- **WHEN** the user opens the first note in a layout that shows one region at a time and then chooses Back
- **THEN** the browser is shown again

#### Scenario: Dirty draft is committed before selection

- **WHEN** the user selects another browser entry while the current page has unsaved changes
- **THEN** the current draft is saved before the page changes

#### Scenario: Conflict blocks selection

- **WHEN** the current page has an unresolved disk conflict
- **THEN** selecting another browser entry does not change the page until the conflict is resolved

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

### Requirement: The workspace stays interactive across refreshes

After any workspace refresh — a section switch, search, explicit refresh, page command, processing or review update, or background scan — every navigation entry, count, browser control, search entry, action, and the detail region SHALL remain usable. A refresh MUST NOT raise a control-lifecycle error or leave the workspace partially updated.

#### Scenario: A section switch follows startup

- **WHEN** the workspace has rendered and the reader selects another destination
- **THEN** the active navigation entry uses the neutral selected-row treatment and no error is shown

#### Scenario: A section switch follows a background scan

- **WHEN** a background refresh has applied a changed scan
- **THEN** selecting another destination still updates the navigation region

#### Scenario: An immutable section entry is recovered

- **WHEN** the presentation toolkit has marked a navigation entry as immutable
- **THEN** the next refresh restores the entry's usability and the reader can switch destinations

#### Scenario: The browser column survives a refresh

- **WHEN** a refresh rebuilds the workspace
- **THEN** the browser list, its search entry, and its actions are still usable

#### Scenario: Refreshing controls writes nothing

- **WHEN** the workspace refreshes its controls
- **THEN** no note file is created, changed, moved, or removed

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

### Requirement: The References section offers a new-reference action

When a vault is open, the References section SHALL offer a New action. The action SHALL open a dialog that asks for a note name and a template card or Empty. The action MUST NOT be available without an open vault.

#### Scenario: The action is present

- **WHEN** the user views the References section
- **THEN** a New action is visible

#### Scenario: The dialog asks for a name and a card

- **WHEN** the user starts the New action
- **THEN** the dialog shows a name field, the valid cards, and Empty

#### Scenario: Invalid cards are reported

- **WHEN** the templates folder contains invalid cards
- **THEN** the dialog names them and still lists the valid cards

#### Scenario: No vault means no action

- **WHEN** no vault is open
- **THEN** the New action is not offered

### Requirement: Browser creation writes immediately

Creating a reference from the browser SHALL write the note atomically and SHALL open it in edit mode. A blank name or a name collision MUST NOT create a note and SHALL be reported.

#### Scenario: Create writes and opens edit mode

- **WHEN** the user submits a valid name and card
- **THEN** the note is written and the page editor opens on it in edit mode

#### Scenario: Empty uses the general category

- **WHEN** the user creates with Empty
- **THEN** the note declares `category: general` and has no starter body

#### Scenario: A blank name is rejected

- **WHEN** the user submits a blank name
- **THEN** no note is created and the dialog reports that a name is required

#### Scenario: A collision is reported

- **WHEN** the name already belongs to a note in the same scheme
- **THEN** no note is created, no suffix is added, and the dialog reports the collision

### Requirement: A browser-created reference appears in its group

After a browser creation succeeds, the application SHALL refresh the scan and SHALL show the new note under its category group. An active search query SHALL be cleared so the note is visible.

#### Scenario: The note appears under its category

- **WHEN** a note is created from a `person` card
- **THEN** it appears under the `person` group

#### Scenario: An active search is cleared

- **WHEN** the user creates a note while a search query is active
- **THEN** the query is cleared and the new note is visible

#### Scenario: A refresh failure is reported

- **WHEN** the note is created but the scan fails
- **THEN** the note remains and the application reports the refresh failure

### Requirement: The workspace arranges its columns by available width

The workspace SHALL choose its column arrangement from the available width without requiring manual resizing. At 1100 px or more it SHALL show navigation, browser, and detail together. From 1024 to 1099 px it SHALL keep browser and detail and place navigation behind a toggle. A narrower browser presentation SHALL show one region at a time with the browser as the root. A resize MUST preserve the open page, active destination, and search query.

#### Scenario: A wide window shows three regions

- **WHEN** the window is 1100 px wide or wider
- **THEN** navigation, browser, and detail are visible side by side

#### Scenario: A medium window keeps browser and detail

- **WHEN** the window is between 1024 and 1099 px wide
- **THEN** the browser and detail remain visible and the navigation is reached through a toggle

#### Scenario: A narrow presentation shows one region

- **WHEN** the presentation is narrower than 1024 px, as in a browser presentation
- **THEN** the browser is shown first and selecting a note replaces it with the detail

#### Scenario: A resize preserves state

- **WHEN** the window is resized across a breakpoint
- **THEN** the open page, active destination, and search query are unchanged

#### Scenario: A hidden navigation remains reachable

- **WHEN** the navigation is behind a toggle
- **THEN** the toggle exposes every destination and count

### Requirement: The workspace toolbar reflects the active view

The detail region SHALL present an in-window toolbar aligned with the navigation and browser headers. It SHALL show the active page or flow title, a Back control when a previous view exists, at most one suggested action, and a secondary menu for the remaining actions. The browser header SHALL show its destination title, search entry, and section actions. The workspace MUST NOT draw controls into the operating-system title bar.

#### Scenario: The toolbar names the active page

- **WHEN** a note is open
- **THEN** the detail toolbar shows the note's title beside the navigation and browser headers

#### Scenario: Back appears when a previous view exists

- **WHEN** the detail region holds a view reached from another view
- **THEN** the toolbar shows a Back control

#### Scenario: At most one suggested action

- **WHEN** the toolbar renders the active view's actions
- **THEN** no more than one action uses the suggested style

#### Scenario: Remaining actions live in the secondary menu

- **WHEN** the active view offers more actions than the toolbar shows
- **THEN** the remaining actions are available from a secondary menu

#### Scenario: The browser header holds search and section actions

- **WHEN** a destination is active
- **THEN** its header shows the destination title, the search entry, and the actions that belong to that destination

#### Scenario: No controls in the title bar

- **WHEN** the application runs on any desktop platform
- **THEN** the operating-system title bar keeps its native decorations and the workspace toolbar holds the application controls

### Requirement: The browser hosts the active destination's controls

The browser region SHALL host the controls that act on the active destination. Inbox SHALL show the capture composer at the top of the browser. References SHALL show the New Reference action. Log SHALL show its date-lens controls. A New Capture toolbar action SHALL switch to Inbox and focus the composer from any other destination.

#### Scenario: Inbox shows the composer

- **WHEN** the user selects Inbox
- **THEN** the capture composer is at the top of the browser region

#### Scenario: References shows New Reference

- **WHEN** the user selects References
- **THEN** the New Reference action is visible in the browser header

#### Scenario: Log shows its date controls

- **WHEN** the user selects Log
- **THEN** the Entries and Everything controls, Today's Entry, and the calendar are available in the browser region

#### Scenario: New Capture focuses the composer

- **WHEN** the user starts New Capture from another destination
- **THEN** the workspace switches to Inbox and focuses the composer

#### Scenario: Another destination omits the Inbox composer

- **WHEN** the user selects Projects
- **THEN** the capture composer is not shown in the browser region

### Requirement: Search spans every destination

A non-empty search query SHALL filter every destination, and the browser SHALL show matching results grouped by section. The active destination MUST NOT limit the results. The Log calendar and date tree SHALL use the same query. Clearing the query SHALL restore the active destination's normal browser.

#### Scenario: A query lists matches from several sections

- **WHEN** the user types a term that appears in an Inbox capture and a reference
- **THEN** the browser shows both matches under their section headings

#### Scenario: A match outside the active section is listed

- **WHEN** the user starts in Inbox and searches for a term that appears only in a project
- **THEN** the project is listed

#### Scenario: Destination counts remain totals

- **WHEN** a search query is active
- **THEN** the navigation counts still show each destination's total, not the number of matches

#### Scenario: The Log calendar uses the query

- **WHEN** the user searches while Log is active
- **THEN** both the calendar marks and the date tree show only matching entries

#### Scenario: Clearing restores the active destination

- **WHEN** the user clears the query
- **THEN** the browser shows the active destination's normal list or calendar

#### Scenario: Switching destinations leaves search

- **WHEN** the user selects a destination while a query is active
- **THEN** the query is cleared and that destination's browser is shown

#### Scenario: No match is explained

- **WHEN** a query matches no note
- **THEN** the browser shows a no-match state that names the query

### Requirement: The workspace exposes the vault and its primary menu

The workspace SHALL show the vault identity in the navigation region and SHALL offer a primary menu above the navigation list. The menu SHALL provide Change Vault…, Create Vault…, Close Vault, and About Afanes. The workspace MUST NOT show a separate status bar for the vault path or vault actions.

#### Scenario: Vault identity is visible

- **WHEN** a vault is open
- **THEN** the navigation region names the vault and its full path is available without a status bar

#### Scenario: The primary menu offers the app and vault actions

- **WHEN** the user opens the primary menu
- **THEN** Change Vault…, Create Vault…, Close Vault, and About Afanes are available

#### Scenario: Change Vault uses the existing flow

- **WHEN** the user chooses Change Vault…
- **THEN** the existing vault chooser is shown

#### Scenario: Create Vault uses the existing flow

- **WHEN** the user chooses Create Vault…
- **THEN** the existing new-vault flow is shown

#### Scenario: Close Vault returns to the welcome state

- **WHEN** the user chooses Close Vault
- **THEN** the workspace closes and the welcome state is shown

#### Scenario: About names the application

- **WHEN** the user chooses About Afanes
- **THEN** a dialog names the application and its version

#### Scenario: No status bar remains

- **WHEN** the workspace renders
- **THEN** no status bar shows the vault path or duplicates the vault actions

### Requirement: Review shows its snapshot queue in the browser

While Review is active, the browser SHALL show the session's snapshot queue in review order as selectable cards and SHALL mark the current item. Selecting a card SHALL make that item current in the detail without reviewing, skipping, or reordering any item. Showing the queue MUST NOT reorder it, add new work to it, or change review records.

#### Scenario: The queue is shown in order

- **WHEN** a review session starts with Inbox items, due steps, and projects
- **THEN** the browser lists them as cards in the session's order

#### Scenario: The current item is marked

- **WHEN** the review session advances
- **THEN** the browser marks the new current card

#### Scenario: Selecting a card shows that item

- **WHEN** the user selects a card in the browser queue
- **THEN** the detail shows that item and its actions

#### Scenario: Selecting a card changes no review record

- **WHEN** the user selects a card in the browser queue
- **THEN** no item is reviewed or skipped and the queue order is unchanged

#### Scenario: New work waits for the next session

- **WHEN** a note is created during the session
- **THEN** the browser queue does not show it

#### Scenario: Viewing the queue changes no review state

- **WHEN** the user views the browser queue without selecting a card
- **THEN** no item is reviewed, skipped, or reordered

#### Scenario: A completed session shows its outcome

- **WHEN** every queue item has been passed
- **THEN** the browser no longer marks an active card and the detail shows the completion summary

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
