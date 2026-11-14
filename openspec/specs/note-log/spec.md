# note-log Specification

## Purpose

Defines the log note type, its one-entry-per-date rule, and the Log workspace that presents dated
entries through a calendar and a collapsible year/month/day tree.

## Requirements

### Requirement: A log note is a dated entry

A note whose `type` is `log` SHALL carry an optional ISO `date`, a body, and a display title from its
first level-1 heading. It MUST NOT carry `category`, `status`, `due_date`, `asked_by`, or `owner`. A
log note without a date SHALL remain readable and SHALL appear in the Undated group rather than
being reported as a parse failure.

#### Scenario: A valid log note parses

- **WHEN** a note declares `type: log` and `date: 2025-10-12`
- **THEN** it parses as a log note with a day-precision date

#### Scenario: A log note without a date is undated

- **WHEN** a note declares `type: log` and no `date`
- **THEN** it parses and appears in the Undated group

#### Scenario: A category is rejected

- **WHEN** a log note declares `category: personal`
- **THEN** parsing reports a validation error

#### Scenario: A status is rejected

- **WHEN** a log note declares `status: archived`
- **THEN** parsing reports a validation error

#### Scenario: A due date is rejected

- **WHEN** a log note declares `due_date: 2025-10-12`
- **THEN** parsing reports a validation error

#### Scenario: A requester is rejected

- **WHEN** a log note declares `asked_by: Sam Rivera`
- **THEN** parsing reports a validation error

#### Scenario: An owner is rejected

- **WHEN** a log note declares `owner: Sam Rivera`
- **THEN** parsing reports a validation error

### Requirement: One log entry per exact date

The vault SHALL contain at most one log note for each exact date value. Creating a log entry,
processing a capture into a log entry, or changing a log entry's date SHALL be refused when another
log entry already uses that date. A year entry, a month entry, and a day entry are different dates
and MAY coexist.

#### Scenario: A duplicate day entry is refused

- **WHEN** `log/2025/10/2025-10-12.md` exists and another entry is created for `2025-10-12`
- **THEN** the creation is refused and no second file is written

#### Scenario: Today's entry opens the existing entry

- **WHEN** today already has a log entry and the user chooses **Today's entry**
- **THEN** the existing entry opens instead of a second one being created

#### Scenario: A month entry and a day entry coexist

- **WHEN** a log entry is dated `2025-10` and another is dated `2025-10-12`
- **THEN** both entries are valid and appear at their own tree levels

#### Scenario: A date change onto an occupied date is refused

- **WHEN** an entry dated `2025-10-12` is changed to `2025-10-13` and that date already has an entry
- **THEN** nothing is renamed or moved and the change is reported

#### Scenario: Processing onto an occupied date is refused

- **WHEN** a capture is processed into a log entry for a date that already has an entry
- **THEN** processing reports the conflict and leaves the capture in the inbox

### Requirement: The Log workspace shows a calendar and a collapsed date tree

The Log section SHALL show a month calendar and a year tree whose year rows start collapsed. The
calendar SHALL mark a day with entries using a tint and a dot, a month header with a month entry
using a dot, and the year heading with a year entry using a dot. The tree SHALL list entries at the
level their date names and SHALL include an Undated row when undated notes exist.

#### Scenario: A day with an entry is marked

- **WHEN** a month contains a log entry dated `2025-10-12`
- **THEN** the calendar tints and dots the 12th

#### Scenario: A month entry is marked on the header

- **WHEN** the month has an entry dated `2025-10`
- **THEN** the month header shows a dot

#### Scenario: A year entry is marked on the year heading

- **WHEN** the year has an entry dated `2025`
- **THEN** the year heading shows a dot

#### Scenario: Years start collapsed

- **WHEN** the Log section opens
- **THEN** every year row is collapsed and only the year rows and Undated are visible

#### Scenario: Entries sit at their date level

- **WHEN** the vault contains entries dated `2025`, `2025-10`, and `2025-10-12`
- **THEN** each appears under the year, month, and day node respectively

