# Tasks

## 1. Core read model and queries

- [x] 1.1 Add `due_date: datetime.date | None` to `VaultNote` and extract it during `Vault.scan`, treating absent, null, and invalid values as no date; verify normal, absent, null, and invalid cases in `tests/core/test_vault.py`.
- [x] 1.2 Add `core/search.py` with browser grouping and title/identity filtering over a `VaultSnapshot`; verify type groups, Inbox-only captures, trash exclusion, failures, case-insensitive matching, and body-only terms in `tests/core/test_search.py`.
- [x] 1.3 Add project summaries to `core/search.py`, including open/closed status rules, action attribution through unique `project` resolution, open counts, later-action exclusion, and deterministic next-action ordering; verify each rule in `tests/core/test_search.py`.
- [x] 1.4 Add the review queue and pending count to `core/search.py`, ordered as Inbox notes, stalled projects, then healthy open projects, with closed projects excluded and a snapshot queue; verify order, counts, and zero state in `tests/core/test_search.py`.

## 2. Workspace shell and browser

- [x] 2.1 Replace the Inbox screen route with a `WorkspaceView` that keeps a sidebar visible beside a main area switching between the page pane, processing, and review; verify welcome, vault selection, and page rendering in `tests/ui/test_app.py` and a new `tests/ui/test_workspace_view.py`.
- [x] 2.2 Add the capture bar at the top of the workspace and preserve capture, clear-on-success, and error behavior; verify capture still creates an Inbox note and updates the browser in `tests/ui/test_workspace_view.py` and `tests/ui/test_state.py`.
- [x] 2.3 Build the type-grouped sidebar with section counts, Inbox-only captures, failures section, and selection that opens the shared page pane; verify groups, counts, failure rescue, and Back history in `tests/ui/test_workspace_view.py` and `tests/ui/test_state.py`.
- [x] 2.4 Add the title/identity search field and filtered results without body reads; verify title, identity, case/whitespace matching, empty results, and no-match body-only terms in `tests/ui/test_workspace_view.py`.
- [x] 2.5 Add workspace copy, dimensions, and accessibility labels to `ui/strings.py` and `ui/theme.py`; verify the new view tests and `hatch check` pass.

## 3. Projects workspace

- [x] 3.1 Add the Projects section with Active, Waiting, Later, and collapsed Closed groups, including no-status projects under Active; verify grouping and collapse behavior in `tests/ui/test_projects_view.py`.
- [x] 3.2 Render project rows with status, optional due date, open action count, and computed next action; verify dates, zero counts, later-action exclusion, and next-action display in `tests/ui/test_projects_view.py`.
- [x] 3.3 Wire project selection to the shared page pane and refresh summaries after actions, saves, renames, and trash; verify counts and next action recompute in `tests/ui/test_projects_view.py` and `tests/ui/test_state.py`.
- [x] 3.4 Add a core regression test that completing every action does not close a project and that closing a project does not change its actions; verify in `tests/core/test_search.py` or `tests/core/test_integration.py`.

## 4. Guided review

- [x] 4.1 Add the Review entry with pending count and zero state to the sidebar; verify count composition, updates after processing, and no session when zero in `tests/ui/test_workspace_view.py` and `tests/ui/test_state.py`.
- [x] 4.2 Add the review session state and snapshot queue, including current item, skipped items, Next, Skip, and completion summary; verify order, snapshot behavior, advancement, skipping, and restart behavior in `tests/ui/test_state.py`.
- [x] 4.3 Embed the existing Processing Wizard in the review main area for Inbox items and advance after a confirmed apply; verify apply, cancel, and non-inference behavior in `tests/ui/test_review_view.py` and `tests/ui/test_state.py`.
- [x] 4.4 Add the project review card showing title, status, due date, next action, and other open actions, with actions to open the project or next action; verify each rendering and navigation in `tests/ui/test_review_view.py`.
- [x] 4.5 Add stalled-project choices for creating a next action, marking done, deferring to later, and skipping, with confirmation for each write; verify mark done, defer, skip, and cancel in `tests/ui/test_review_view.py` and `tests/ui/test_state.py`.

## 5. Next-action creation

- [x] 5.1 Add `Vault.create_project_action` with a required title, project reference, optional status, due date, people, exact-name collision handling, path containment, and atomic write; verify success, blank title, collision, invalid metadata, and containment in `tests/core/test_vault.py`.
- [x] 5.2 Add the next-action form and `AppState` command for a stalled project, refreshing the project summary and advancing the review after a confirmed create; verify create, cancel, validation error, and refreshed next action in `tests/ui/test_review_view.py` and `tests/ui/test_state.py`.
- [x] 5.3 Verify that next-action creation during review writes only the new action, preserves the project note, and does not auto-change any status; add the regression test in `tests/core/test_integration.py`.

## 6. Integration and documentation

- [x] 6.1 Add an end-to-end test with a demo-like vault that opens a project from the browser, processes an Inbox item through review, creates a next action for a stalled project, and confirms the resulting files and refreshed browser; verify in `tests/core/test_integration.py`.
- [x] 6.2 Update `README.md` with the browser, Projects view, Review session, nested note grouping, and title/identity search limitations; verify the documented commands and workflows match the implementation.
- [x] 6.3 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the vocabulary compliance check; fix every failure before reporting the change complete.

## Workflow follow-up

- Archive the change after review and validation are complete.
- Run the post-archive release workflow from `AGENTS.md` section 5.8.
