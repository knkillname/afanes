# date-entry Specification

## Purpose

A shared, localized, keyboard-accessible date entry and calendar dialog used by every date input in
the interface.

## Requirements

### Requirement: Every date input offers the shared calendar action

Every editable date field SHALL embed a calendar action, and every read-mode date action SHALL use
the same picker. The Page Date, Page Due, Processing due, Review postpone, and reminder one-shot
fields SHALL offer it, as SHALL the read-mode note date, project due date, and step plan.

#### Scenario: A date field opens the picker

- **WHEN** the user activates the calendar action on a date field
- **THEN** the shared picker opens with the field's current value

#### Scenario: A read-mode action opens the picker

- **WHEN** the user activates the note date, project due date, or step plan action
- **THEN** the shared picker opens with the current value

#### Scenario: Cancelling leaves the value unchanged

- **WHEN** the user cancels the picker
- **THEN** the field and the vault keep their previous value

#### Scenario: Typed ISO remains valid

- **WHEN** the user types a valid ISO date and leaves the field
- **THEN** the existing validation and save path runs without opening the picker

### Requirement: The picker returns a precision-aware note date

The picker SHALL return a `NoteDate` at day, month, or year precision. The Page Date SHALL allow all
three precisions; every other date input SHALL allow day precision only and SHALL hide the mode
switch. The field SHALL keep ISO text and its existing save and validation path.

#### Scenario: The Page Date writes each precision

- **WHEN** the user confirms an unchanged Page Date in Day, Month, or Year mode
- **THEN** the field receives `YYYY-MM-DD`, `YYYY-MM`, or `YYYY` respectively

#### Scenario: Day-only fields hide the mode switch

- **WHEN** the picker opens for the Due date, step plan, Processing due, Review postpone, or reminder
  one-shot date
- **THEN** the mode switch is absent and only day selection is available

#### Scenario: An empty or invalid current value opens Day mode

- **WHEN** the field is empty or its text is not a valid ISO date
- **THEN** the picker opens in Day mode with today selected

#### Scenario: A typed partial date remains valid

- **WHEN** the user types `YYYY` or `YYYY-MM` into the Page Date field
- **THEN** the existing note-model validation and save path accepts or rejects it without the picker

#### Scenario: The field command remains authoritative

- **WHEN** the user confirms a date in the picker
- **THEN** the field runs its existing save command and the picker does not write the vault directly

### Requirement: The picker dialog presents one calendar surface

The picker SHALL be a dialog with a title, a selected caption, a mode switch when more than one
precision is allowed, a Monday-first weekday row, a day grid, month and year navigation, and
current-period, Cancel, and Select actions. Select SHALL confirm; Cancel, Esc, and an outside click
SHALL discard.

#### Scenario: The selected caption names the pending value

- **WHEN** the picker is open
- **THEN** a caption shows the day, month, or year that Select will write

#### Scenario: Select confirms the pending value

- **WHEN** the user activates Select
- **THEN** the picker closes and the field receives the pending value

#### Scenario: Cancel, Esc, and an outside click discard

- **WHEN** the user chooses Cancel, presses Esc, or clicks outside the dialog
- **THEN** the picker closes without changing the field

#### Scenario: Initial focus reaches the selected cell

- **WHEN** the picker opens
- **THEN** focus is on the selected day, month, or year cell

#### Scenario: The dialog keeps the action order

- **WHEN** the picker shows its actions
- **THEN** Cancel appears before Select, Select names the operation, and the dialog closes on Esc

### Requirement: The Page Date picker preserves the day across precision modes

The Page Date picker SHALL start in the current value's precision. Changing modes SHALL keep the
anchor date. Selecting a different month or year SHALL keep the day-of-month, clamped to the month
length. Switching back to Day SHALL restore the preserved or clamped day. Select SHALL write the
mode's precision.

#### Scenario: Day to Month to Day round-trips

- **WHEN** the user opens `2026-11-14` in Day mode, switches to Month, and switches back without
  selecting a month
- **THEN** the day remains `2026-11-14`

#### Scenario: A short month clamps the day

- **WHEN** the user opens `2026-01-31` in Day mode, selects February in Month mode, and switches to
  Day
- **THEN** the selected day is the last day of February

#### Scenario: A leap day clamps in a common year

- **WHEN** the user opens `2028-02-29` and selects `2027` in Year mode, then switches to Day
- **THEN** the selected day is `2027-02-28`

#### Scenario: Select writes the mode's precision

- **WHEN** the user confirms a selection in Month or Year mode
- **THEN** the Page Date receives `YYYY-MM` or `YYYY`, not a day-precision value

### Requirement: The picker offers month and year grids

Month mode SHALL show a 3x4 grid of full localized month names for the visible year. Year mode SHALL
show a decade grid. The current-period action SHALL select today, the current month, or the current
year for the active mode. The picker SHALL support the full `datetime.date` range.

#### Scenario: Month mode shows the year's months

- **WHEN** the picker is in Month mode for 2026
- **THEN** it shows the twelve month names in the active language and the selected month

#### Scenario: Year mode shows a decade

- **WHEN** the picker is in Year mode
- **THEN** it shows a decade page of years and the selected year

#### Scenario: The current-period action follows the mode

