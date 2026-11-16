# Design

## Context

See `proposal.md` — Why. The current `AppShell.pick_date` wraps Flet's Material `DatePicker` and
reaches only the read-mode project due date and the step plan. The Page Date, Due date in edit mode,
Processing due date, Review postpone, and reminder one-shot fields are typed ISO only. The read-mode
note date action is specified but missing.

The existing Log calendar already has a localized, Monday-first month grid. `NoteDate` already
models day, month, and year precision. `FormFieldControl.suffix` accepts an embedded control, so a
calendar action can sit inside a date field. The interface and copy gates bound the visual values and
copy. Flet exposes no anchored popover or anchor geometry; `AlertDialog` is the available focused
surface.

## Goals / Non-Goals

**Goals:**

- One shared date entry and calendar dialog for every date field and read-mode date action.
- Exact Monday-first localization and a visual language that matches the Log calendar.
- Day, month, and year selection where the domain supports it, with the day preserved across mode
  changes.
- Keyboard access, full `datetime.date` range, no new dependency, no new conformance baseline entry.
- Keep every existing save, validation, rename, and move path authoritative.

**Non-Goals:**

- A time picker; the reminder time stays typed.
- Month or year precision for due dates, step plans, processing, review, or reminders.
- Localized display inside the text fields; the fields keep ISO.
- A clear suffix inside date fields; the existing edit paths clear values.
- An anchored popover; the dialog is the recorded Flet difference.

## Decisions

### D1: Replace the Material `DatePicker` with a custom Adwaita dialog

The picker becomes a custom `AlertDialog` built from the app's own calendar, because the Material
picker derives morning/day order and labels from Flutter's locale. It cannot guarantee Monday-first
in English, and it does not use `LocaleFormat`.

Alternatives considered:

- **Theme the Material picker.** Rejected: colors and copy can be themed, but the first weekday and
  month/weekday labels remain Flutter's.
- **Inline calendar panel.** Rejected: it pushes forms down, complicates focus and multiple open
  panels, and still is not an anchored popover.
- **Keep the Material picker for day-only fields.** Rejected: two calendar idioms and two
  localization sources would remain.

The dialog is a bounded difference independent of the week-start problem; the interface standard
records it.

### D2: Extract `CalendarGrid` from `LogCalendar`

`ui/components/calendar.py` gains a presentational `CalendarGrid` that renders the Monday-first
weekday row and the day grid from a `CalendarMonth`. It accepts optional `selected` and `today`
dates, an optional day tooltip callback, and a `key` prefix. `LogCalendar` keeps its title, entry
marks, and month navigation, and delegates its weekday row and grid to `CalendarGrid`.

Alternatives considered:

- **Use `LogCalendar` directly.** Rejected: it has no selection styling, year navigation, or
  picker-specific day labels.
- **Duplicate the grid in the picker.** Rejected: two sources of truth for the one calendar layout.

The existing `LogCalendar` tests keep their `title`, `weekdays`, `day_buttons`, and `grid` surface
through aliases, so the refactor is behavior-preserving.

### D3: Use `NoteDate` as the picker value; keep a day-only wrapper

The picker returns `NoteDate | None`. The existing day-only API stays:

```text
AppShell.pick_note_date(current: NoteDate | None, precisions: frozenset[DatePrecision]) -> NoteDate | None
AppShell.pick_date(current: date | None) -> date | None
```

`pick_date` converts the current day to `NoteDate.from_date`, calls `pick_note_date` with `{DAY}`,
and converts the result back to a `date`. It preserves every existing day-only call site and test.
The new action is added as a trailing optional field to the action dataclasses and as a keyword-only
parameter to the views, so existing positional constructors keep working.

Alternatives considered:

- **One `NoteDate` API for every caller.** Rejected: every day-only view would carry precision
  knowledge it does not need, and the existing `ProjectBodyView`/read-mode due APIs would churn.
- **Two dialogs.** Rejected: duplicated calendar, keyboard, and copy behavior.

### D4: Precision-aware Page Date, day-only elsewhere

Only the Page Date field and the read-mode note date action allow all three precisions. The Due date,
step plan, Processing due, Review postpone, and reminder one-shot date pass `{DAY}`; the dialog hides
the mode switch. This follows the domain: a due date, plan, or reminder instant has no month/year
form.

The Page Date picker starts in the current value's precision. Empty or invalid values start in Day
mode with today selected.

### D5: Preserve the day with clamping

The dialog keeps a concrete **anchor date** and a current precision. Changing modes keeps the anchor;
selecting a different month or year changes only that part and clamps the day to the month length.
Switching back to Day restores the preserved or clamped day. Select writes the current precision.

Alternatives considered:

- **Reset to the first of the period.** Rejected: it loses the day on a simple mode round-trip.
- **Preserve only while the period is unchanged.** Rejected: two rules to learn for the same gesture.

A small clamp helper uses `calendar.monthrange`; the anchor is a `datetime.date`, so the leap-day
behavior is explicit and testable.

