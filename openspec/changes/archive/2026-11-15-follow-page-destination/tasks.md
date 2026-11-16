# Tasks

## 1. Destination mapping and selection

- [x] 1.1 Add a `BrowserState` lookup that maps a page path to Inbox, Projects, References, Log, Needs attention, or no destination, using the current snapshot and the browser grouping precedence; verify with unit tests for an inbox note, project, reference, log entry, misplaced note, and missing path.
- [x] 1.2 Add the synchronous page-following selection used while the command lock is held; verify it sets the active destination, clears the query, and leaves the active destination unchanged when the path has no destination.
- [x] 1.3 Refactor `BrowserState.set_section` to share the selection step with page navigation while keeping its lock and Trash retention; verify the existing section-switch and Trash maintenance tests still pass.

## 2. Page navigation

- [x] 2.1 Make `PageNavigator.open_page` follow the loaded page’s destination; verify a state test that opens a reference while Projects is active and asserts References is active.
- [x] 2.2 Make `PageNavigator.back` follow the restored page’s destination and skip missing history entries without changing it; verify tests for project-to-reference Back and an exhausted history.
- [x] 2.3 Verify body links, role names, and ambiguous-reference candidates all route through `open_page` and follow their target; add state tests for an owner reference and a chosen ambiguous candidate.
- [x] 2.4 Verify connection entries follow their target destination; add a page-view test that opens a connection to another destination and asserts the browser selection.
- [x] 2.5 Verify a search result leaves search and shows the result’s destination; add a workspace test that types a query, selects a result, and asserts the query is empty, the destination is active, the destination title is restored, and the row is selected.
- [x] 2.6 Verify opening a managed Trash result selects Trash and clears the query; add or extend a workspace test for the search-result path.
- [x] 2.7 Verify opening an unreadable note leaves the active destination unchanged; add a workspace test for raw rescue mode.

## 3. Review, creation, and manual switching

- [x] 3.1 Remove the Review flow’s local note-type map and redundant section calls; verify the existing open-project and open-reminder tests assert Projects and References.
- [x] 3.2 Make the missing-role-name creation flow follow References after it writes and opens the new note; verify a state test for a reference created from a project role.
- [x] 3.3 Verify browser reference creation still selects References and clears an active query; update the test if the shared selection changes its assertions.
- [x] 3.4 Verify manual destination selection still keeps the open page and selects the chosen destination; add or extend a workspace test for a reference page while Projects is selected.
- [x] 3.5 Verify an unsaved draft keeps the current destination until it is written, as recorded in the design; add a test only if the behavior is not already covered.

## 4. Documentation

- [x] 4.1 Update `docs/guide/workspace.md` for links, search results, Back, and manual destination selection; verify the wording matches the new behavior and the docs build passes.
- [x] 4.2 Update `docs/guide/pages-and-editing.md` for role names, body links, connections, and Back; verify the docs build passes.
- [x] 4.3 Update `docs/develop/interface-standard.md` for the search-result and navigation rule; verify the docs build passes.

## 5. Integration checks

- [x] 5.1 Run `hatch check`, `hatch test --cover`, `hatch run docs:build`, `openspec validate --all --strict`, `openspec doctor`, and the vocabulary compliance greps; verify every command passes.
- [x] 5.2 Run the desktop app with a fixture vault and verify the owner link, body link, connection, search result, Back, Trash result, and manual destination behaviors by hand.
- [x] 5.3 Check keyboard focus after a search result opens; verify focus is not lost and remains on a usable control without changing the destination.

## Workflow follow-up

- Archive the change after implementation and review.
- Run the post-archive release workflow in `AGENTS.md` section 5.3; update the changelog, README, and docs as needed.
- Do not tag, push, or publish unless the maintainer asks.
