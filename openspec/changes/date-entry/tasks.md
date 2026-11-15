# Tasks

## 1. Shared calendar grid

- [x] 1.1 Add `CalendarMonth.for_month(year, month)` to `src/afanes/core/log.py` and cover it in `tests/core/test_log.py`; verify `hatch test tests/core/test_log.py`.
- [x] 1.2 Extract `CalendarGrid` from `LogCalendar` in `src/afanes/ui/components/calendar.py`, with optional selected and today dates, a day-tooltip callback, and a key prefix; keep the existing `LogCalendar` aliases; verify `hatch test tests/ui/test_calendar.py`.
- [x] 1.3 Add selection, today, focus, and tooltip coverage for `CalendarGrid` in `tests/ui/test_calendar.py`; verify the Log calendar tests still pass.
- [x] 1.4 Move the new grid dimensions into `src/afanes/ui/theme.py` and delete stale conformance baseline counts from `tests/ui/test_conformance.py`; verify `hatch test tests/ui/test_conformance.py`.

## 2. Date entry dialog and field action

- [x] 2.1 Add the date-entry copy to `src/afanes/i18n/ui/en.py` and the Spanish `.po` catalogs, declare each constant in the copy-gate sets, and include the open tooltip in the ellipsis set; verify `hatch run i18n-compile` and `hatch test tests/i18n/test_copy.py`.
- [x] 2.2 Add `src/afanes/ui/components/date_entry.py` with the dialog shell, selected caption, mode switch, day/month/year grids, current-period action, and Cancel/Select actions; verify the new shell and caption tests in `tests/ui/test_date_entry.py`.
- [x] 2.3 Implement the anchor date, precision policy, initial mode, day preservation with clamping, and `NoteDate` output; verify the mode, round-trip, short-month, leap-day, and precision tests in `tests/ui/test_date_entry.py`.
- [x] 2.4 Implement the keyboard and focus model: arrows, PageUp/PageDown, Shift+PageUp/PageDown, Home/End, Enter on a focused cell, Esc, Tab, and focus following the selection; verify the keyboard tests in `tests/ui/test_date_entry.py`.
- [x] 2.5 Add `DatePickerActions` and `DatePickerButton` and attach the button to a text field suffix; verify the pick, cancel, focus, and callback tests in `tests/ui/test_date_entry.py`.
- [x] 2.6 Add localization and full-range coverage for the dialog, including both locales, Monday-first, the selected caption, and the minimum/maximum years; verify `hatch test tests/ui/test_date_entry.py`.
- [x] 2.7 Add the date-entry dimensions and colour tokens to `src/afanes/ui/theme.py`, style the selected/today/focus states, and confirm the conformance baseline does not grow; verify `hatch test tests/ui/test_conformance.py`.
- [x] 2.8 Add `docs/guide/dates.md`, link it from `docs/index.md`, and update `docs/develop/interface-standard.md` with the date-entry pattern and the sixth bounded difference; verify `hatch run docs:build`.

## 3. Application picker API

- [x] 3.1 Replace the Material `ft.DatePicker` in `src/afanes/ui/app.py` with `pick_note_date`, add the day-only `pick_date` wrapper, store the open dialog, route keyboard events, and remove the old picker; verify the updated picker, wrapper, cancel, and keyboard tests in `tests/ui/test_app.py`.
- [x] 3.2 Add `pick_note_date` as a trailing optional field to `WorkspaceActions` and `PageActions`, pass it through `WorkspaceView`, and keep `pick_date` for day-only surfaces; verify the app and workspace wiring tests.

## 4. Page, read-mode dates, and Log

- [x] 4.1 Add the Page Date and Due date field actions, the read-mode note date add/change action, and the Add/Change Due Date tooltip; use `pick_note_date` for the Page Date and `pick_date` elsewhere; verify `tests/ui/test_page_view.py` and `tests/ui/test_workspace_view.py`.
- [x] 4.2 Add Log precision coverage for day, month, and year selections, including the folder move, generated heading, custom heading, and typed ISO paths; verify `hatch test tests/ui/test_page_view.py tests/ui/test_workspace_view.py`.
- [x] 4.3 Update `docs/guide/pages-and-editing.md`, `docs/guide/log.md`, `docs/guide/projects-and-steps.md`, `docs/reference/frontmatter.md`, and `docs/reference/step-metadata.md` for the picker, precision, read-mode actions, and step plan; verify `hatch run docs:build`.

## 5. Processing

- [x] 5.1 Add the day-only picker to the Processing due date field, with field parsing, plan invalidation, and cancel behaviour; verify `hatch test tests/ui/test_processing_view.py`.
- [x] 5.2 Update `docs/guide/processing.md` for the due date picker and ISO path; verify `hatch run docs:build`.

## 6. Review

- [x] 6.1 Add the day-only picker to the Review postpone form, with `_typed` updates and submit-state refresh; verify `hatch test tests/ui/test_review_view.py`.
- [x] 6.2 Update `docs/guide/review.md` for the postpone picker; verify `hatch run docs:build`.

## 7. Reminders

- [x] 7.1 Add the day-only picker to the reminder one-shot date portion and preserve the typed time; verify `hatch test tests/ui/test_reminder_editor.py`.
- [x] 7.2 Change `REMINDER_ONCE_LABEL` to `Date and time`, move it to the sentence-case set, update the Spanish catalog, and recompile; verify `hatch test tests/i18n/test_copy.py`.
- [x] 7.3 Update the reminder guidance in `docs/guide/pages-and-editing.md` and `docs/reference/frontmatter.md` for the one-shot picker and time; verify `hatch run docs:build`.

## 8. Integration and gates

- [x] 8.1 Run `hatch check` and fix every lint, format, or strict type diagnostic; verify 0 diagnostics.
- [x] 8.2 Run `hatch test --cover` and verify the suite passes with coverage at or above 85%.
- [x] 8.3 Run `openspec validate --all --strict` and `openspec doctor`, then the vocabulary greps, `git diff --check`, and the no-tracked-`.mo` check; verify every command passes.
- [ ] 8.4 Run `hatch run docs:build`; verify the documentation builds with warnings as errors.
- [ ] 8.5 Run the manual check under English and Spanish: Page Date day/month/year and clamping, read-mode note date, Log month/year move, Due date, step plan, Processing, Review postpone, reminder one-shot time preservation, keyboard navigation, cancel, the 1024x600 window, large text, the full date range, and no operating-system notification; record the version, date, machine, and result in `RELEASE.md`.

## Workflow follow-up

- Archive the change after the project review requirements and the manual check are satisfied.
- Complete the post-archive release in `AGENTS.md` section 5.3, including the MINOR bump, changelog, README/docs status, gates, and the archive release commit.
- Do not tag, push, or publish unless asked.
