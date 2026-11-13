# Spec Delta

## ADDED Requirements

### Requirement: Search is a browser filter, not a navigation destination

The global search entry SHALL be part of the browser region and SHALL be available without entering a separate search destination. The navigation region MUST NOT offer a Search destination, a Search section, a search count, or a selected search row. The navigation region SHALL continue to list only its existing destinations and counts.

#### Scenario: Search is not a sidebar destination

- **WHEN** the workspace renders the navigation region
- **THEN** no Search destination, Search section, or search count appears

#### Scenario: Search remains available from every destination

- **WHEN** the user enters a query while any content destination is active
- **THEN** the browser shows the global search results without changing the active destination

## MODIFIED Requirements

### Requirement: The workspace toolbar reflects the active view

The detail region SHALL present an in-window toolbar aligned with the navigation and browser headers. It SHALL show the active page or flow title, a Back control when a previous view exists, at most one suggested action, and a secondary menu for the remaining actions. The browser header SHALL show its destination title and section actions. A permanent, full-width search row directly beneath the browser header SHALL hold the global search entry. The workspace MUST NOT draw controls into the operating-system title bar.

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
- **THEN** its header shows the destination title and the actions that belong to that destination, and the search entry appears in the dedicated row beneath the header

#### Scenario: The search entry has its own row

- **WHEN** the browser renders
- **THEN** the search entry is permanently available in a full-width row beneath the browser header, separate from the title and actions

#### Scenario: No controls in the title bar

- **WHEN** the application runs on any desktop platform
- **THEN** the operating-system title bar keeps its native decorations and the workspace toolbar holds the application controls

### Requirement: The browser hosts the active destination's controls

The browser region SHALL host the controls that act on the active destination. While no search is active, Inbox SHALL show the capture composer at the top of the browser, References SHALL show the New Reference action, and Log SHALL show its date-lens controls. While a search query is active, the browser SHALL hide those destination-specific controls and show the global search results instead. A New Capture toolbar action SHALL switch to Inbox and focus the composer from any other destination.

#### Scenario: Inbox shows the composer

- **WHEN** the user selects Inbox without an active search query
- **THEN** the capture composer is at the top of the browser region

#### Scenario: References shows New Reference

- **WHEN** the user selects References without an active search query
- **THEN** the New Reference action is visible in the browser header

#### Scenario: Log shows its date controls

- **WHEN** the user selects Log without an active search query
- **THEN** the Entries and Everything controls, Today's Entry, and the calendar are available in the browser region

#### Scenario: New Capture focuses the composer

- **WHEN** the user starts New Capture from another destination
- **THEN** the workspace switches to Inbox and focuses the composer

#### Scenario: Another destination omits the Inbox composer

- **WHEN** the user selects Projects
- **THEN** the capture composer is not shown in the browser region

#### Scenario: Search hides destination controls

- **WHEN** a non-empty search query is active
- **THEN** the capture composer, New Reference action, Log date-lens controls, and Review queue are not shown

### Requirement: Search spans every destination

A non-empty search query SHALL replace the active destination's browser content with matching results grouped by section. The active destination MUST NOT limit the results. While the query is active, the browser header SHALL show Search results, and the browser MUST NOT show the Log calendar, date tree, or other destination-specific content. Clearing the query SHALL restore the active destination's normal browser.

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
- **THEN** the global result list is built from the query-filtered Log timeline, and the Log calendar and date tree are not shown

#### Scenario: The title names the search mode

- **WHEN** a non-empty query is active
- **THEN** the browser title shows Search results instead of the active destination title

#### Scenario: Clearing restores the active destination

- **WHEN** the user clears the query
- **THEN** the browser shows the active destination's normal list or calendar

#### Scenario: Switching destinations leaves search

- **WHEN** the user selects a destination while a query is active
- **THEN** the query is cleared and that destination's browser is shown

#### Scenario: No match is explained

- **WHEN** a query matches no note
- **THEN** the browser shows a no-match state that names the query
