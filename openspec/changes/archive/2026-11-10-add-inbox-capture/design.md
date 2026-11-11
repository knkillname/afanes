# Design

## Context

See `proposal.md` for motivation. The current code base ships the reference and identity engine, 214 tests, and no user interface, no settings, and no CLI. `core/vault.py` already provides read-only scans, atomic writes, name uniqueness, and note creation. `ui/` and `__main__.py` do not exist, and Flet is not yet a dependency.

Two constraints shape this design:

- The application must remain offline at runtime. Flet 1.x downloads its desktop client on first use unless a packaged build or a pre-provisioned cache supplies it, so the development run is a provisioning step and distribution is a later change.
- There is still no index or cache. The Inbox will scan the vault on open and on refresh. That is acceptable for a personal vault and keeps this change small.

## Goals / Non-Goals

**Goals:**

- Make the capture loop runnable from source: choose a vault, capture a thought, see it in the Inbox, and read it.
- Keep the UI thin and the behavior testable without a rendered Flutter window.
- Persist one vault path outside the vault, and recover cleanly from a missing or corrupt settings file.
- Preserve the existing headless architecture: `core/` and `models/` gain no Flet imports.

**Non-Goals:**

- Editing notes, the Processing Wizard, statuses, due dates, people, and projects.
- The SQLite index, `core/search.py`, and query performance work.
- Timeline, People, and Next Actions views.
- The CLI, packaging, installers, auto-update, and file watching.
- External link launching, internal link navigation, and attachment rendering.

## Decisions

### 1. The Inbox is a folder, not a status

The Inbox lists notes under the vault's `inbox/` directory. Captures land there, and a note leaves the Inbox when its file leaves the folder. This is the simplest model that gives the first slice a visible queue without introducing the status lifecycle.

Consequences:

- Captured notes carry no `status` key. `status` becomes a processing-time concept; `AGENTS.md` section 1.3 is updated accordingly.
- Moving a file out of `inbox/` looks like processing. That is a deliberate trade-off: the folder is the queue, and the future Processing Wizard will make the move and the classification an explicit, confirmed step.
- Note identity and references are untouched. A move changes neither the filename stem nor any reference, consistent with `note-identity`.

Alternative considered: a `status: inbox` query. It would require a `Status` enum, a per-type validity matrix, and parsing rules before the first view exists. It is the better long-term model but a much larger first change.

### 2. Captured notes are minimal

A capture writes:

```markdown
---
type: note
---

<the captured text>
```

`type` is the only frontmatter key. No status, project, people, due date, or inferred references are added. Capture is intentionally not clarification.

`create_note` gains `status: str | None`, keeping its `"inbox"` default for backward compatibility. The new `capture_note` workflow passes `None`, which omits the key. The parameter stays stringly for now; the status vocabulary belongs to the processing change.

### 3. The filename is the first non-blank line

`capture_note` selects the first non-blank line, passes it through the existing `safe_filename` and `unique_name` policy, and writes the complete captured text as the body. The line is not stripped from the body, so truncation never loses text. Leading blank lines are skipped for naming only.

The existing policy already covers forbidden characters, reserved Windows names, trailing dots and spaces, NFC, the 200-byte cap, and collision suffixes. Capture adds no new naming rules.

Alternative considered: a timestamp or a title prompt. A timestamp produces meaningless labels; a title prompt breaks the rapid-capture loop.

### 4. `capture_note` lives in `core/vault.py`

The product rule — first line, full body, `inbox/`, no status — is a vault operation, not a view rule. `capture_note(vault_root, text)` calls `create_note` with `directory=INBOX_DIRECTORY` and `status=None`. `INBOX_DIRECTORY = Path("inbox")` is a public constant, and `inbox_notes(snapshot)` is a public query that filters and orders notes.

This keeps the UI free of business logic and lets the capture rule be tested headlessly. The capture policy is not duplicated in `ui/state.py`.

### 5. Settings are JSON in the platform configuration directory

The settings file is app-owned and machine-managed:

```json
{
  "version": 1,
  "vault": "/absolute/path/to/vault"
}
```

JSON is chosen because the standard library can both read and write it. `tomllib` is read-only, so a TOML settings file would need a hand-written writer or a new dependency. Settings are app-owned, so JSON's lack of comments is acceptable.

Platform locations, resolved without a third-party package:

