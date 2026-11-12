# Tasks

## 1. Make the gate measure the surface

- [x] 1.1 Add a public-surface counter to `tests/core/test_architecture.py` that counts distinct public names (properties, methods, async methods) per class in the state package; verify it reports the current counts from design.md.
- [x] 1.2 Add the confirmed budgets (10 for `AppState`, 25 for any one domain controller) and an allowlist matching today's counts; verify the gate passes.
- [x] 1.3 Add the rule that a class declaring state fields must define at least one public command, with the same allowlist; verify `UiStatus`, `PageEditorState`, `ProcessingState`, and `ReviewState` fail once their allowlist entries are removed.
- [x] 1.4 Add the combined facade check: `AppState` annotated fields plus public command names must stay at or below 10; verify the gate reports the current combined count before the split and fails while it exceeds the budget.

## 2. Extract the state package

- [x] 2.1 Move the classes into `ui/state/` as `status.py`, `session.py`, `browser.py`, `pages.py`, `dialogs.py`, `processing.py`, `review.py`, and `controller.py`, without changing behavior; verify the UI tests pass.
- [x] 2.2 Define `app_state` in `ui/state/__init__.py` without binding `AppState`; verify every `afanes.ui.state.app_state` import still resolves and `afanes.ui.state.AppState` does not.
- [x] 2.3 Update the remaining `afanes.ui.state.AppState` references in tests to `afanes.ui.state.controller.AppState`; verify `hatch check types` passes.
- [x] 2.4 Repoint the architecture tests at the package: the field budget on `controller.py`, the surface counters across the package, and the view-import check over every module; verify the gate passes.
- [x] 2.5 Add `ui/state/lock.py` with the shared `CommandLock` service and wire one instance into every controller.
- [x] 2.6 Add `ui/state/workspace.py` with the `WorkspaceController` shell and `ui/state/navigation.py` with the `PageNavigator` shell; wire both into `AppState` without moving behavior yet.

## 3. Move each domain to its owner

- [x] 3.1 Move the vault lifecycle and refresh commands from `AppState` to `WorkspaceController`; verify `hatch test tests/ui/test_state.py` and the launch tests pass.
- [x] 3.2 Move the browser section and query commands to `BrowserState`; verify the workspace view tests pass.
- [x] 3.3 Move the page draft, edit, save, autosave, conflict, and query commands to `PageEditorState`; move `open_page`, `back`, `follow_link`, `open_failure`, and `history` to `PageNavigator`; and move the label, type/category, repair, unresolved-link, rename, and trash dialog commands to `PageDialogState`; verify the page view tests pass.
- [x] 3.4 Move the processing commands to `ProcessingState`; verify the processing view tests pass.
- [x] 3.5 Move the review commands to `ReviewState`; verify the review view tests pass.
- [x] 3.6 Update `ui/views/` and `ui/app.py` call sites to the owning controller; verify no view still calls a removed `AppState` member.
- [x] 3.7 Move message, busy, and session-flag mutation to `UiStatus` commands; verify the status flags still drive the banner and busy indicator and `UiStatus` passes the anemic-bag rule.
- [x] 3.8 Remove public setters and other public names that no view, app, or test references, keeping `reset`; verify the audit reports zero unreferenced names.

## 4. Tighten and document

- [x] 4.1 Delete the allowlist; verify the gate passes with the confirmed budgets and no exemptions.
- [x] 4.2 Update `AGENTS.md` 4.2 (formerly 4.3) so the stated rule matches the test constants; verify the wording names all three budgets.
- [x] 4.3 Add the `Unreleased` changelog entry with the Python API migration (the singleton keeps its path; the type moves to `ui/state/controller.py`; commands move to the domain controllers); verify each moved entry names its replacement.

## 5. Integration checks

- [x] 5.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the 6.6 compliance check; verify all pass.
