# Design

## Context

See `proposal.md` for the motivation and `specs/` for the behavior contract. The current code shapes
the approach:

- `afanes.core.vault.schema.CURRENT_SCHEMA_VERSION` is `1`, and `Vault.open` validates the settings
  file without writing. `afanes.yaml` currently contains exactly one line.
- `NoteDocument` recognizes seven keys and preserves unknown keys. `PageLabels` owns the page
  editor's label writes. A malformed `date` is a warning rather than a fatal parse error.
- `VaultNote` lives in `core/vault/snapshot.py`; `ReviewPlanner` in `core/search.py` knows Inbox
  captures, due steps, waiting steps, and projects.
- `AppState` is at its 10-name surface budget. `PageDialogState` is at 24 of 25 public commands;
  `PageEditorState` is at 20 and `ReviewState` at 15.
- `core/vault/service.py` is exactly 900 lines and `core/vault/snapshot.py` is 890, the architecture
  ceiling. Adding a `VaultNote.reminder` field to the existing layout would exceed the service
  ceiling.
- `app.py` already runs a 5-second background loop that applies external vault changes. Its task is
  cancelled on disconnect, vault close, and workspace replacement.
- `LocaleFormat` already formats 12-hour English and 24-hour Spanish times; it has month and short
  weekday tables but no full weekday names or relative-time formatter.
- The application is offline-only and must behave the same on Linux, macOS, and Windows.

## Goals / Non-Goals

**Goals:**

- One whole-note reminder on references, projects, and log entries, with six recurrence kinds and one
  one-shot form.
- Stored IANA zones with system-zone detection and correct DST behavior.
- Due occurrences, one-entry catch-up, pause and resume, and dismissal without changing the note's
  body or status.
- Review, digest, editor, schema upgrade, localization, and documentation integrated through the
  existing ownership boundaries.
- A schema `2` contract that a future change can extend without changing the meaning of existing
  schedules.

**Non-Goals:**

- Operating-system notifications, delivery while the application is closed, snooze, end dates,
  multiple reminders per note, per-step reminders, and schedule exceptions.
- A persistent index, a background service, or a side database for reminder state.
- Reminder content in bundled starter templates.
- Automatic downgrade of a schema `2` vault.

## Decisions

### D1. The reminder is a nested, tagged frontmatter mapping

One optional `reminder` key holds the whole schedule:

```yaml
reminder:
  zone: America/Mexico_City
  recurrence:
    kind: weekdays
    weekdays: [mon, wed, fri]
    times: ["09:00", "17:30"]
  handled: 2026-11-14T15:00:00+00:00
```

A one-shot uses `once: 2026-11-20T09:00` instead of `recurrence`. The six kinds are `daily`,
`weekdays`, `month_day`, `nth_weekday`, `last_day`, and `last_weekday`. `handled` is an absolute
instant with an offset. Unknown nested keys are preserved.

Alternatives considered:

- flat keys such as `reminder_every` and `reminder_at`: more top-level keys, harder to validate as
  one unit;
- a string grammar: compact but hard to read, localize, and validate;
- an app-managed side file: breaks the vault as the source of truth and drifts under renames;
- a `since` marker: the user chose to show the latest missed occurrence immediately when a schedule
  is created or edited, so `since` would suppress the behavior the user asked for.

### D2. Due state is the latest occurrence after the handled instant

A `Reminder` value object owns the schedule and exposes the latest occurrence at or before a
reference instant and the next occurrence after it. The due occurrence is the latest occurrence in
the stored zone when it is after `handled`, or when `handled` is absent. This makes multiple missed
times collapse into one entry and lets a dismissal advance to the next time naturally.

The occurrence rules:

- a time is local wall-clock time in the stored zone;
- a nonexistent DST time is skipped;
- a repeated DST hour produces one entry because the planner asks for the latest occurrence;
- a month without the chosen day or nth weekday is skipped;
- a past one-shot is due once and a future one-shot is not due;
- a `handled` instant later than the current instant is treated as absent, so a clock skew or a
  hand-edited future value cannot suppress a reminder indefinitely.