| Platform | Directory |
| --- | --- |
| Linux | `$XDG_CONFIG_HOME/afanes` or `~/.config/afanes` |
| macOS | `~/Library/Application Support/afanes` |
| Windows | `%APPDATA%\afanes` or `~\AppData\Roaming\afanes` |

The file is `settings.json` inside that directory. It is outside the vault, so the vault stays portable and startup performs no vault write. Writes create the configuration directory, then reuse `core.vault.write_text_atomic`; a failed write leaves the previous file intact. A new `ConfigurationError` in `core/errors.py` wraps unreadable, malformed, unsupported-version, and unwritable settings failures.

Load outcomes:

- File missing: welcome state.
- File unreadable or malformed: welcome state with a message, file untouched.
- Version other than 1: welcome state with a message, file untouched.
- Valid: resolve and open the vault; if the path is missing or not a directory, welcome state with a message.

A relative path is resolved to an absolute path when the user chooses a vault and is always stored absolute. A relative path found in a hand-edited file is treated as invalid.

Alternatives considered: TOML (read-only writer problem), a file inside the vault (pollutes user data), and the OS keychain (overkill for one path).

### 6. One `AppState`, async commands, views that only render

`ui/state.py` owns the singleton `AppState` with a `reset()` hook for tests. It holds the vault root, inbox items, scan failures, selected note, preview body, busy flag, and user-facing message. Commands are async: `start`, `choose_vault`, `change_vault`, `refresh`, `capture`, `select_note`, and `reset`.

```
ui/views/inbox.py  --intent-->  ui/state.py  --calls-->  core/vault.py
        ^                          |                     core/settings.py
        |                          |                     core/frontmatter.py
        +------ state fields ------+
```

- Blocking settings, scan, capture, and preview reads run through `asyncio.to_thread`.
- One `asyncio.Lock` serializes commands so a capture cannot overlap a scan or a vault change.
- The state never imports views or components. Views import the state and forward events; they do not read files or parse Markdown.
- Errors are caught at the state boundary, logged at debug level with vault-relative paths, and converted to concise banner messages. No traceback reaches the UI.
- `AppState` is reset between tests; tests use `asyncio.run` rather than adding an async test plugin.

Alternatives considered: per-view state (violates the single-controller rule) and dependency injection (forbidden by `AGENTS.md`).

### 7. Flet 1.x, source-run only

The app targets Flet 1.x and pins an exact stable version (1.1.x at design time, verified when the dependency is added). The entry point is `src/afanes/__main__.py`, which calls `ft.run(main)`. No 0.28 patterns are used.

- `flet` is a runtime dependency; `flet-desktop` is pinned in the development group so `python -m afanes` has a client to launch. The Flet CLI is not needed.
- The first development run downloads and caches the desktop client under `~/.flet/client/`. This is documented as environment provisioning, not product behavior. A packaged build, which bundles the client, is a separate change.
- The app never calls the network itself. No external link is launched, and the preview intercepts every link tap.

Alternatives considered: local web mode (a browser app plus a loopback server, not a desktop product) and packaging now (Flutter toolchain and per-platform artifacts before the workflow is proven).

### 8. Ordering uses `st_mtime_ns` on `VaultNote`

`VaultNote` gains `modified_ns: int`, read from `Path.stat().st_mtime_ns` during the scan. It is display metadata, not vault data, and no timestamp is written to frontmatter. `inbox_notes(snapshot)` sorts by `(-modified_ns, name.casefold(), relative_path.as_posix())`.

A new capture is inserted at the top of the current list so it is visible immediately, then a rescan applies the durable ordering. Nanosecond timestamps make ties rare; the name and path tie-breakers make them deterministic.

Alternative considered: a `created` frontmatter key. It is durable across copies, but it is a new format key and a clock-driven write that belongs to a later change.

### 9. The preview renders Markdown with inert links

`select_note` reads the file on demand, parses it with `NoteDocument.from_text`, and exposes the body. The view renders it with Flet's public Markdown control and sets the link callback to a no-op. The raw frontmatter never reaches the body.

Reading on demand avoids carrying every note body in memory. If the file changed or became unparseable since the scan, the state shows an error and refreshes the list.

Known limitation: vault-relative images will not resolve inside Flet's Markdown renderer. Attachments are out of scope, so the preview may show a broken image placeholder.