#### Scenario: Undated notes are listed

- **WHEN** a note has no `date`
- **THEN** the tree lists it under Undated

### Requirement: The Log date controls share one row

The Log section SHALL place **Today's Entry**, **Entries**, and **Everything** in one control row above the calendar. The controls SHALL use natural widths and SHALL wrap only when the browser cannot fit them in one row.

#### Scenario: Controls share a wide row

- **WHEN** the Log browser is wide enough for all three date controls
- **THEN** Today's Entry, Entries, and Everything appear in one row above the calendar

#### Scenario: Narrow browser wraps the controls

- **WHEN** the browser cannot fit the three date controls in one row
- **THEN** the controls wrap onto additional rows without horizontal scrolling

#### Scenario: Search hides the controls

- **WHEN** a non-empty search query is active
- **THEN** the Log date controls are not shown

### Requirement: The Log workspace switches between Entries and Everything

The Log section SHALL offer an **Entries** mode that shows only `type: log` notes and an
**Everything** mode that shows every parsed note by date. The selected mode SHALL be persisted per
vault as a user-interface preference and restored when the vault is opened again. A newly opened
vault SHALL start in Entries mode.

#### Scenario: Entries shows only log notes

- **WHEN** the Log is in Entries mode
- **THEN** projects, references, and captures are absent from the calendar and tree

#### Scenario: Everything shows every note

- **WHEN** the Log is in Everything mode
- **THEN** every parsed note appears at the level its date names

#### Scenario: The mode survives a restart

- **WHEN** the user selects Everything and reopens the vault
- **THEN** the Log opens in Everything mode

#### Scenario: A new vault starts in Entries

- **WHEN** a vault with no remembered mode is opened
- **THEN** the Log opens in Entries mode

### Requirement: The Log search filters the tree and the calendar

The Log SHALL apply the workspace search query to both the date tree and the calendar. Matching SHALL
use the same title, identity, body, step-text, and role-name rules as the rest of the browser. Days
without a match MUST NOT be accented while a query is active.

#### Scenario: Matching entries remain in the tree

- **WHEN** the user searches for `dentist` and one log entry contains that word
- **THEN** the tree lists only the matching entry

#### Scenario: Non-matching days lose their accent

- **WHEN** a search query matches only one entry
- **THEN** only that entry's day keeps its tint and dot

#### Scenario: An empty query restores the archive

- **WHEN** the user clears the search field
- **THEN** the full tree and every entry accent return

#### Scenario: A role name match names the project

- **WHEN** the Log is in Everything mode and a project's owner, requester, or step owner matches the
  query
- **THEN** the project is listed

### Requirement: Dated actions open log drafts

The Log SHALL open an unsaved log draft for **Today's entry**, an empty calendar day, and the plus on
an empty month or year row. Each draft SHALL use the action's date and open in edit mode without a
title or starter dialog. An occupied date SHALL open its existing entry in read mode instead. A day
with more than one entry SHALL expand in the date tree rather than open one entry.

#### Scenario: An empty day opens a draft

- **WHEN** the user clicks a calendar day with no entry
- **THEN** the editor opens an unsaved log draft for that day without a dialog

#### Scenario: Today's entry opens a draft

- **WHEN** today has no entry and the user chooses **Today's entry**
- **THEN** the editor opens an unsaved log draft for today

#### Scenario: A month plus opens a draft

- **WHEN** the user clicks the plus on an empty month row
- **THEN** the editor opens an unsaved log draft dated `YYYY-MM`

#### Scenario: A year plus opens a draft

- **WHEN** the user clicks the plus on an empty year row
- **THEN** the editor opens an unsaved log draft dated `YYYY`

#### Scenario: An occupied day opens read mode

- **WHEN** the user clicks a calendar day with one entry
- **THEN** that entry opens in read mode and no draft appears

#### Scenario: Today's entry opens an occupied date in read mode

- **WHEN** today has an entry and the user chooses **Today's entry**
- **THEN** the existing entry opens in read mode

