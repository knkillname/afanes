# Proposal

## Why

Afanes can browse by note type, project status, and due date, but it cannot answer a simple
chronological question: what did I write, and when? A dedicated log note type plus an editable date
on every note gives the vault a diary and an archive lens without leaving Markdown or adding a
persistent index.

## What Changes

- Add `log` as a fourth note type. A log entry has `type: log`, an editable ISO `date`, a title, and
  a body. It has no category, status, due date, or requester. **BREAKING**
- Add an editable `date` key to every note. Values use ISO precision: `YYYY`, `YYYY-MM`, or
  `YYYY-MM-DD`. `due_date` remains a full-day project deadline.
- A log entry's identity is its date. It is filed under `log/<year>/` for a year entry or
  `log/<year>/<month>/` for a month or day entry, and linked with the new `log:` scheme.
  **BREAKING**
- Enforce one log entry per exact date. Creating, processing into, or moving onto an occupied date
  is refused.
- Add a Log workspace section with a month calendar, a collapsed year/month/day tree, an
  Entries/Everything switch, and search that filters both.
- Create entries from **Today's entry**, an empty calendar day, or the plus control on an empty
  month/year row. A bundled `type: log` card named **Daily entry** provides a reflection starter.
- Changing a log entry's date renames it, moves it, and rewrites inbound links automatically.
  Changing a note into or out of `log` moves and renames it and rewrites links. Rename is hidden for
  log entries. **BREAKING**
- Add a **Log entry** outcome to processing. It moves the capture to the log folder, uses the
  capture's date, and refuses an occupied date. An undated capture uses its last-modified date for
  this conversion.
- Notes without a `date` are **Undated**. The application does not guess, backfill, or write dates
  on open. No backward compatibility is promised before 1.0.0. **BREAKING**
- Update the guide, the frontmatter and vault-format references, and the workspace documentation.

## Capabilities

### New Capabilities

- `note-log`: the log note type's one-per-date rule, date-based creation, calendar and date tree,
  Entries/Everything lens, and log card behavior.

### Modified Capabilities

- `note-model`: fourth note type and the `date` key with ISO partial precision.
- `note-identity`: date-based identity, filenames, uniqueness, rename, and type-change rules for log
  notes.
- `note-references`: the `log:` scheme and automatic rewriting when a note enters or leaves the log.
- `note-editing`: the Date field, log type in the editor, hidden Rename, date-change writes, and
  malformed-date warning.
- `vault-layout`: `log/<year>/` and `log/<year>/<month>/` folders and lazy creation.
- `vault-browsing`: the Log section and the Everything lens exception to one home per note.
- `template-cards`: log cards alongside reference cards, including picker and validation rules.
- `vault-templates`: eight seeded cards and the guide's explanation of the log type.
- `processing`: the Log entry outcome, one-per-date refusal, and undated-capture conversion.
- `inbox-capture`: captures declare `date` in addition to `type`.

## Impact

- Models and parsing: `models/note.py`, `core/frontmatter.py`, `core/editing.py`.
- Vault: `core/vault/service.py`, `snapshot.py`, `pages.py`, `naming.py`, `processing.py`.
- Queries: `core/search.py` or a new read-only `core/log.py`; the Log timeline is derived from the
  snapshot, with no index.
- Templates: `core/templates.py`, `core/template_cards.py`, a new `template_cards/daily.md`, and the
  bundled guide.
- UI: `ui/state/browser.py`, `session.py`, `pages.py`, `dialogs.py`, `navigation.py`;
  `ui/views/workspace.py`, `page.py`; a new calendar component; `ui/strings.py`, `ui/theme.py`.
- Settings: a per-vault Log mode preference in `core/settings.py`.
- Docs: frontmatter, vault format, workspace, a new Log guide page, and the bundled guide.
- Tests: parser, identity, layout, processing, browser/search, editor, and UI state.
- No new dependency, network, telemetry, or persistent index.
- Architecture: `AppState` is at its 10-name budget; Log state must live in `BrowserState` or a new
  core service, not a new facade field.
- Cross-change: `iso-week-labels` introduces `date-display`; the Date field and log dates must follow
  that formatting when both changes land. `note-connections` adds a page panel; the Date field must
  not collide with it.
