# Tasks

## 1. Workspace guard

- [x] 1.1 Add the private `_own_controls` tree walk to `WorkspaceView` and call it at the start of `_refresh_dynamic` and `_set_working`; verify `hatch test tests/ui/test_workspace_view.py` passes.
- [x] 1.2 Add regression tests for a frozen section tile and a frozen sidebar count, covering a direct section switch and a background-style refresh; verify each test fails with `RuntimeError: Frozen controls cannot be updated.` when the guard is removed and passes with it.
- [x] 1.3 Add a scope test proving a frozen control outside the workspace tree keeps its marker after a refresh; verify `hatch test tests/ui/test_workspace_view.py` passes.
- [x] 1.4 Confirm the fix needs no user-facing documentation change and record `Docs: no change required`; verify no `docs/` edit is added by this change.

## 2. Integration

- [x] 2.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, and `openspec doctor`; verify all pass and coverage remains at or above 85 percent.
- [x] 2.2 Run `hatch run afanes` and switch browser sections after startup and after an external vault change; verify no `Frozen controls cannot be updated` error appears and the sidebar stays responsive.

## Workflow follow-up

- Apply the change with `/opsx-apply` after approval.
- Archive the change after implementation, review, and the project gates pass.
