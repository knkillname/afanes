# Tasks

## 1. Dependency and package setup

- [x] 1.1 Add `flet` to the runtime dependencies and `flet-desktop` to the `dev` group, pinned to the same exact 1.1.x version; verify `hatch run python -c "import importlib.metadata as m; print(m.version('flet'), m.version('flet-desktop'))"` prints matching versions.
- [x] 1.2 Update `AGENTS.md` section 2.7 (and any affected Flet note in 2.3) to distinguish the runtime Flet library from the development-only desktop client and its one-time provisioning; verify the policy text matches the pinned dependencies.
- [x] 1.3 Add thin `src/afanes/ui/__init__.py`, `src/afanes/ui/views/__init__.py`, and `tests/ui/__init__.py`; verify `hatch run python -c "import afanes.ui, afanes.ui.views"` succeeds and `hatch test tests/core/test_architecture.py` still passes.

## 2. Settings and configuration errors

- [x] 2.1 Add `ConfigurationError` to `core/errors.py` with a strict NumPy-style docstring; verify `hatch test tests/core/test_errors.py` passes with a test asserting it derives from `AfanesError`.
- [x] 2.2 Add `core/settings.py` with `config_directory()`, `settings_path()`, `load_settings()`, and `save_settings()`, covering Linux, macOS, and Windows configuration directories, absolute-path resolution, missing/corrupt/unsupported-version outcomes, and atomic writes through `vault.write_text_atomic`; verify `hatch test tests/core/test_settings.py` passes.
- [x] 2.3 Add `tests/core/test_settings.py` covering the platform path table with patched platform and environment, a save/load round-trip, a missing file, malformed JSON, an unsupported version, relative-path rejection, and a failed atomic write that preserves the previous file; verify the file passes and the settings module reports at least 90% coverage.

## 3. Capture and inbox query

- [x] 3.1 Add `INBOX_DIRECTORY` and `inbox_notes(snapshot)` to `core/vault.py`, and add `modified_ns` to `VaultNote`, populated from `stat().st_mtime_ns` during the scan; add tests for nested and case-variant inbox paths, exclusion of notes outside `inbox/`, and newest-first deterministic ordering; verify `hatch test tests/core/test_vault.py` passes.
- [x] 3.2 Extend `create_note` with `status: str | None = "inbox"` so `None` omits the key, and add `capture_note(vault_root, text)` plus a capture-specific error for empty input in `core/errors.py`; add tests for the first-non-blank-line rule, full-body preservation, empty rejection, lazy `inbox/` creation, repeated captures, and the absence of a status key; verify `hatch test tests/core/test_vault.py` passes.
- [x] 3.3 Add an end-to-end core test that captures two notes, scans the vault, calls `inbox_notes`, and extracts preview bodies through `NoteDocument`; verify `hatch test tests/core/test_integration.py` passes.
- [x] 3.4 Update `AGENTS.md` section 1.3 so `status` is optional until processing begins, update section 1.4 so the Inbox is the `inbox/` folder, and add a short capture paragraph to `README.md`; verify the documented behavior matches the tests and the vocabulary compliance check is clean.

## 4. App state

- [x] 4.1 Add `ui/strings.py` with the welcome, composer, banner, and error copy; verify `hatch run python -c "import afanes.ui.strings"` succeeds and a review finds no user-facing copy constructed inline in the views.
- [x] 4.2 Add `ui/state.py` with the `AppState` singleton, a `reset()` hook, async commands for start, choose, change, refresh, capture, and select, a command lock, `asyncio.to_thread` for blocking work, and banner error translation; add `tests/ui/test_state.py` covering every startup outcome, vault selection and change, capture, ordering, preview body, scan failures, concurrency guarding, and reset; verify `hatch test tests/ui/test_state.py` passes.
- [x] 4.3 Add UI layering assertions to `tests/core/test_architecture.py`: `ui/state.py` must not import views or components, `ui/theme.py` and `ui/strings.py` must be import leaves, and `ui/` must not import `cli/`; verify `hatch test tests/core/test_architecture.py` passes.

## 5. UI shell and Inbox view

- [x] 5.1 Add `ui/theme.py`, the welcome state, the folder picker integration, `ui/app.py`, and `src/afanes/__main__.py`; verify `hatch run python -m afanes` opens the welcome screen, choosing a temporary vault opens the Inbox, and cancelling the picker leaves the welcome state.
- [x] 5.2 Add `ui/views/inbox.py` with the composer, newest-first list, read-only Markdown preview with inert links, failure banner, refresh action, and Change vault action; verify the manual checklist passes: capture a thought, see it first, open it, refresh after an external edit, and change vaults.
- [x] 5.3 Add `tests/ui/test_inbox_view.py` constructing the view with a stub page and asserting the composer, list, preview, banner, and no-op link handler; verify `hatch test tests/ui/` passes.
- [x] 5.4 Update `README.md` with the source-run command, first-run vault selection, the `inbox/` capture rule, and Flet's one-time client provisioning, and correct the installation section so it does not imply a packaged desktop app; verify the documented command runs as written.
- [x] 5.5 Run `hatch check types` after the UI modules land; verify strict mode passes, using narrowly justified casts or ignores only where Flet's public annotations are incomplete, and never weakening the project configuration.
- [x] 5.6 Perform the accessibility and cross-platform review: visible labels, focus order, light and dark behavior, `pathlib` usage, case-insensitive inbox matching, and reserved Windows names; record the results with the change.

## 6. Integration and quality gates

- [x] 6.1 Run `hatch check`; verify it passes.
- [x] 6.2 Run `hatch test --cover`; verify it passes with at least 85% overall coverage.
- [x] 6.3 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass.
- [x] 6.4 Run the vocabulary compliance check from `AGENTS.md` section 6.6; verify it exits clean.
- [x] 6.5 Review `src/` for network clients and verify the only network-dependent step is the documented Flet development provisioning; record that the application performs no runtime network calls.
- [x] 6.6 Run the full capture-loop smoke test from a clean settings state; verify welcome, choose vault, capture, list, preview, refresh, and change vault all behave, and that opening a vault writes nothing to it.

## Workflow follow-up

- Archive the change after review and approval.
- Run the post-archive release workflow: choose the MINOR bump, update the changelog and README, run all gates, and create the release commit.
