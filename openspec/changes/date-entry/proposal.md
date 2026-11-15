# Proposal

## Why

Date entry is inconsistent. Five date fields — the Page Date, the project Due date in edit mode,
Processing due date, Review postpone, and the reminder one-shot date — accept only typed ISO text.
Only the read-mode project due date and the step plan open Flet's Material `DatePicker`, which is
unthemed, uses Flutter's locale labels, and cannot guarantee the project's Monday-first rule in
English. The Log guide already promises a Date-field picker, and the read-mode note date's specified
add-date action is missing.

The result is one of the most common inputs in the application behaving differently depending on
where it appears, with a picker that cannot meet the interface standard.

## What Changes

- Add a shared `date-entry` control: a text field with an embedded calendar action and a custom
  Adwaita-style calendar dialog. Replace the Material `DatePicker`.
- Make the Page Date picker precision-aware: Day, Month, and Year modes, month and year grids, a
  selected caption, and day preservation with clamping across mode changes. Support the full
  `datetime.date` range instead of 1900–2100.
- Keep the Page Due, step plan, Processing due, Review postpone, and reminder one-shot date
  day-only; hide the mode switch there. The reminder time remains typed.
- Add the read-mode note date calendar action (**Add Date…** / **Change Date…**) and route the
  existing read-mode due date and step plan actions through the shared picker.
- Keyboard support: arrows by day, month, or year; PageUp/PageDown; Home/End; Enter to confirm a
  focused grid cell; Esc to cancel; Tab through the mode switch, header, grid, and actions. Initial
  focus goes to the selected cell.
- Localization: month names, weekday labels, the selected caption, the mode switch, and the
  current-period action follow the active locale; the calendar is Monday-first in both languages;
  the chosen date is locale-independent.
- Theme: tokens only, neutral selected day, accent today and focus, and an outlined **Select**
  action. No new conformance baseline entries.
- Record the picker dialog as a bounded difference: Flet exposes no anchored popover or anchor
  geometry, so the calendar is a dialog rather than a reference popover.
- Keep ISO in the fields; typed ISO remains valid. The picker only supplies a value; the existing
  validation, save, rename, and move paths stay authoritative.
- Small related copy fixes: **Date and time** as a field label, **Add/Change Due Date…** for the
  project action, and a format hint instead of a stale year.

## Capabilities

### New Capabilities

- `date-entry`: The shared date field action, calendar dialog, precision modes, keyboard model,
  localization, theming, and the contract that the picker supplies a value while the field keeps its
  existing write path.

### Modified Capabilities

- `note-editing`: The Date and Due date fields gain the shared calendar action; Date is
  precision-aware; Due is day-only; the read-mode note date gains its calendar action; the read-mode
  due and step plan actions use the shared picker.
- `note-log`: The log Date field opens the precision-aware picker; a month or year selection renames
  and moves the entry through the existing date path.
- `processing`: The optional project due date offers the day-only picker.
- `guided-review`: The postpone form offers the day-only picker.
- `note-reminders`: The one-shot date offers the day-only picker and preserves the typed time.
- `interface-theme`: The bounded-difference list gains the date-picker dialog that stands in for an
  anchored calendar popover.
- `interface-localization`: The native-picker requirement becomes the shared custom date picker;
  its month and weekday labels, mode switch, caption, current-period action, and controls follow the
  active locale and remain Monday-first.

## Impact

- New `src/afanes/ui/components/date_entry.py` and a `CalendarGrid` extraction from
  `ui/components/calendar.py`.
- `ui/app.py`: a `pick_note_date` dialog core and a `pick_date` day-only wrapper, plus keyboard
  routing.
- `ui/views/workspace.py`, `ui/views/page.py`, `ui/views/project_body.py`,
  `ui/views/processing.py`, `ui/views/review.py`, and `ui/components/reminder.py`.
- `i18n/ui/en.py` and the Spanish `.po` catalogs; compiled `.mo` files remain build artifacts.
- `ui/theme.py` tokens; no new dependency and no network access.
- Tests for the shared grid, dialog, mode switch and clamping, keyboard model, every date surface,
  localization, copy, and conformance.
- Documentation for the date-entry guide section, Log, pages and editing, projects and steps,
  processing, review, reminders, frontmatter, and the interface standard.
- No public API removal: the existing `AppShell.pick_date` signature remains, `pick_note_date` is
  additive, and the new view constructor parameters are optional keywords. The Material picker is
  removed from the interface.
