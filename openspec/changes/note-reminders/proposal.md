# Proposal

## Why

Afanes can surface due steps and stalled projects, but a reference, project, or log entry cannot
nudge the user at a chosen time. That leaves every whole-note routine dependent on the user
remembering to open the page. The `1.0.0` gate requires one whole-note reminder per note, and this
is the last functional capability before the final interface and packaging work.

This is also the only remaining change to the on-disk vault contract. A schema `2` reminder records
its own IANA time zone, so a schedule means the same wall-clock time when the user travels or moves
the vault. Defining that contract now avoids a second schema bump when time-zone behavior is added.
The same change keeps the Review count live with a short poll, because a reminder that becomes due
while the application is open should not wait for a manual refresh.

## What Changes

- Add one optional `reminder` key to references, projects, and log entries. It stores one recurrence
  or one one-shot, an IANA time zone, and an absolute `handled` instant. **BREAKING**: the vault
  schema becomes `2`.
- Support six recurrence kinds: daily, selected weekdays, day of month, nth weekday, last day of
  the month, and last weekday. Every recurrence has one or more `HH:MM` times.
- Show due reminders first in Review, most overdue first, with **Open Page**, **Dismiss**, and
  **Skip**. A reminder is one catch-up entry showing the latest missed occurrence.
- Record a dismissal as `handled`; it never changes the note body, status, or schedule. A changed
  schedule or zone resets the marker; a body-only edit keeps it.
- Include due reminders in the Review pending count and the launch digest. The digest uses neutral
  “items” wording so a user with only reminders still gets a launch signal.
- Pause a reminder while its note is in Trash or its status is `done`, `cancelled`, `archived`, or
  `later`. On return, show one catch-up entry and then continue.
- Refresh the Review count every 15 seconds while a vault is open. The poll never changes a review
  session's snapshot queue and is cancelled when the vault closes or the application exits. No
  operating-system notifications are added.
- Add a read-mode reminder summary and a separate editor dialog. The dialog offers a searchable
  IANA zone list, one-shot deadline shortcuts, an inline warning for monthly days that do not exist
  in every month, and removal with Undo.
- Treat a malformed reminder as a warning: the page stays readable, the schedule is ignored, and
  the raw value is preserved until the user replaces or removes it. A missing zone assumes the
  system zone.
- Upgrade a writable schema `1` vault by rewriting only the one-line `afanes.yaml`, then show a
  one-time toast. Open a read-only schema `1` vault for browsing with reminders off and a persistent
  banner. Refuse schema `3` and newer, and preserve invalid files.
- Add `tzdata` and `tzlocal` as offline runtime dependencies for IANA zone rules and system-zone
  detection across Linux, macOS, and Windows.
- Update the affected specifications, manual, release gate, changelog, and tests.

## Capabilities

### New Capabilities

- `note-reminders`: one whole-note reminder per eligible note, six recurrence kinds, stored time
  zones, due-occurrence calculation, catch-up, Review cards, dismissal, pause rules, the editor, and
  schema `2`.

### Modified Capabilities

- `note-model`: the recognized frontmatter key set gains `reminder`, with validation and a
  malformed-value warning for eligible notes.
- `note-editing`: the page shows a reminder summary and offers a separate reminder editor, including
  removal with Undo.
- `guided-review`: the pending count and launch digest include reminders; the snapshot queue places
  due reminders first; a reminder card adds Open Page, Dismiss, and Skip.
- `vault-schema`: version `2` becomes current; a writable version `1` file is upgraded; a read-only
  version `1` vault opens with reminders off; newer versions stay refused.
- `vault-selection`: opening a version `1` vault reports the upgrade or the read-only banner, and a
  schema `2` vault opens without a compatibility notice.
- `vault-templates`: a created vault records schema `2`.
- `command-line`: `vault create` and `vault adopt` report and write schema `2`.

## Impact

- New core model and service modules for reminder schedules and dismissal, plus a new reminder
  editor component.
- `core/frontmatter.py`, `core/labels.py`, `core/vault/schema.py`, `core/vault/snapshot.py`,
  `core/vault/service.py`, `core/search.py`, and `core/localization.py` gain reminder behavior.
- `ui/state/review.py`, `ui/state/pages.py`, `ui/state/workspace.py`, `ui/views/page.py`,
  `ui/views/review.py`, and the interface catalogs gain reminder behavior and copy.
- Two new runtime dependencies: `tzdata` (Apache-2.0) and `tzlocal` (MIT). Both are offline and
  cross-platform.
- The core line ceiling is tight: `core/vault/service.py` is exactly 900 lines and
  `core/vault/snapshot.py` is 890. The change plans a small extraction rather than line golf.
- `LABEL_KEYS` in the architecture gate gains `reminder`; the key remains written only by
  `core/labels.py` and `core/frontmatter.py`.
- No new `AppState` field or command. The editor uses `PageEditorState` or view-local state, the
  dismissal uses `ReviewState`, and the poll uses `WorkspaceController`.
- Older applications refuse schema `2`. Existing note bodies are unchanged; only `afanes.yaml` is
  upgraded.
- Documentation, screenshots, and the `RELEASE.md` reminder row change. The gate row expands beyond
  four recurrence kinds and records the stored-zone and live-count evidence.
