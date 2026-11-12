# Design

## Context

The current model has three note types, a five-key frontmatter vocabulary, and a read-only scan into
`VaultSnapshot`. Identity is the filename stem, references use the `note` and `project` schemes, and
the workspace has Inbox, Projects, References, Needs attention, and Review destinations. There is no
persistent index. `AppState` is at its 10-name architecture budget, and `core/search.py` is the
read-only query layer over a snapshot. See `proposal.md` for motivation and the spec deltas for
behavioral requirements.

## Goals / Non-Goals

**Goals:**

- Add a fourth note type, `log`, with a date-based identity and a Log workspace.
- Add an editable ISO `date` to every note, with year, month, or day precision.
- Keep the scan read-only and the query layer index-free.
- Reuse the existing rename, atomic-write, and reference-rewrite machinery for date changes.
- Keep the change cross-platform and inside the existing architecture budgets.

**Non-Goals:**

- No migration or backfill of existing notes; notes without a date are Undated.
- No calendar-day view, reminders, recurrence, or time-of-day precision.
- No changes to project steps, due-date semantics, review planning, or the CLI.
- No new runtime dependency, network call, telemetry, or persistent index.

## Decisions

### A dedicated `NoteDate` value object with precision

`models/note.py` gains a frozen slotted `NoteDate` (or `PartialDate`) value with a `DatePrecision`
enum (`YEAR`, `MONTH`, `DAY`), the ISO text, and comparison helpers. `core/frontmatter.py` parses the
raw YAML value into it:

- `datetime.date` becomes day precision.
- An integer (but not a boolean) becomes year precision.
- A string is parsed as `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`.
- A `datetime.datetime` or any other value is malformed.

`NoteDocument` stores `date: NoteDate | None` and `date_error: str | None`. A malformed value is not a
`NoteParseError`; the note still parses, the date is treated as absent, and the editor reads the
error. `VaultNote` stores `date` only; the scan does not need the warning.

When serializing, day precision is written as a `datetime.date` (so YAML emits an unquoted ISO
date, like `due_date`), while year and month precision are written as strings (so YAML keeps them as
strings). The editor accepts any of the three ISO forms and reports the same warning as the parser.

**Alternatives considered:** a single timestamp (rejected: the tree is date-based and timezones add
noise); separate `year`/`month`/`day` keys (rejected: three keys to keep consistent and no single
value to move); storing the date only on log notes (rejected by the product decision that every note
has a date).

### Log identity is the date; date changes reuse the rename pipeline

`ReferenceScheme` gains `LOG`. A log note's filename is exactly its date (`2025.md`, `2025-10.md`,
`2025-10-12.md`), and its name is therefore the date. The `log:` scheme resolves only log notes.

`VaultNaming` gains a date-change plan and a type-change plan that both produce a rename-shaped
preview:

- The new `date` is written to the log file's frontmatter first.
- The file is renamed to the new ISO name and moved to the folder the date selects.
- Inbound references are rewritten from the old `log:` name to the new one using the existing
  `apply_rename` rewrite logic.
- The heading is never rewritten by a date change; the heading is the display title, not the
  identity.
- The operation is safe to re-run; changed or missing referring files are skipped and reported.

The existing `plan_rename`/`apply_rename` machinery already checks content hashes, writes
atomically, and rewrites resolving references. The date-change preview wraps it with the new date and
the `log` scheme. Type changes involving `log` use the same pipeline: becoming a log renames to the
date and rewrites `note:`/`project:` references to `log:`; leaving the log renames to the display
title and rewrites `log:` references to the target scheme.

The one-per-date rule is enforced by the log scheme's name catalog and the target-path check. A
target date already present in the catalog or on disk refuses creation, processing, or a date change
before any write.

**Alternatives considered:** keeping the title as the identity and the date as metadata (rejected:
it allows duplicate dates and makes the tree ambiguous); renaming only when links exist (rejected:
the product chose automatic rewrites); using a numeric suffix for duplicate dates (rejected: it
breaks the one-entry-per-date model).

### A new read-only `core/log.py` query service

`core/search.py` already hosts the browser, project board, and review planner and is close to its
900-line module budget. A new `core/log.py` owns a `LogTimeline` service over one `VaultSnapshot`:

- `LogTimeline.entries(mode)` returns dated notes filtered by Entries or Everything.
- It builds `LogYear`, `LogMonth`, and `LogDay` value objects with entries at the level their date
  names.
- The calendar month view is derived from the same buckets: day counts, month-entry presence, and
  year-entry presence.
- Search filtering reuses `Browser.matches`, so the same title, identity, body, and step-text rules
  apply.
- Undated notes are a separate bucket and never invent a date.

The service performs no file I/O and never writes. The UI consumes the buckets; it does not derive
the tree or calendar itself.

**Alternatives considered:** extending `core/search.py` (rejected: module budget and mixed
concerns); a persistent date index (rejected: no index without an approved change and unnecessary
for snapshot-scale data).

### The Log section is a workspace destination, not a browser group

`WorkspaceSection` gains `LOG`. Like `REVIEW`, it has no flat `BrowserSection` mapping; its lower
sidebar area is a custom calendar plus tree. In Entries mode, log notes are reached there and are
their only home. In Everything mode, the Log is an additional date lens over every parsed note, so a
project can appear under Projects and in the Log. The existing "one home per note" rule is therefore
scoped to normal browsing; Everything is explicitly a lens.

