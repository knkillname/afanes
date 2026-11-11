# Proposal

## Why

Afanes can capture, process, and open pages, but the application shell exposes only the Inbox. Projects, actions, people, and references exist in the vault yet are unreachable unless an Inbox note happens to link to them. The result is a personal wiki that cannot be browsed and a project list that cannot be seen.

This change adds the missing workspace layer: a browser over the whole vault, a Projects workspace that shows every open project with its next step, and a guided Review queue that walks pending Inbox items and project next steps in one session.

## What Changes

- Replace the single Inbox screen with a workspace shell that keeps a navigation sidebar and the page pane visible together.
- Add a vault browser grouped by note type: Inbox, Projects, Actions, People, References, and Notes. Selecting any entry opens it in the page pane.
- Add title-and-identity search to the browser. Full-text body search is deferred to the indexer change.
- Add a Projects view grouped by status, showing due date, open action count, and the next action for each project. Closed projects are available in a collapsed group.
- Add a Review entry with a pending count. A review session walks pending Inbox items first, then projects that need a next step, then healthy projects for a quick confirmation.
- Reuse the existing Processing Wizard for Inbox items in a review session.
- Add a project review card that shows the current next action, lets the user open another open action, or creates a new action linked to the project when no next step exists.
- Expose `due_date` on scanned notes and add read-only project and review queries over the vault snapshot.
- Update the README to describe the browser, Projects view, and Review session.

Assumptions recorded for review:

- “Open project” means a project whose status is absent, `active`, `waiting`, or `later`. `done`, `cancelled`, and `archived` are closed.
- “Open action” means an action whose status is absent, `active`, or `waiting`. A `later` action is deferred and does not count as an open action or a next step.
- A project's next action is computed, not stored: the open action with the earliest due date, then `active` before `waiting`, then title. No new frontmatter field is introduced.
- The review queue is snapshotted when the session starts. Notes created during the session appear in the browser immediately and in the next review session.

## Capabilities

### New Capabilities

- `vault-browsing`: The persistent navigation shell, the type-grouped browser over every parsed note, title-and-identity search, and opening any entry in the page pane.
- `project-overview`: The Projects view, status grouping, open/closed rules, due dates, open action counts, computed next action, and project membership through the `project` frontmatter reference.
- `guided-review`: The Review entry, pending count, sequential queue over Inbox items and open projects, reuse of the Processing Wizard, and the project next-step card and action creation flow.

### Modified Capabilities

- None. Existing Inbox capture, processing, link, identity, layout, and page-editing behavior is preserved; this change adds navigation and review surfaces over it.

## Impact

- **UI**: new workspace shell and browser sidebar; Projects and Review views; the Inbox list becomes one section of the browser; the page pane remains the shared read/edit surface.
- **State**: `AppState` gains the active workspace section, all-note query results, project summaries, and review-session state.
- **Core**: `VaultNote` gains `due_date`; `core/search.py` gains read-only project and review queries over `VaultSnapshot`. No SQLite schema or cache change is required for this change.
- **Models**: no new note type, frontmatter key, or status value.
- **Dependencies**: none. The change uses the existing Flet controls and standard library only.
- **Platforms**: macOS, Linux, and Windows use the same layout and queries; no path or platform-specific behavior is introduced.
- **Deferred**: full-text body search, tabs, folder-tree navigation, a saved “last reviewed” timestamp, project status cascades to actions, and a global New Page action.