### D6: A custom mode switch and period grids

The mode switch is a three-button segmented control (`Day`, `Month`, `Year`) with the neutral
selected-row fill, not a Material `SegmentedButton`. Month mode is a 3x4 grid of full localized month
names. Year mode is a 5x2 decade page. The current-period action changes with the mode: `Today`,
`This Month`, `This Year`.

Alternatives considered:

- **Material `SegmentedButton`.** Rejected: another Material idiom in an explicitly Adwaita control.
- **A year dropdown.** Rejected: a long menu and a keyboard/focus conflict with the grid.
- **Year page as 12 years.** Rejected: decade pages align with the reference's date language and
  fit the dialog width more comfortably.

### D7: Confirm with Select; no immediate close

A day, month, or year click updates the selection and the caption; **Select** confirms. Cancel, Esc,
and an outside click discard. This is safer than a popover-style immediate close because a log date
change renames and moves the file immediately.

The Select action is an `OutlinedButton`. A new class with a `FilledButton` would add a conformance
baseline entry, which the ratchet forbids; the reminder editor already uses an outlined primary
action.

### D8: Keyboard and focus tracking at the AppShell boundary

Flet exposes only `Page.on_keyboard_event`, with no focused-control target. `AppShell` owns the
dialog and routes keys while it is open:

- Day mode: arrows by day/week, PageUp/PageDown by month, Shift+PageUp/PageDown by year, Home/End to
  the week boundary.
- Month mode: arrows by month/row, PageUp/PageDown by year, Home/End to January/December.
- Year mode: arrows by year/row, PageUp/PageDown by decade, Home/End to the page ends.
- Esc cancels; Enter confirms only while a grid cell is focused.

The dialog tracks whether a grid cell has focus through the cells' `on_focus`/`on_blur`. The mode
switch, header, and actions clear that flag, so Enter on those controls performs their own action.
Tab reaches the mode switch, header, grid, and actions; arrows are the primary movement, so a
31-tab walk is not required.

### D9: Field integration and write ownership

`DatePickerActions` carries two view methods: `pick()` returning `NoteDate | None`, and
`on_picked(NoteDate)`. `DatePickerButton` renders the embedded `IconButton` and calls those methods.
The view owns parsing, the precision policy, and the write.

This keeps `core` and the vault out of the picker. The field keeps its existing validation and
command:

| Surface | Precision | Field current | On picked |
|---|---|---|---|
| Page Date edit | day/month/year | `NoteDate.from_text` | write text, commit |
| Page Due edit | day | `date.fromisoformat` | write text, save due |
| Page note read | day/month/year | labels or `NoteDate` | write text, commit |
| Page due read | day | due date | save due |
| Step plan | day | plan date | step edit |
| Processing due | day | field date | write text, invalidate plan |
| Review postpone | day | `_typed` | write `_typed`, refresh |
| Reminder one-shot | day | date part | write date, preserve time |

Day-only views wrap `pick_date` into a day `NoteDate`; the Page Date and read-mode note date call
`pick_note_date` directly.

### D10: Add the read-mode note date action

`PageView` adds a calendar `IconButton` beside `meta_date`, with **Add Date…** when the date is
missing and **Change Date…** when present. It opens `pick_note_date` with all precisions and writes
through the existing `commit_date` path, so a log date still renames and moves the entry. The
read-mode due date action keeps its day-only `pick_date` path; its edit field gets the shared
`DatePickerButton`.

### D11: Localization, copy, and tokens

- Month names, weekday labels, and the selected caption come from `LocaleFormat` and `log_title`;
  Monday-first is a property of the shared grid.
- The title, open tooltip, mode labels, selected caption, current-period action, navigation tooltips,
  Select, and Cancel come from `UiCopy`.
- The selected day uses the neutral selected-row fill; today uses accent text and a bold weight;
  focus uses the accent ring. Today deliberately has no contour, so the blue contour always means
  focus and moves with the clicked or tabbed cell.
- `Date and time` becomes a sentence-case field label; **Change Due Date…** joins **Add Due Date…**;
  the stale `2025` hint becomes a format hint.
- New dimensions live in `theme.py`; no literal enters a view or component.
- The baseline does not grow. The `CalendarGrid` refactor may remove literals from
  `components/calendar.py`; those baseline counts are deleted in the same change.
- The interface standard gains the sixth bounded difference and the date-entry control pattern.

### D12: No new dependency, no data migration

The change uses Flet, `datetime`, and `calendar` only. There is no schema, vault-format, CLI, or
network change. The Material `DatePicker` disappears from the interface; the `pick_date` signature
survives. The release is MINOR; rollback is a code revert, not a data operation.

## Architecture

### Component map

