# Tasks

## 1. Shared capture loading

- [x] 1.1 Add `ProcessingState.load(path)` to read the capture body and template card catalog into the wizard fields, and make `begin()` use it; verify the existing begin tests pass with `hatch test tests/ui/test_state.py -k "begin_processing"`.
- [x] 1.2 Replace the duplicated capture setup in `ReviewState._enter_current_review_item()` with `ProcessingState.load()` while keeping the skip-on-failure behavior; verify `hatch test tests/ui/test_state.py -k "review"` passes.
- [x] 1.3 Add state tests for review start and review advance that assert the valid template cards are loaded; verify `hatch test tests/ui/test_state.py` passes.

## 2. Template picker refresh

- [x] 2.1 Rebuild `ProcessingView.template.options` from the current catalog in `_refresh_dynamic()`, preserve a still-valid selection, and fall back to Empty when the selected card disappeared; verify the existing processing view tests pass with `hatch test tests/ui/test_processing_view.py`.
- [x] 2.2 Add view tests for card changes on refresh, selection preservation, and the Empty fallback; verify `hatch test tests/ui/test_processing_view.py` passes.

## 3. Integration checks

- [ ] 3.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, and `openspec doctor`; verify all pass and coverage remains at or above 85 percent.
- [ ] 3.2 Run the AGENTS.md section 6.1 vocabulary grep commands; verify each exits with no output. Record `Docs: no change required` because the existing documentation already states that the Template field lists every valid card plus Empty.

## Workflow follow-up

- Apply the change with `/opsx-apply` after approval.
- Archive the change after implementation, review, and the project gates pass.
