# Tasks

## 1. Feedback state model

- [x] 1.1 Add `NoticeAction` and a frozen slotted `Notice` to `src/afanes/ui/state/status.py`, add the transient `notice` field and `show_notice`, `take_notice`, and `clear_notice` to `UiStatus`, and keep the existing message slot temporarily so the tree stays green; verify focused tests cover latest-wins, consume-once, and reset, and `hatch test tests/ui/test_state.py` passes.
- [x] 1.2 Add one owned banner field or property to `WorkspaceController`, `VaultSession`, `PageEditorState`, and `ProcessingState`; derive the page banner from its existing conflict and blocking state; verify one focused test per owner sets and clears its banner without touching another owner.
- [ ] 1.3 Add a focused `tests/ui/test_feedback.py` for the notice lifecycle and owner-banner isolation; verify `hatch test tests/ui/test_feedback.py` passes.

## 2. Toast presenter and shell wiring

- [x] 2.1 Add `src/afanes/ui/components/toast.py` with a `ToastPresenter` that wraps Flet `SnackBar`, closes only its own current snackbar, and exposes `show` and `close`; add the toast surface, text, action, duration, margin, and padding tokens to `theme.py`; verify focused tests cover show, replacement, action, dismissal, and that `pop_dialog` is never called.
- [x] 2.2 Add an `on_notice` callback to `WorkspaceActions`, consume `take_notice()` in `WorkspaceView`, and own the presenter in `AppShell`; verify `tests/ui/test_workspace_view.py` and `tests/ui/test_app.py` pass with a fake presenter.
- [ ] 2.3 Render the toast in both appearance modes with the themed tokens; verify `hatch test tests/ui/test_theme.py tests/ui/test_conformance.py` passes and the conformance baseline does not grow.

## 3. Core trash return and restore

- [ ] 3.1 Change `VaultNaming.trash` to return the `TrashPreview` it actually used instead of an integer, update the processing caller that ignores it, and verify `hatch test tests/core/vault/test_naming.py tests/core/vault/test_processing.py tests/core/test_processing.py` passes.
- [ ] 3.2 Add `VaultNaming.restore_from_trash(preview, confirm=True)` with vault containment, missing-trash refusal, occupied-source refusal, parent creation, and an exclusive publish that never overwrites; verify focused tests cover success, collision, missing file, path escape, and no overwrite.
- [ ] 3.3 Verify a restored note's inbound references resolve on the next scan and a collision leaves the trash file byte-identical; run `hatch test tests/core/vault/test_naming.py tests/core/vault/test_service.py`.

## 4. Immediate trash flow

- [ ] 4.1 Replace `PageDialogState.begin_trash`, `apply_trash`, and `cancel_trash` with one immediate trash command and an `undo_trash` command, keep one in-memory undo record, and emit the moved, restored, and failure notices; verify focused state tests cover immediate move, undo, collision, replacement by a second trash, and restart loss.
- [ ] 4.2 Update `PageView` so the Trash menu action calls the immediate command, remove its trash confirmation methods and panel wiring, delete `TrashPanel` from `page_panels.py`, and verify `hatch test tests/ui/test_page_view.py` passes.
- [ ] 4.3 Update the copy: `PAGE_TRASH` loses its ellipsis, remove `PAGE_TRASH_TITLE`, `PAGE_TRASH_BODY`, and `PAGE_TRASH_CONFIRM`, add the moved, restored, failure, and Undo constants, update the copy-gate classifications and `ELLIPSIS_ACTIONS`, and verify `hatch test tests/ui/test_copy.py` passes.
- [ ] 4.4 Remove the `TrashPanel` entry from the conformance baseline, verify the baseline still only shrinks, and run `hatch test tests/ui/test_conformance.py`.

## 5. Feedback migration

- [ ] 5.1 Migrate `PageEditorState` and `PageDialogState` to the new channels: conflict and blocking state to the page banner, partial rewrite reports to the page banner, one-time failures to notices, and category and rename validation inline; verify focused tests cover a conflict across a background refresh and a failed save as a notice.
- [ ] 5.2 Migrate `VaultSession`, `WorkspaceController`, `PageNavigator`, `ReviewState`, and `ProcessingState`: refresh failures to owner banners, one-time failures to notices, and form failures inline; verify the review form and processing form still show their own errors and the post-processing refresh failure uses the processing banner.
- [ ] 5.3 Render the owned banners in the workspace shell and the page view, remove the duplicate status-message banners from the inbox, review, and processing views, and verify a background refresh preserves each banner and each notice.
- [ ] 5.4 Remove `UiStatus.message` and `show_message` after every call site is migrated, update the remaining tests, and verify `grep -rn "show_message\|status.message" src tests` returns no output and the full suite passes.

## 6. Overlay audit

- [ ] 6.1 Audit every `AppShell` dialog for initial focus, Esc dismissal, Cancel before the affirmative action, a specific affirmative label, and no destructive default; add focused tests with the fake page and verify `hatch test tests/ui/test_app.py` passes.
- [ ] 6.2 Audit the primary and page menus for Esc dismissal and low complexity; add or update focused tests and verify `hatch test tests/ui/test_workspace_view.py` passes.
- [ ] 6.3 Verify the toast, dialogs, menus, and inline panels follow the new overlay requirements and that no inline confirmation panel was moved into a modal.

## 7. Documents and gates

- [ ] 7.1 Update `AGENTS.md` 4.5 and 4.6 so a destructive action requires a confirmation or a visible undo path, trash is immediate and undoable, and the feedback channels are named; verify the old confirmation wording is gone.
- [ ] 7.2 Update `docs/develop/interface-standard.md` with the feedback channels, the toast and banner rules, the overlay audit, the trash undo, and wave 4 marked landed; verify `hatch run docs:build` passes.
- [ ] 7.3 Update the guide pages that describe trash, editing, inbox, review, processing, and workspace behavior; verify quoted labels match the catalog and `hatch run docs:build` passes.
- [ ] 7.4 Add one `Unreleased` changelog entry naming the change, the feedback channels, the trash undo, the `VaultNaming.trash` return change, `restore_from_trash`, the `UiStatus.show_message` removal, and `README: no change required` / `Docs: updated`; verify no version bump.
- [ ] 7.5 Run `hatch check`, `hatch test --cover`, `hatch run docs:build`, `openspec validate --all --strict`, `openspec doctor`, both vocabulary greps, and `git diff --check`; verify coverage stays at or above 85%.
- [ ] 7.6 Review the final diff for scope: no vault schema, `afanes.yaml`, trash frontmatter, retention, sidebar, dependency, CLI, or runtime-network change.

## Workflow follow-up

- Archive `establish-writing-style` before this change so the main `interface-theme` baseline includes
  the writing-style requirements and the copy gate.
- Archive this change after the maintainer approves and every task is complete.
- Run the post-archive release workflow and record the version, README status, and docs status.
- Plan the trash-room change separately; it owns the sidebar, the 30-day purge, the trash frontmatter, and the schema binder.