The recurrence and occurrence methods live on the value objects. They are pure and do not read files
or the current clock; callers pass the reference instant.

Alternatives considered:

- cron expressions: powerful but a new parser and vocabulary for six constrained kinds;
- materializing each occurrence: more state and a migration problem when a schedule changes;
- calculating in UTC only: loses the user's wall-clock intent;
- recalculating from the last acknowledgement with an interval count: more state and more edge cases
  than the latest-occurrence rule.

### D3. Time zones use `tzdata` and `tzlocal`

`zone` is an IANA name. `tzdata` supplies the zone rules on every supported platform, including
Windows, and is read offline. `tzlocal` reports the computer's current IANA zone so the editor can
default to it. A missing zone resolves to the system zone; an unknown zone is a warning and the
reminder is ignored for scheduling.

The editor offers a searchable IANA list. The page summary and card show the schedule; the card uses
a relative time, and the summary carries the exact cadence, times, and zone. The zone list is
technical data, not translated copy.

Alternatives considered:

- system tzdata only: inconsistent on Windows;
- fixed UTC offset: no DST and wrong when the user travels;
- UTC only: defeats wall-clock routines;
- free-text zone entry: unusable without knowing the exact IANA name;
- a standard-library-only detector: no cross-platform API for the local IANA name.

`tzdata` is Apache-2.0 and `tzlocal` is MIT. Both are offline, pure data or pure Python, and are
included in the wheel, the Flet build, and the dependency-floor matrix.

### D4. Schema 2 is upgraded outside the read-only open validation

`Vault.open` remains the read-only validation path. It reads a schema `1` or `2` file and returns the
vault with the declared schema. The interface's `VaultOpener` then performs the courtesy upgrade:

1. validate the directory and settings file;
2. if the schema is `1` and the file is writable, atomically rewrite only `afanes.yaml` with
   `schema_version: 2`;
3. scan the vault;
4. show a one-time toast for a successful upgrade, or open with reminders off and a persistent
   banner when the upgrade cannot be written;
5. a read-only schema `1` vault skips the write, opens for browsing, and sets reminders off.

This keeps the specification's "validation writes nothing" guarantee while allowing the explicit
post-validation upgrade. The UI session stores the schema version and a `reminders_enabled` flag; the
Review planner, page summary, and editor read that flag. A schema `2` read-only vault keeps reminders
enabled for reading; a dismissal that cannot write reports a failure and leaves the reminder due.

The core `Vault` service keeps only its root. A `VaultOpen` value carries the vault, schema, upgrade
result, and capability flag from the UI opener to the session. The CLI has no open command;
`vault create` and `vault adopt` write schema `2`, and an already versioned folder is reported with
its declared schema.

Alternatives considered:

- upgrading inside `Vault.open`: simpler call path but breaks the read-only validation contract and
  makes a failed upgrade indistinguishable from an invalid vault;
- refusing read-only schema `1`: rejected by the user; the vault stays browsable with reminders off;
- mixed-schema note parsing: rejected; one capability flag controls the feature;
- writing a hidden upgrade marker: adds state without a user-visible benefit.

### D5. Review puts reminders first and reuses the existing refresh loop

`ReviewPlanner` gains a reference instant and a `reminders_enabled` flag. It emits a `REMINDER` item
with the due occurrence, sorts reminders by occurrence oldest first, and places them before Inbox
captures. The pending count and the digest count include reminders. The digest copy changes from
"due steps" to "items".

The existing `app.py` background loop already ticks every 5 seconds and is cancelled on disconnect,
vault close, and workspace replacement. The reminder count is recomputed from the current snapshot on
each tick; the workspace repaints only when the displayed count changes. This meets the 15-second
freshness requirement with margin and avoids a second timer. It reads the snapshot only, never
writes, and never changes an active session's queue.

Alternatives considered:

- a separate 15-second timer: correct but redundant with the existing loop;
- an event-driven wake at the next occurrence: exact but needs a scheduler, rescheduling on every
  vault change, and more lifecycle work;
