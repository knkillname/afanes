# Tasks

## 1. Foundation, dependencies, and architecture headroom

- [ ] 1.1 Extract `VaultNote`, `NoteOrder`, `InboxOrder`, and `VaultPath` from `core/vault/snapshot.py` into `core/vault/note.py`; update imports without behavior changes; verify `hatch test tests/core/test_architecture.py tests/core/vault` and the line ceilings.
- [ ] 1.2 Add `tzdata>=2026.6,<2027` and `tzlocal>=5.4.5,<6` to `pyproject.toml` and the floor matrix; verify `hatch env create` and a test that `ZoneInfo("America/Mexico_City")` and `tzlocal.get_localzone_name()` resolve.
- [ ] 1.3 Document the new dependencies and module layout in `docs/develop/setup.md` and `docs/develop/architecture.md`; verify the pages describe offline, cross-platform behavior and the existing DAG.

## 2. Reminder model and recurrence

- [ ] 2.1 Add `models/reminder.py` with `Weekday`, `ClockTime`, `ReminderKind`, `Recurrence`, `OneShot`, and `Reminder`; verify strict docstrings and a pure-model import test.
- [ ] 2.2 Implement mapping parse and serialization for the six recurrence kinds and the one-shot form, preserving unknown nested keys; verify round-trip tests for every kind.
- [ ] 2.3 Implement `latest_occurrence`, `next_occurrence`, and `due_occurrence` on the reminder value objects; verify unit tests for daily, weekdays, month-day, nth-weekday, last-day, last-weekday, and one-shot schedules.
- [ ] 2.4 Add Hypothesis property tests for occurrence bounds, sorted unique times, month skips, nth-weekday bounds, and the latest-occurrence rule; verify the property suite.
- [ ] 2.5 Add deterministic regression tests for DST gap and repeated hour, a month without the chosen day, a fifth weekday that does not exist, a past one-shot, and a future `handled` value; verify the tests pass.

## 3. Frontmatter and page labels

- [ ] 3.1 Add `reminder` and `reminder_error` to `NoteDocument` and parse the key as a warning rather than a fatal error; verify valid, malformed, null, misplaced-capture, and unknown-nested-key tests.
- [ ] 3.2 Add the `ReminderEdit` state to `PageLabels` with set, remove, and unchanged behavior; verify a body-only save preserves a malformed raw value and the editor can replace or remove it.
- [ ] 3.3 Add `reminder` to the architecture gate's `LABEL_KEYS`; verify the label ownership test and that only `core/labels.py` and `core/frontmatter.py` write the key.
- [ ] 3.4 Update `docs/reference/frontmatter.md` with the `reminder` shape, eligibility, `handled`, zone, and malformed-value behavior; verify the examples parse and the page builds.

## 4. Schema 2 and the open flow

- [ ] 4.1 Set `CURRENT_SCHEMA_VERSION` to `2`; accept schema `1` and `2`, refuse `3` and newer, add the atomic upgrade, and keep creation/adoption on schema `2`; verify `tests/core/vault/test_schema.py`.
- [ ] 4.2 Update `VaultOpener`/`VaultSession` with the schema version, upgrade result, and `reminders_enabled` flag; upgrade a writable schema `1` vault after validation and before scanning; verify the open, upgrade, read-only, and failure paths.
- [ ] 4.3 Add the one-time upgrade toast and the persistent read-only old-format banner; verify the workspace state and view tests, including a failed upgrade falling back to reminders off.
- [ ] 4.4 Update `tests/core/vault/test_service.py`, `tests/cli/test_main.py`, `tests/ui/test_state.py`, and the template creation tests for schema `2`; verify the old `schema_version: 1` fixtures are either upgraded intentionally or changed.
- [ ] 4.5 Update `docs/reference/vault-format.md`, `docs/reference/troubleshooting.md`, and `docs/guide/command-line.md` for schema `2`, the upgrade, read-only compatibility, and the new CLI output; verify the documented commands and examples.

## 5. Snapshot and Review

