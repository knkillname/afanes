# note-log Specification

## Purpose

Defines the log note type, its one-entry-per-date rule, and the Log workspace that presents dated
entries through a calendar and a collapsible year/month/day tree.

## Requirements

### Requirement: A log note is a dated entry

A note whose `type` is `log` SHALL carry an optional ISO `date`, a body, and a display title from its
first level-1 heading. It MUST NOT carry `category`, `status`, `due_date`, or `asked_by`. A log note
without a date SHALL remain readable and SHALL appear in the Undated group rather than being
reported as a parse failure.

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
use the same title, identity, body, and step-text rules as the rest of the browser. Days without a
match MUST NOT be accented while a query is active.

#### Scenario: Matching entries remain in the tree

- **WHEN** the user searches for `dentist` and one log entry contains that word
- **THEN** the tree lists only the matching entry

#### Scenario: Non-matching days lose their accent

- **WHEN** a search query matches only one entry
- **THEN** only that entry's day keeps its tint and dot

#### Scenario: An empty query restores the archive

- **WHEN** the user clears the search field
- **THEN** the full tree and every entry accent return

### Requirement: Log entries are created from dated actions

The Log SHALL offer **Today's entry**, creation from an empty calendar day, and a plus control on an
empty month or year row. Each action SHALL ask for a title and a log card or Empty, SHALL write the
entry with the action's date, and SHALL open it in edit mode. A blank title SHALL be rejected.

#### Scenario: Today's entry creates today's page

- **WHEN** today has no entry and the user chooses **Today's entry**
- **THEN** the dialog asks for a title and a card, and the page is written with today's date

#### Scenario: An empty day creates an entry

- **WHEN** the user clicks a calendar day with no entry
- **THEN** the dialog asks for a title and a card, and the page is written for that day

#### Scenario: An occupied day opens its entry

- **WHEN** the user clicks a calendar day with one entry
- **THEN** that entry opens and no dialog appears

#### Scenario: A month plus creates a month entry

- **WHEN** the user clicks the plus on an empty month row
- **THEN** the dialog writes an entry dated `YYYY-MM`

#### Scenario: A year plus creates a year entry

- **WHEN** the user clicks the plus on an empty year row
- **THEN** the dialog writes an entry dated `YYYY`

#### Scenario: A blank title is rejected

- **WHEN** the user submits a blank title
- **THEN** no entry is written and the dialog reports that a title is required

### Requirement: Log cards provide only a starter body

The log creation dialog SHALL list every valid `type: log` card and Empty. A card SHALL supply only a
starter body below the entry's heading; it MUST NOT supply a category, status, or date. Empty SHALL
create a log entry with no starter body.

#### Scenario: A card supplies the starter body

- **WHEN** the user creates an entry from the Daily entry card
- **THEN** the body contains the title heading followed by the card's headings

#### Scenario: A card does not set the date

- **WHEN** an entry is created from a log card for a chosen day
- **THEN** the date is the chosen day, not a value from the card

#### Scenario: Empty creates a bare entry

- **WHEN** the user chooses Empty
- **THEN** the body contains only the title heading

#### Scenario: An invalid card is reported

- **WHEN** a log card is malformed
- **THEN** the dialog names the file and lists the valid cards

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
Date field, which performs the rename and move. The entry's level-1 heading SHALL NOT be rewritten by
a date change.

#### Scenario: Rename is absent

- **WHEN** a log entry is open
- **THEN** the page offers no Rename action

#### Scenario: A date change keeps the heading

- **WHEN** a log entry titled `A quiet Tuesday` is changed from `2025-10-12` to `2025-10-13`
- **THEN** the heading remains `A quiet Tuesday`

#### Scenario: Trash remains available

- **WHEN** a log entry is open
- **THEN** the page still offers the Trash action