- a 60-second poll: undersamples a minute-resolution schedule;
- a toast or OS notification when due: outside the gate and more intrusive than the Review badge.

### D6. The editor is a separate surface on the page boundary

The page shows a read-mode summary and a **Set Reminder** or **Edit Reminder** action. Editing opens a
dialog or panel owned by a new reminder component; the page's label form does not grow.

- The editor holds the six kinds, a time list, the zone picker, and the one-shot date and shortcuts.
- A monthly day that does not exist every month shows an inline warning and suggests the last-day
  choice; a fifth weekday warns and suggests the last-weekday choice.
- Saving goes through the existing page draft and conflict guard. A read-mode save writes immediately;
  a dirty draft carries the reminder into its next write; a new page is created on first save.
- Removing is immediate with Undo in a toast. The undo payload holds the exact previous reminder.
- Changing the schedule or zone resets `handled`; saving an unchanged reminder or editing only the
  body preserves it.

`PageEditorState` gets the set and remove commands (20 to 22, within the 25-command budget). The
dialog's transient open/closed state stays in the view component. `PageDialogState` remains at 24 and
is not extended.

Alternatives considered:

- inline reminder fields in the label form: too crowded and poor for a recurrence form;
- a page-menu-only action: hidden state and no summary;
- deriving the reminder from the due date: loses one-shots, references, and logs;
- a confirmation dialog for removal: the reversible-action rule prefers Undo.

### D7. Ownership and module layout follow the existing DAG

New units:

- `models/reminder.py`: immutable `Reminder`, `Recurrence`, `OneShot`, `ClockTime`, `Weekday`, and
  occurrence methods. It imports only the standard library.
- `core/vault/reminders.py`: a service that loads a note, validates the target occurrence, records
  `handled`, and writes through the existing page write path with the content-hash guard.
- `ui/components/reminder.py`: the editor dialog/panel and its local controls.

Changed units:

- `core/frontmatter.py`: parse and warn on `reminder`; expose `NoteDocument.reminder` and
  `reminder_error`.
- `core/labels.py`: a `ReminderEdit` state (`unchanged`, `set`, `removed`) so a body-only save
  preserves a malformed raw reminder and the editor can replace or remove it.
- `core/vault/schema.py`: version `1`/`2` loading, the atomic upgrade, and schema `2` creation.
- `core/search.py`: reminder items, queue order, count, digest count, and reference instant.
- `ui/state/review.py`: dismiss and open commands (15 to 17).
- `ui/state/pages.py`: set and remove commands (20 to 22).
- `ui/views/page.py`, `ui/views/review.py`, and `ui/components/reminder.py`: presentation only.
- `ui/app.py`: the existing refresh loop compares the reminder count and repaints on change.

`VaultNote` and its ordering value objects move from `core/vault/snapshot.py` to a new
`core/vault/note.py` before the reminder field is added. This is a behavior-preserving extraction
that frees the 900-line ceilings in `snapshot.py` and `service.py`; `service.py` imports the note
value directly. The new module is a value-type module, not a sibling vault service, so the
`VAULT_SIBLING_MODULES` rule is unaffected.

The architecture gate's `LABEL_KEYS` gains `reminder`. `core/labels.py` and `core/frontmatter.py`
remain the only writers of the top-level key. No new `AppState` field or command is added.

### D8. Localization covers relative time and full weekday names

`LocaleFormat` gains a relative-time formatter and full weekday names. The formatter uses the active
language and the same explicit tables as the rest of the module:

- English: “just now,” “5 minutes ago,” “2 hours ago,” “yesterday,” “3 days ago.”
- Spanish: “ahora mismo,” “hace 5 minutos,” “hace 2 horas,” “ayer,” “hace 3 días.”

The page summary uses the existing 12-hour English and 24-hour Spanish time format and the stored
zone. The Review card uses the relative time only. All new interface copy goes through the existing
English source modules and Spanish `.po` catalogs, and the copy gate classifies every new constant.

The zone name is data, not copy. The picker may humanize the city segment, but the stored IANA name
is the source of truth and is never translated.

### D9. Malformed data is a warning, not an unreadable note