- [ ] 5.1 Add `reminder` to `VaultNote` and populate it during the scan; verify snapshot and vault integration tests with valid, absent, and malformed reminders.
- [ ] 5.2 Add `ReviewItemKind.REMINDER`, the occurrence value, the reference instant, and the `reminders_enabled` flag to `ReviewPlanner`; implement queue order, pending count, and digest count; verify `tests/core/test_search.py`.
- [ ] 5.3 Update `BrowserState` and `ReviewState` to pass the flag and reference instant, start a session with reminders, and enter a reminder item; verify `tests/ui/test_state.py`.
- [ ] 5.4 Add `core/vault/reminders.py` with a dismissal write that uses the content-hash guard and records `handled`; add the `ReviewState` dismiss and open commands; verify success, conflict, and read-only failure tests.
- [ ] 5.5 Add the reminder card to `ReviewView` with Open Page primary, Dismiss secondary, Skip text, and relative time; extend the existing 5-second app loop to repaint only when the reminder count changes; verify `tests/ui/test_review_view.py`, `tests/ui/test_app.py`, and the lifecycle cancellation tests.
- [ ] 5.6 Update `docs/guide/review.md` and add a reminder section or page linked from the docs index; verify the queue order, card actions, digest wording, and pause behavior match the specs.

## 6. Page summary and editor

- [ ] 6.1 Add `set_page_reminder` and `remove_page_reminder` to `PageEditorState`; keep `PageDialogState` at 24 commands; verify the state tests and the architecture surface budgets.
- [ ] 6.2 Add `ui/components/reminder.py` with the six kinds, time list, searchable zone picker, one-shot shortcuts, short-month warning, and fifth-weekday warning; verify the component tests.
- [ ] 6.3 Add the read-mode reminder summary and the Set/Edit action to `page.py`; hide it for captures, raw-rescue pages, and trashed pages; verify `tests/ui/test_page_view.py`.
- [ ] 6.4 Add removal with an Undo toast that restores the exact previous reminder; verify the removal, undo, transient, and failed-write tests.
- [ ] 6.5 Update `docs/guide/pages-and-editing.md` with the summary, separate editor, zone picker, shortcuts, and Undo behavior; verify the page build.

## 7. Localization and copy

- [ ] 7.1 Add relative-time formatting and full weekday names to `LocaleFormat`; verify English and Spanish unit tests for minutes, hours, yesterday, days, and weekday names.
- [ ] 7.2 Add every reminder constant to the English source modules and the Spanish `.po` catalogs; classify each constant in the copy gate; verify `hatch test tests/i18n/test_copy.py`.
- [ ] 7.3 Update `docs/develop/interface-standard.md` for relative time, full weekday names, and the stored zone display; verify the documented examples match the formatter.
- [ ] 7.4 Run `hatch run i18n-compile` and verify the compiled catalogs match the tracked `.po` sources and remain untracked.

## 8. Starter content and templates

- [ ] 8.1 Reject a bundled template or guide that declares `reminder`; verify a template with a reminder is refused and a created vault has zero due reminders.
- [ ] 8.2 Update `docs/reference/templates.md` with the no-reminder starter rule; verify the page builds and the rule is visible to template authors.

## 9. Release metadata and documentation pass

- [ ] 9.1 Update `README.md` with the reminder feature and schema `2` behavior; verify the landing page names the capability without overpromising OS notifications.
- [ ] 9.2 Add an `Unreleased` changelog entry for the reminder capability, schema `2`, time zones, dependencies, and compatibility behavior; verify the entry follows Keep a Changelog.
- [ ] 9.3 Update the `RELEASE.md` reminder row with six recurrence kinds, stored zones, live count, automated evidence, and the revised Linux manual check; verify the row no longer claims four kinds or “dismiss without changing the note” without the metadata exception.
- [ ] 9.4 Update `docs/index.md` and any affected guide navigation for the reminder documentation; verify `hatch run docs:build` passes with warnings as errors.

## 10. Integration gates

- [ ] 10.1 Run `hatch check`; verify 0 diagnostics and all files formatted.
- [ ] 10.2 Run `hatch test --cover`; verify the full suite passes and coverage is at least 85%.
- [ ] 10.3 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass.
- [ ] 10.4 Run the vocabulary greps and `git diff --check`; verify no prohibited vocabulary, no trailing whitespace, and no tracked `.mo` files.
- [ ] 10.5 Verify the wheel and Flet build include `tzdata` and `tzlocal` and that zone lookup works offline; record the packaging result.
- [ ] 10.6 Run the Linux manual check: create one recurrence and one one-shot, confirm the due card and single catch-up, dismiss without changing the note body or status, pause through Trash or a status, upgrade a schema `1` vault, open a read-only schema `1` vault with reminders off, and record the version, date, and machine.

## Workflow follow-up

- Archive the change after the maintainer reviews the artifacts and all tracked tasks are complete.
- Run the post-archive release workflow: bump the MINOR version to `0.11.0`, move the `Unreleased` entry into the dated release section, update `README.md` and `docs/` when needed, run the full gates, and commit the archive with the release artifacts.
- Do not tag, push, or publish unless the maintainer asks.