#### Scenario: Several entries expand the tree

- **WHEN** the user clicks a calendar day with more than one entry
- **THEN** the day expands in the date tree and no entry opens

### Requirement: A new log entry has a default date title

A new log entry SHALL start with the long date of its action as its level-1 heading: a month name,
day, and year for a day, a month name and year for a month, and a year for a year. The heading SHALL
remain editable, and the filename SHALL remain the ISO date.

#### Scenario: A day draft gets a long date title

- **WHEN** the user opens a draft for `2026-11-13`
- **THEN** the draft heading is `November 13, 2026`

#### Scenario: A month draft gets a long date title

- **WHEN** the user opens a draft for `2026-11`
- **THEN** the draft heading is `November 2026`

#### Scenario: A year draft gets the year title

- **WHEN** the user opens a draft for `2026`
- **THEN** the draft heading is `2026`

#### Scenario: The default title is editable

- **WHEN** the user replaces the heading before the first write
- **THEN** the written entry uses the replacement heading

#### Scenario: The filename stays ISO

- **WHEN** an entry titled `November 13, 2026` is written
- **THEN** its filename is `2026-11-13.md`

### Requirement: Log cards provide only a starter body

A new log draft SHALL offer a Starter control that lists every valid `type: log` card and Empty.
Choosing a card SHALL supply only a starter body below the entry's heading; Empty SHALL leave only
the heading. The control MUST NOT supply a category, status, or date. It SHALL be available only
while the draft has no content beyond its generated heading and selected starter, and an existing
entry MUST NOT offer it.

#### Scenario: A card supplies the starter body

- **WHEN** the user chooses the Daily entry card in a new log draft
- **THEN** the body contains the title heading followed by the card's headings

#### Scenario: A card does not set the date

- **WHEN** the user chooses a log card for a draft dated `2025-10-12`
- **THEN** the date remains `2025-10-12`, not a value from the card

#### Scenario: Empty creates a bare entry

- **WHEN** the user chooses Empty in a new log draft
- **THEN** the body contains only the title heading

#### Scenario: An invalid card is reported

- **WHEN** a log card is malformed
- **THEN** the Starter control names the file and still lists the valid cards

#### Scenario: Selecting Empty removes a starter

- **WHEN** the user chooses a card and then Empty before adding content
- **THEN** the body returns to only the title heading

#### Scenario: The starter disappears after content

- **WHEN** the user types body text beyond the generated heading and selected starter
- **THEN** the Starter control is no longer available

#### Scenario: An existing entry has no starter

- **WHEN** an existing log entry is open
- **THEN** no Starter control appears

### Requirement: Viewing the Log performs no write

Opening the Log, switching its mode, expanding a date row, moving the calendar, searching, or
opening an entry SHALL NOT create, change, or remove a vault file. Only an explicit creation, date
change, edit, rename, or trash action SHALL write.

#### Scenario: Browsing makes no changes

- **WHEN** the user opens the Log, moves to another month, and expands a year
- **THEN** no note file is created, changed, or removed

#### Scenario: Search makes no changes

- **WHEN** the user types a query in the Log search field
- **THEN** no note file is created, changed, or removed

#### Scenario: Opening an entry is read-only

- **WHEN** the user clicks an entry in the tree
- **THEN** the page opens in read mode and the file is unchanged

### Requirement: Log entries are not renamed directly

The page for a log entry SHALL NOT offer the Rename action. Its date SHALL be changed through the
Date field, which performs the rename and move. The entry's level-1 heading SHALL be updated only
when it equals the generated date title for its old date, as defined by `note-identity`.

#### Scenario: Rename is absent

- **WHEN** a log entry is open
- **THEN** the page offers no Rename action

#### Scenario: A date change keeps the heading

- **WHEN** a log entry titled `A quiet Tuesday` is changed from `2025-10-12` to `2025-10-13`
- **THEN** the heading remains `A quiet Tuesday`

#### Scenario: Trash remains available

- **WHEN** a log entry is open
- **THEN** the page still offers the Trash action