The parser follows the malformed-date precedent: a bad `reminder` is preserved in `raw`, exposed as
`reminder_error`, and ignored for scheduling. A capture with a reminder is also ignored with a
warning. The page remains readable and the raw value survives a body-only save. The reminder editor
can replace or remove it. A scan never rewrites a malformed value.

The `handled` marker is an absolute instant. A future value is treated as absent so it cannot
suppress a reminder indefinitely; the raw value remains until the next valid dismissal.

### D10. Starter content stays reminder-free

Bundled templates and the guide are refused if they declare a `reminder`. A daily reminder in starter
content would be due immediately under the latest-occurrence rule and would violate the existing
zero-pending-work promise. Users add reminders after creation.

## Risks / Trade-offs

- **The existing loop runs every 5 seconds, not 15.** → It is already running for external edits, and
  the count check is an in-memory comparison. The tighter bound is a superset of the requirement and
  avoids a second timer. If the loop is ever slowed, the reminder count must keep a 15-second maximum.
- **`tzdata` needs periodic updates.** → Pin a compatible date-based range, include it in the floor
  matrix and the wheel, and treat an unknown zone as a warning so a renamed zone never hides a page.
- **Schema `1` compatibility is a real shim.** → Gate it behind one `reminders_enabled` flag, cover
  writable upgrade, read-only open, failed upgrade, and schema `2` read-only with tests, and show a
  persistent banner whenever reminders are off.
- **The upgrade writes during open.** → It runs after read-only validation, rewrites only
  `afanes.yaml`, uses the atomic writer, and falls back to browsing with reminders off if the write
  fails. A later writable open retries.
- **The `VaultNote` extraction is a large mechanical diff.** → Move value types only, keep the module
  free of service imports, and land the extraction as its own task before the reminder field.
- **Dismissal writes the note.** → Use the existing content-hash guard. An external edit aborts the
  dismissal, reports it, and leaves the reminder due.
- **A schema `2` vault is refused by older applications.** → Document the one-line rollback: set
  `afanes.yaml` back to schema `1`; older applications preserve the unknown `reminder` key and ignore
  it. The current application will re-upgrade on its next writable open.
- **A long IANA zone list can overwhelm the editor.** → Searchable list, system-zone default, and a
  humanized city label; the stored value stays the IANA name.
- **The editor is a large UI surface for wave 5.** → Follow the existing dialog patterns now (initial
  focus, Esc, Cancel before affirmative, labels, focus ring) so wave 5 audits rather than rewrites it.
- **Relative time only hides the exact schedule on the card.** → The page summary shows the exact
  cadence, times, and zone; the card is deliberately about urgency.
- **No OS notification when the app is closed.** → The gate already excludes OS notifications; the
  digest and Review badge are the promised surface.

## Migration Plan

1. Extract the `VaultNote` value types to `core/vault/note.py` with no behavior change; run the
   architecture and vault tests.
2. Add `tzdata` and `tzlocal` to `pyproject.toml`, the floor matrix, and the package checks.
3. Add the reminder model and property tests for recurrence, zones, DST, month skips, and the
   latest-occurrence rule.
4. Add frontmatter parsing, `PageLabels` edit state, and the architecture-gate label key.
5. Add schema `2`, the upgrade, read-only schema `1` behavior, and the open-flow flags.
6. Add snapshot, Review planner, digest, card, and the live count.
7. Add the page summary, editor dialog, Undo, and copy.
8. Update docs, the release gate, the changelog, and the full test suite.
9. Archive and release as a MINOR `0.11.0` after the change is complete; `1.0.0` remains reserved for
   the full MVP gate.

Rollback before archive is a code revert. After a vault has been upgraded to schema `2`, an older
application refuses it. To return to an older application, set `afanes.yaml` back to schema `1`; the
older application treats `reminder` as an unknown key and preserves it, while reminders are inactive.
The current application upgrades the file again on the next writable open. There is no automatic
downgrade.

## Open Questions

None. The exploration settled the data model, compatibility behavior, time-zone handling, queue
order, dismissal, editor surface, Undo, live refresh, and the one-change scope.
