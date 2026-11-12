# Tasks

## 1. Align the documentation with the current implementation

- [x] 1.1 Rewrite the `## Purpose` paragraph in `openspec/specs/processing/spec.md`, `openspec/specs/project-overview/spec.md`, and `openspec/specs/reference-categories/spec.md` so each matches its requirement text (no retired action note, no `project` frontmatter attribution, no category-selected scheme). Verify with `grep -n -i "action note\|project frontmatter\|selects the reference scheme" openspec/specs/*/spec.md` returning nothing and `openspec validate --all --strict` passing.
- [x] 1.2 Bring `AGENTS.md` 3.1 and 3.2 in line with the real tree (`views/page.py`, `views/projects.py`, `views/review.py`, `models/step.py`, `core/steps.py`, `core/editing.py`, `core/templates.py`, `cli/strings.py`, `cli/vault.py`) and annotate the SQLite indexer, `cli/index.py`, and `cli/doctor.py` as planned rather than present. Verify every path listed in 3.1 exists or is marked planned.
- [x] 1.3 State in `AGENTS.md` 4.10 that the cache rules take effect when the SQLite cache exists, keeping every existing rule intact. Verify by reading the section and confirming no rule, limit, or gate was removed.

## 2. Produce a packaged desktop build

- [x] 2.1 Confirm the src-layout project builds with `hatch run flet build linux --build-version "$(hatch version)"`; when the build rejects the layout or the dynamic version, add the minimum build metadata or launcher that reuses the existing entry point instead of duplicating it. Verify an artifact appears under `build/linux/`.
- [x] 2.2 Document the build command, the Flutter SDK prerequisite, the per-platform build rule, the version flag, the output directory, and the offline launch check in `README.md`. Verify the documented commands run exactly as written on Linux.
- [x] 2.3 Launch the built artifact with networking unavailable and confirm the window opens, a vault captures a note, and the reported version equals `hatch version`. Verify the note written by the packaged app is identical to the one a source run writes.

## 3. Detect vault changes cheaply

- [x] 3.1 Add `Vault.scan_fingerprint()` with a strict NumPy-style docstring and tests in `tests/core/test_vault.py`: stable for an unchanged vault, different after an edit, an addition, and a removal, and unchanged by a file under `trash/` or a hidden directory. Verify the new tests pass and the existing vault tests still pass.
- [x] 3.2 Store the fingerprint applied with each scan in `VaultSession` and add `refresh_if_changed()` that returns the new snapshot only when the fingerprint moved. Verify with tests in `tests/ui/test_state.py` that an unchanged vault returns `None` without a scan, and that a touched file triggers exactly one scan.
- [x] 3.3 Add the proposed `REFRESH_SECONDS` interval constant beside `AUTOSAVE_SECONDS` and document why it exists. Verify the constant is the only interval the new loop reads.

## 4. Follow external edits in the open page

- [x] 4.1 Add `AppState.refresh_workspace()` that skips while the command lock is busy, does not set the busy indicator, returns whether anything changed, and leaves a processing or review flow untouched. Verify with tests in `tests/ui/test_state.py` for a busy lock, no vault, and a pending processing plan.
- [x] 4.2 Apply the open-page rule: a clean draft reloads the current content, a dirty draft raises `conflict = "changed"` without touching the draft, and a missing file raises `conflict = "missing"`. Verify with tests that reuse the existing reload, overwrite, recreate, and discard actions and their `PAGE_CONFLICT_*` copy.
- [x] 4.3 Keep a message raised by a user command across a background apply while a command-driven apply still clears it. Verify with a test that sets `status.message`, refreshes in the background, and asserts it survives, plus a test that a capture still clears it.
- [x] 4.4 Confirm a background refresh writes nothing: assert no file mtime changes after `refresh_workspace()` on a changed vault. Verify the test fails if the refresh path is pointed at a write.

## 5. Run the refresh loop

- [x] 5.1 Start exactly one refresh task when a session is claimed and cancel it on vault close, on session release, and when the workspace is replaced. Verify with tests in `tests/ui/test_app.py` that a second start does not create a second task and that a closed vault leaves no running task.
- [x] 5.2 Add a public `WorkspaceView.refresh()` that rebuilds the dynamic lists from state and repaints, and call it from the shell only when `refresh_workspace()` reports a change. Verify with `tests/ui/test_workspace_view.py` that one repaint follows one reported change and that the view performs no file I/O.
- [x] 5.3 Confirm a second browser session starts no loop and scans nothing, reusing the existing session notice. Verify with a test that a rejected session creates no refresh task.

## 6. Integration and gates

- [x] 6.1 Add an integration test in `tests/core/test_integration.py` that creates a vault, captures a note, edits it directly on disk, and asserts the browser and project rows reflect the change after `refresh_workspace()` without an explicit refresh. Verify the test passes with `hatch test tests/core/test_integration.py`.
- [x] 6.2 Run `hatch check`, `hatch test --cover` (85% minimum), `openspec validate --all --strict`, `openspec doctor`, and the vocabulary check from AGENTS 6.6; fix findings rather than waiving them. Verify each command exits successfully.
- [x] 6.3 Record the packaged-artifact and refresh checks for macOS and Windows, where the maintainer runs them, and state which platform was verified here. Verify the README claims match the platforms actually checked.

## Workflow follow-up

- Archive the change after review, then run the post-archive release workflow in AGENTS 5.8.
- Decide whether the packaged build completes the milestone and therefore justifies a version bump, and update `CHANGELOG.md` with the packaged-build, refresh, and documentation outcomes.