The tree starts with every year collapsed. The calendar is a month grid. The year and month headers
are controls: the row expands or collapses the tree; a visible plus on an empty month/year row opens
the creation dialog; a dot/open control on an occupied row opens the entry. Days are cells: a tinted
cell with a dot marks entries; clicking a day with one entry opens it, a day with several expands the
tree, and an empty day opens the creation dialog.

`BrowserState` gains `log_mode`, `log_month`, and the calendar/tree selection. `AppState` does not
gain a field, preserving its 10-name budget. The mode is persisted per vault; the viewed month is
session state and starts at the current month.

**Alternatives considered:** a flat Log list plus a tree (rejected: duplicate surfaces); a separate
main-area calendar mode (rejected in favor of keeping the page pane); a third AppState controller
(rejected: architecture budget).

### Settings remember the Log mode per vault

`Settings` gains a `log_modes: dict[str, str]` mapping from resolved vault path to `entries` or
`everything`. The JSON payload keeps `version: 1` and treats a missing mapping as empty, so a
settings file without the new field still loads without a migration branch. The workspace writes the
mapping when the mode changes and reads it when a vault opens. The stored values are validated; an
unknown mode falls back to `entries`.

**Alternatives considered:** a global mode (rejected: the product chose per-vault); storing the
mode in the vault (rejected: UI preferences do not belong in the Markdown vault); bumping the
settings version (rejected: it would forget the remembered vault for no benefit).

### Creation, processing, and template cards share one log path

- `Vault.log_directory(date)` returns `log/<year>/` for year precision and
  `log/<year>/<month>/` for month or day precision, reusing existing case variants.
- `VaultPages.create_log_entry(date, title, scaffold)` writes `type: log`, the date, and a body made
  of `# <title>` plus the optional card body. It checks the log scheme and target path before
  writing, opens in edit mode, and follows the existing atomic-write rules.
- `ProcessingOutcome` gains `LOG`. The plan uses the capture's `date`; when it is missing, the
  capture file's last-modified calendar date is used for this conversion only. The target path is the
  log directory plus the date filename. The plan refuses an occupied date and preserves the capture
  body and heading. The resulting note writes only `type` and `date`.
- `TemplateCard` becomes `note_type: NoteType` plus optional `category`. A reference card requires
  `category`; a log card requires no category. The reference picker lists reference cards and the log
  picker lists log cards; both always offer Empty.
- `core/templates.py` stamps the vault creation date into every bundled note during
  `_read_notes`, so the guide and starter notes are dated without editing every bundled file. The
  validation sees the date and the template validity rules remain unchanged.
- The bundled `template_cards/daily.md` card declares `type: log`, `title: Daily entry`, the
  description, and the three `##` prompts. New vaults seed eight cards.

**Alternatives considered:** a separate log creation service outside `VaultPages` (rejected: the
existing page creation and atomic write paths already own this); a `log` category on references
(rejected: the product chose a fourth type); a card-only creation path (rejected: the calendar and
Today's entry need a direct write).

### The page editor shows Date for every type and hides log workflow labels

`PageLabels` gains `date_text` and a `date_error` property, parallel to `DueDateText`. The edit form
shows the Date field for every note. Category, status, due date, and requester remain type-scoped;
log offers none of them. The read meta row becomes visible for every page and shows the date; the
project status, due date, and requester remain project-only additions. Rename is hidden for log
entries, and the date field is the only identity control. A malformed date blocks the save with the
same warning the parser reports.

**Alternatives considered:** showing Date only on log pages (rejected: every note is dated and the
archive uses it); keeping the project-only meta row and adding a separate date row (rejected: two
meta rows for one page).

## Risks / Trade-offs

- **Automatic renames can surprise the user.** → The rename is limited to the log date change and
  log type changes, uses the existing content-hash checks, rewrites only resolving references, skips
  changed files, reports failures, and is safe to re-run. The Log tree and page update from the next
  scan.
- **Partial-date parsing has many input shapes.** → A single value object owns parsing, serialization,
  and comparison; Hypothesis covers YAML date, int, string, timestamp, and malformed values; a
  deterministic regression test covers each rejected shape.
- **The calendar is a custom control.** → Build it from standard Flet rows and cells with text
  labels, focus states, and dots/tints that are not color-only. Keyboard users can reach every
  control; tests assert the accent and click outcomes without a rendered window.
- **The mode preference adds settings state.** → Keep it in the existing app-owned settings file,
  validate the values, and default to `entries` for an absent or unknown value. No vault content is
  stored.
- **The Log section and the in-flight `iso-week-labels` and `note-connections` changes touch the
  same page area.** → The Date field uses the `date-display` formatter when that capability exists;
  otherwise it uses ISO text. The page layout leaves room for the connections panel, and the two
  changes can land in either order.
- **`AppState` and `core/search.py` are near their budgets.** → Add Log state to `BrowserState` and a
  new `core/log.py` module; do not add an `AppState` field or grow `search.py` with calendar logic.

## Migration Plan

There is no migration before 1.0.0. Existing notes without a `date` remain **Undated**; opening or
scanning a vault writes nothing. New notes receive a date at creation. The bundled guide and starter
notes receive the vault creation date. No settings version bump is needed because the new mapping is
optional. Rollback is a code revert; the extra `date` keys are preserved as unknown data by older
code.

## Open Questions

None that change the specs or the approach. The remaining defaults are fixed here: the Log tile
count follows the active mode, the calendar month starts at the current month and is not persisted,
**Today's entry** sits above the calendar, and the bundled card file is `daily.md`.