- **WHEN** the user activates the current-period action in Day, Month, or Year mode
- **THEN** today, the current month, or the current year is selected respectively

#### Scenario: The full date range is available

- **WHEN** the user navigates to a year before 1900 or after 2100
- **THEN** the picker still selects that calendar date

### Requirement: The picker is keyboard accessible

The picker SHALL place initial focus on the selected day, month, or year. Tab SHALL reach the mode
switch, header, grid, and actions. Enter SHALL confirm a focused grid cell. Esc SHALL cancel the
dialog.

#### Scenario: Initial focus is on the selection

- **WHEN** the picker opens
- **THEN** the selected cell holds focus

#### Scenario: Tab reaches the controls

- **WHEN** the user presses Tab from the grid
- **THEN** focus reaches the mode switch, header, grid, and actions in order without trapping

#### Scenario: Enter confirms a grid cell

- **WHEN** a day, month, or year cell has focus and the user presses Enter
- **THEN** the pending value is confirmed and the picker closes

#### Scenario: Esc cancels the dialog

- **WHEN** the user presses Esc
- **THEN** the picker closes without changing the field

### Requirement: The picker keyboard moves by precision

In Day mode, arrows SHALL move by day and week, PageUp/PageDown by month, and Home/End to the week
boundary. In Month mode, arrows SHALL move by month and row, PageUp/PageDown by year, and Home/End
to January/December. In Year mode, arrows SHALL move by year and row, PageUp/PageDown by decade, and
Home/End to the page ends.

#### Scenario: Day mode moves by day and month

- **WHEN** the picker is in Day mode and the user presses Right, Down, PageDown, or End
- **THEN** the selection moves by one day, one week, one month, or to the week end

#### Scenario: Month mode moves by month and year

- **WHEN** the picker is in Month mode and the user presses Right, Down, PageDown, or Home
- **THEN** the selection moves by one month, one row, one year, or to January

#### Scenario: Year mode moves by year and decade

- **WHEN** the picker is in Year mode and the user presses Right, Down, PageDown, or End
- **THEN** the selection moves by one year, one row, one decade, or to the page end

#### Scenario: Focus follows the moved selection

- **WHEN** a key moves the selection across a month or year boundary
- **THEN** the visible period changes and focus moves to the selected cell

### Requirement: The picker is localized and Monday-first

The picker SHALL render month names, weekday labels, the selected caption, the mode switch, the
current-period action, and navigation controls in the active locale. The calendar SHALL be
Monday-first in both languages. The chosen `NoteDate` SHALL be locale-independent.

#### Scenario: English labels

- **WHEN** the picker opens under English
- **THEN** its month names, weekday labels, mode switch, caption, current-period action, and
  navigation controls are English

#### Scenario: Spanish labels

- **WHEN** the picker opens under Spanish
- **THEN** its month names, weekday labels, mode switch, caption, current-period action, and
  navigation controls are Spanish

#### Scenario: Both locales start on Monday

- **WHEN** the picker opens in either locale
- **THEN** the weekday row starts with Monday and ends with Sunday

#### Scenario: The chosen value is locale-independent

- **WHEN** the user chooses the same calendar date under either locale
- **THEN** the same `NoteDate` text and precision are returned

### Requirement: The picker follows the visual standard and stays offline

The picker SHALL use interface tokens, the neutral selected-row fill for the selected cell, accent
text and a bold weight for today, the accent ring for focus, and an outlined Select action. It SHALL
add no conformance baseline entry, no network call, and no operating-system notification. The dialog
SHALL be recorded as the bounded dialog-versus-popover difference.

#### Scenario: Values come from the tokens

- **WHEN** the picker renders
- **THEN** its colors, spacing, radii, sizes, and widths come from the interface token module

#### Scenario: Selection, today, and focus do not rely on hue

- **WHEN** the selected day, today, and a focused day are shown
- **THEN** selection uses the neutral selected-row fill, today uses accent text and a bold weight,
  and focus uses the accent ring

#### Scenario: The baseline does not grow

- **WHEN** the conformance gate runs
- **THEN** the new components add no baseline entry and any removed literals delete a stale entry

#### Scenario: The difference is recorded

- **WHEN** the interface standard lists bounded differences
- **THEN** it records the date-picker dialog that stands in for an anchored calendar popover

#### Scenario: The picker stays offline

- **WHEN** the picker opens, navigates, or confirms a date
- **THEN** it makes no network request and requests no operating-system notification

### Requirement: The picker changes no vault file until confirmed

Opening, navigating, switching modes, and cancelling SHALL write nothing. Select SHALL run the
field's existing command. A failed command SHALL leave the field and vault unchanged.

#### Scenario: Browsing writes nothing

- **WHEN** the user opens the picker, changes months or years, and switches modes
- **THEN** no vault file is created, changed, or removed

#### Scenario: Cancelling writes nothing

- **WHEN** the user cancels the picker
- **THEN** no vault file is created, changed, or removed

#### Scenario: Confirming runs the field command

- **WHEN** the user activates Select
- **THEN** the field runs its own save command with the chosen value

#### Scenario: A failed command keeps the old value

- **WHEN** the field's save command fails after Select
- **THEN** the field and the vault keep their previous value and the failure is reported
