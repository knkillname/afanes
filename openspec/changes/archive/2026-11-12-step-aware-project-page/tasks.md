# Tasks

## 1. Core project body model

- [x] 1.1 Add `afanes.core.project_body` with `ProjectBody`, prose blocks, step-list blocks, and step entries; verify a simple prose-and-task-list body returns blocks in source order with `tests/core/test_project_body.py`.
- [x] 1.2 Preserve nested task items and indented detail lines in the block model; verify depth and detail fixtures in `tests/core/test_project_body.py`.
- [x] 1.3 Implement the conservative fallback for mixed lists, blockquotes, tables, fenced code, and shapes that cannot be separated safely; verify each fixture renders as a prose block with unchanged source text.
- [x] 1.4 Add property tests that every source line is accounted for once and CRLF/LF bodies round-trip through block extraction; verify with Hypothesis in `tests/core/test_project_body.py`.

## 2. Page state and metadata writes

- [x] 2.1 Add a `page_body_blocks` property to `PageEditorState`; verify project pages return blocks and non-project pages return an empty tuple in `tests/ui/test_state.py`.
- [x] 2.2 Add a `StepEdit` value object and one `edit_page_step_metadata` command to `PageEditorState`; verify plan set, plan clear, owner add, owner remove, multiple owners, unknown-key preservation, and unchanged `actual` and tags.
- [x] 2.3 Add a `force` flag to `PageEditorState.autosave` and a `save_page_due_date` command to `PageDialogState`; verify read-mode due-date set, clear, invalid-date rejection, body preservation, and conflict handling.
- [x] 2.4 Run the architecture gate and verify `PageEditorState` has at most 25 public names, `PageDialogState` stays within budget, and `AppState` gains no field.

## 3. Step-aware body rendering

- [x] 3.1 Add theme tokens and strings for the accent step surface, on-accent text, muted actions, link decoration, owner panel, and date actions; verify no hardcoded colors or pixel values appear in the new view.
- [x] 3.2 Add `ui/views/project_body.py` to render prose blocks with `ft.Markdown` and each step-list block as one accent card; verify prose-step-prose order and fallback rendering in `tests/ui/test_project_body_view.py`.
- [x] 3.3 Render each step row as a checkbox plus separate Markdown text with a semantics label and structured metadata details; verify raw link syntax is absent, internal links open their target, and external links stay inert.
- [x] 3.4 Delegate the project read body to the new view and remove the separate Steps panel; verify a project page shows one step surface and a non-project page still renders ordinary Markdown.
- [x] 3.5 Set `GITHUB_FLAVORED` on the non-project page Markdown and `ProcessingView.capture_body`; verify task-list checkboxes render in both tests.

## 4. Inline step actions

- [x] 4.1 Add a date-picker callback from the application shell through `WorkspaceView` to `PageView` and the project-body view; verify tests use a fake picker and a desktop/web smoke run reaches the picker.
- [x] 4.2 Add always-visible muted person and calendar actions with tooltips and semantics labels, emphasized on hover and keyboard focus; verify the actions exist at rest and remain reachable without hover.
- [x] 4.3 Wire the calendar action to the picker and a clear action; verify plan set and clear call the page command and a failed write keeps the previous metadata.
- [x] 4.4 Add the inline owner manager with removable chips, an add field, and note-name suggestions from `assignment_candidates`; verify multiple owners, last-owner removal, and free-form names.
- [x] 4.5 Verify step action writes respect the existing conflict guard, refresh the snapshot, and leave every other step line byte-identical.

## 5. Project meta row

- [x] 5.1 Add a project meta row under the page title with status and optional due date; verify a project shows both and a note or reference shows neither.
- [x] 5.2 Wire the due-date calendar action and clear action to the read-mode write command; verify set, clear, invalid rejection, and unchanged body content.
- [x] 5.3 Verify the edit-mode due-date field remains available and read-mode and edit-mode writes produce the same frontmatter shape.

## 6. Integration and documentation

- [x] 6.1 Add integration tests covering prose-step-prose order, step link navigation, owner and plan edits, project due date, and reload after an external edit; verify all pass in `tests/core/test_integration.py`.
- [x] 6.2 Update `README.md` for the step-aware project page, inline actions, and project meta row; verify the documented behavior matches the new tests.
- [x] 6.3 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the vocabulary compliance greps; verify all pass with coverage at or above 85%.
- [x] 6.4 Review macOS, Linux, and Windows parity for the date picker, hover/focus/touch actions, keyboard navigation, and light/dark contrast; verify the notes in `design.md` stay accurate.

## Workflow follow-up

- Archive this change after implementation review and a green gate run.
- Run the post-archive release workflow in `AGENTS.md` section 5.3.