```text
+---------------------------+          +----------------------------+
| LogCalendar (browser)     |          | DatePickerDialog (dialog)  |
|  header: month + marks    |          |  title + caption           |
|  +---------------------+  |          |  mode switch               |
|  | CalendarGrid        |<-+----------+-> header + day/month/year |
|  +---------------------+  |  shared  |  actions                   |
+---------------------------+          +----------------------------+
                                                    ^
                                                    |
                                       AppShell.pick_note_date()
                                                    ^
                                                    |
+---------------------------+          +----------------------------+
| DatePickerButton          |          | Read-mode date actions     |
|  field.suffix             |          |  note date, due, step plan |
+---------------------------+          +----------------------------+
```

### Core calendar helper

`core/log.py` gains `CalendarMonth.for_month(year, month)`, which builds a zero-count month with
`calendar.monthrange` and `CalendarDay(day=..., count=0)` cells. The picker uses it; the Log timeline
keeps its count-building path. This avoids duplicating month layout in the UI and keeps date math out
of the dialog.

### Dialog state

- `_anchor: datetime.date` — the selected date, including the hidden day used across modes.
- `_precision: DatePrecision` — the mode and the output precision.
- `_visible_year`, `_visible_month` — the rendered month grid.
- `_grid_focused: bool` — whether Enter should confirm.
- `_today: datetime.date` — a plain value, injectable for tests.
- `_first_date`, `_last_date` — `date.min`/`date.max` by default.

Selecting a day writes the anchor. Selecting a month or year changes that part and clamps the day.
Switching precision keeps the anchor. The current-period action sets the anchor to today and moves
the visible period; the caption always renders the anchor at the current precision.

### Keyboard map

| Mode | Arrows | PageUp/PageDown | Home/End | Enter |
|---|---|---|---|---|
| Day | day / week | month | week | confirm |
| Month | month / row | year | January / December | confirm |
| Year | year / row | decade | page ends | confirm |

Esc cancels in every mode. Tab moves between the mode switch, header, grid, and actions without a
focus trap.

### Error and edge behavior

- Empty or invalid current values open Day mode with today.
- A missing date does not block the picker; the Page Date field remains optional.
- A malformed typed date still shows the existing inline warning and blocks the save.
- A failed save after Select leaves the field and vault unchanged and uses the existing error path.
- Cancelling or clicking outside writes nothing.
- Dates before 1900 and after 2100 are selectable; the year grid pages and the header arrows clamp
  at `date.min`/`date.max`.

## Migration Plan

1. Add the shared grid, dialog, field action, and copy behind the existing `pick_date` seam.
2. Add `pick_note_date` and route the Page Date and read-mode note date through it.
3. Add the embedded field actions to the Page Due, Processing, Review, and reminder views.
4. Replace the Material `DatePicker` in `AppShell`; remove its test-only assumptions.
5. Add the view/read-mode tests, then the keyboard and localization tests.
6. Update the interface standard, guide pages, reference pages, and changelog at archive time.
7. Run the conformance, copy, architecture, type, test, and documentation gates.

No data or schema rollback is required. If the custom dialog is reverted, the existing `pick_date`
call sites keep their signatures, but the Material picker would reintroduce the Monday-first and
locale-label deviation.

## Risks / Trade-offs

- **Focus tracking is a workaround.** Flet exposes no focused-control target; the grid-cell
  `on_focus`/`on_blur` flag is the mechanism. Mitigation: cover Enter on the grid, mode switch, and
  Select in unit tests and a manual keyboard pass.
- **Tab order across a 31-day grid.** Mitigation: arrows are the primary movement; the actions remain
  reachable and Enter confirms from a cell. Verify with the manual check.
- **Large text can clip fixed cells.** Mitigation: use tokenized minimum heights, let the dialog
  scroll, and check the 1024x600 and large-text cases.
- **Spanish month names can be wide.** Mitigation: a three-column month grid and a tokenized dialog
  width; verify both locales.
- **The shared calendar refactor can regress the Log browser.** Mitigation: keep the existing
  `LogCalendar` surface and run its full test module.
- **The Page Date picker can change a log entry's precision accidentally.** Mitigation: the selected
  caption and the explicit Select confirmation; the existing rename/move error path stays.
- **The Page Date field can commit twice when its blur fires before the picker opens.** Mitigation:
  both commits run the same idempotent date command; the second is the chosen value; tests cover the
  field/picker path.
- **Review rebuilds its form after a pick.** Mitigation: the picker writes `_typed`, then refreshes;
  the new field shows the chosen day and the submit state updates.
- **The reminder field is a combined date/time string.** Mitigation: preserve the parsed time when
  the date changes; default to the editor's `09:00` when the time is invalid or absent.
- **The conformance baseline could grow.** Mitigation: tokens in every new control, an outlined
  Select, and delete stale baseline entries from the calendar refactor.
- **The full `datetime.date` range can expose year-1 layout and validation edges.** Mitigation: test
  the minimum and maximum years and the year-grid page boundaries.

## Open Questions

None. The year page is a decade (5x2), the month page is 3x4, and Select is the affirmative action;
the remaining values are token and copy choices settled during implementation.