### 10. Scan failures become a banner

`scan_vault` already returns `VaultFailure` values instead of aborting. The Inbox shows the readable notes and a banner with the count and vault-relative paths of the failures. It performs no repair and no write.

Alternative considered: blocking the view on the first failure. One bad note would make the queue unusable.

### 11. Inbox filtering and the case-insensitive folder

`inbox_notes(snapshot)` includes a note when the first component of its vault-relative path matches `inbox` case-insensitively and the path is not the folder itself. This makes `Inbox/` behave the same on case-sensitive and case-insensitive filesystems and keeps the filter in `core/`, not in the view.

The app creates the canonical lowercase `inbox` directory on the first capture. Opening a vault never creates it.

### 12. Testing without a Flutter window

- `tests/core/test_settings.py`: platform path resolution with patched platform/environment, load outcomes, save round-trip, atomic failure, relative-path rejection.
- `tests/core/test_vault.py`: `status=None` omits the key, `capture_note` naming rules, empty rejection, inbox creation, repeated captures, full-body preservation, `inbox_notes` filtering and ordering.
- `tests/ui/test_state.py`: start/choose/change/refresh/capture/select/reset against `tmp_path`, with settings patched to a temporary config directory.
- View construction with a stub page may assert key controls, but no rendered Flutter window is required. Event handlers delegate to state commands.
- An integration test covers capture → scan → list → preview body without Flet.
- Cross-platform path behavior is tested by patching `sys.platform` and the environment; `pathlib` is used everywhere.

## Risks / Trade-offs

- **Moving a file looks like processing** → The folder model is explicit in the spec; the future Processing Wizard will make classification and the move one confirmed step. Identity and references never change on a move.
- **Notes without a status exist** → `AGENTS.md` is updated, and the later lifecycle change must treat a missing status as pre-processing.
- **Flet's first-run client download** → Pin `flet-desktop` in development, document the one-time provisioning, and treat packaged builds as the only offline distribution. Do not ship a bare Python package as a runnable desktop app.
- **Flet 1.x API churn** → Exact pin, public APIs only, and a manual smoke test on the development platform. No 0.28 snippets.
- **Full scan on every refresh** → Acceptable for personal vaults. `core/search.py` and the indexer remain the later seam; the UI never queries files directly.
- **mtime ordering is metadata** → Display-only, nanosecond precision, deterministic tie-breaker, and an optimistic insert after capture. A durable `created` key can come later.
- **Preview link taps** → The handler is a no-op and is covered by a test; no external launcher is ever called.
- **No packaging** → The README states that this change runs from source; installation and distribution are a later change.

## Migration Plan

There is no existing UI, settings file, or `inbox/` convention, so no vault migration is required. `create_note` keeps its current default, so existing callers and tests continue to work. Rolling back means removing the new modules and the Flet dependency; the settings file can remain but is ignored, and no vault file is changed by this change beyond a user-initiated capture.

## Verification

Implementation review on Linux (2026-11-10):

- Visible labels: the composer has a label and hint, icon buttons have tooltips, note rows have a title and subtitle, and every banner pairs an icon with text rather than color alone.
- Focus and keyboard: the composer autofocuses. `shift_enter` makes Enter fire the capture command while Shift+Enter inserts a newline.
- Light and dark: the page follows the system theme, and custom surfaces use theme-aware `ft.Colors` values.
- Paths: every filesystem path uses `pathlib`; configuration paths are selected per platform and covered by tests with patched platform and environment values.
- Inbox matching: the first path component is matched case-insensitively and covered by a test.
- Windows names: capture reuses the existing `safe_filename` policy and its reserved-device tests.
- Offline: application code contains no HTTP or socket client. The only network activity observed was the documented one-time Flet desktop client provisioning on the first source run.
- The view and shell were exercised with stub pages, not a rendered Flutter window. macOS and Windows runtime behavior was reviewed from the platform branches and public Flet controls, but a manual pass on those platforms belongs to the later packaging change.
- The full suite surfaced a pre-existing idempotence bug in `safe_filename` for inputs such as `.|0`: the first pass left a leading space that the second pass removed. The fix strips leading dots and spaces together and includes a deterministic regression test.

## Open Questions

None. The remaining choices — exact Flet patch, picker API details, and control spacing — are implementation details covered by the tasks and do not change the specs or the approach.
