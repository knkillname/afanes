# Spec Delta

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Log entries are created from dated actions

**Reason**: The title-and-card dialog is replaced by a direct draft opened from each dated action.

**Migration**: An empty calendar day, **Today's entry**, and the plus on an empty month or year row
open an unsaved log draft. An occupied date opens its existing entry in read mode. The Starter
control in the draft replaces the dialog's card choice.

## ADDED Requirements

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
