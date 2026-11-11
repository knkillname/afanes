# Design

## Context

The application shell in `ui/app.py` routes between the welcome screen, `InboxView`, and the full-screen Processing Wizard. `InboxView` owns a note list, a composer, and the shared `PageView`; it lists only `VaultSnapshot.inbox_notes()`. `AppState` already keeps the full `VaultSnapshot` privately and owns the page session, history, conflicts, and processing state.

`VaultSnapshot` contains every parsed note plus the name catalog. `VaultNote` carries type, category, status, references, and modified time, but not `due_date`. `Vault.plan_rename`, `Vault.plan_trash`, and `Vault.plan_reference_repair` already provide confirmed write flows. `core/search.py` and `core/indexer.py` do not exist yet; there is no SQLite cache and no full-text search.

Flet 1.1.2 provides `NavigationRail`, `NavigationBar`, `Tabs`, and `SearchBar`, but the browser needs grouped sections with counts, so a custom sidebar is simpler than a flat rail.

## Goals / Non-Goals

**Goals:**

- One persistent workspace: browser sidebar, main content area, and a fast capture entry.
- A type-grouped browser over every parsed note with title/identity search and failure access.
- A Projects workspace with deterministic open/closed rules, action attribution, counts, and a computed next action.
- A guided review session that reuses the Processing Wizard for Inbox items and adds a project next-step card.
- All queries read-only over the existing scan; no new dependency, schema, or frontmatter field.

**Non-Goals:**

- Full-text body search and the SQLite indexer.
- Tabs, plugins, calendar/journal pages, folder-tree navigation, or a global New Page action.
- A stored “next action” pointer or “last reviewed” timestamp.
- Automatic project status changes or action cascades.
- Persisting a review session across application restarts.

## Decisions

### Workspace composition

Create `WorkspaceView` in `ui/views/workspace.py` that composes three regions:

```text
+---------------------------------------------------------------+
| Capture bar (always available)                                |
+----------------------+----------------------------------------+
| Browser sidebar      | Main area                              |
|  Review (n)          |  page pane while browsing              |
|  Inbox (n)           |  Processing Wizard during processing  |
|  Projects (n)        |  Review card during a review           |
|  Actions (n)         |                                        |
|  People (n)          |                                        |
|  References (n)      |                                        |
|  Notes (n)           |                                        |
+----------------------+----------------------------------------+
```

`ui/app.py` renders `WorkspaceView` whenever a vault is open. The old `InboxView` split is retired as a screen; its composer becomes a `CaptureBar` component, and its list becomes the browser's Inbox group. `PageView` and the Processing Wizard are reused as main-area controls.

Alternative considered: keep separate full-screen routes for Inbox, Projects, and Review. That would hide the browser during focused work and contradict the workspace requirement.

### Sidebar is grouped by type, not folders

The sidebar groups notes as Inbox, Projects, Actions, People, References, and Notes. Captures appear only under Inbox. `trash/` is absent. Failures appear in a separate section below the groups.

Rationale: identity is the filename stem and folders classify only; type groups match the workflow and avoid exposing storage accidents such as deeply nested reference folders. A folder-tree toggle is deferred.

Alternative considered: mirror the filesystem tree like a traditional desktop wiki. It is familiar, but it makes `reference/people/older/` part of navigation and duplicates the type information already in frontmatter.

### Read-only queries live in `core/search.py`

Add a new `core/search.py` with pure functions and small frozen value objects over `VaultSnapshot`:

- `browse_groups(snapshot)` returns the type-grouped browser entries and failures.
- `filter_notes(notes, query)` matches display title or identity using `normalize_name`.
- `project_summaries(snapshot)` returns one summary per project with open actions and a computed next action.
- `review_queue(snapshot)` returns Inbox items, stalled projects, then healthy projects.

The UI calls `AppState` commands; it does not compute groupings or resolve project membership. No SQLite schema is added. The snapshot is already materialized and refreshed off the UI thread; this is sufficient for the current vault scale and keeps the cache disposable.

Alternative considered: add the indexer now and query SQLite. That adds schema, migration, rebuild, and failure modes before the product shape is validated.

### Expose `due_date` on scanned notes

Extend `VaultNote` with `due_date: datetime.date | None`. `_read_note` reads the raw `due_date` value from the parsed document: a YAML date or a valid ISO string becomes a date; absent, null, or invalid values become `None` so the scan continues. The page editor remains the place that reports invalid due-date text.

Alternative considered: re-read each file when the Projects view opens. That duplicates parsing and makes sorting and counts expensive.

### Project membership resolves through the catalog

For each action with a `project` frontmatter reference, resolve it against `snapshot.catalog`. Only a unique resolution counts as project membership. Body links, unresolved references, and ambiguous references are ignored for step counts; they remain visible in the page body and backlinks.

`ProjectSummary` contains the project note, open actions, next action, and counts. Open project statuses are absent, `active`, `waiting`, and `later`. Open action statuses are absent, `active`, and `waiting`; `later` is deferred and excluded. Next action ordering is earliest due date, then `active` before `waiting`, then normalized display title.

Alternative considered: a `next_action` frontmatter pointer on the project. It is explicit but creates two sources of truth and a rewrite problem when the action is renamed or trashed. Compute it for now and revisit if users need manual ordering.

### Review state lives in `AppState`

`AppState` gains `active_section`, browser query results, project summaries, and a `ReviewSession` value object holding a snapshotted tuple of `ReviewItem` values, the current index, and skipped paths. `ReviewItem` distinguishes an Inbox path from a project summary. Starting review builds the queue once; applying a processing outcome, creating a next action, closing or deferring a project, Next, and Skip advance the session. The session is intentionally not persisted.

The existing `processing_note`, `processing_plan`, and `processing_result` fields remain the source of truth while an Inbox item is open. The review layer only sequences items and shows the completion summary.

Alternative considered: a separate `ReviewController` singleton. The project has one permitted mutable `AppState`; adding another mutable controller would violate that boundary.

### Creating a next action is a core service method

Add a `Vault.create_project_action(...)` operation that accepts a title, the project reference, and optional status, due date, and people. It validates the project reference and metadata, builds the canonical action document with `project:`, writes atomically under `actions/`, and returns the path. The review card collects the values; it does not build YAML.

Name collisions use the existing safe-name policy. A failed validation or write leaves the project unchanged and reports a message in the review card.

Alternative considered: route creation through the link-draft flow. That flow starts from a missing reference and forces an identity from a link; it does not collect a fresh action title or project metadata.

### Capture entry stays fast

A `CaptureBar` at the top of the workspace preserves the existing capture behavior: first non-blank line becomes the filename and heading, the note is written under `inbox/`, and the field clears on success. It uses the existing `AppState.capture` command. The Inbox group updates from the next scan.

Alternative considered: put the composer inside the sidebar. A 280-pixel sidebar is too narrow for the multiline composer and would compete with the browser.

## Risks / Trade-offs

- **Workspace refactor breaks existing Inbox behavior** → Keep `PageView`, the Processing Wizard, and the capture command intact; update Inbox and app tests to exercise the new composition.
- **Ambiguous or unresolved project references make actions invisible** → Document that only unique resolution counts; keep the page body and backlinks visible; consider an “Unassigned actions” review section in a later change.
- **Computed next action can feel arbitrary** → Show every open action on the project card and allow opening another action; do not write the computed choice into the vault.
- **Review queue can be long** → Snapshot the queue, make Skip cheap, and count only Inbox plus stalled projects in the badge.
- **Scan-based queries get slower on large vaults** → Keep refresh and query work off the UI thread; the indexer change can replace the query source without changing the spec.
- **Creating an action during review adds a new write path** → Reuse the vault's containment, collision, and atomic-write rules; test cancellation, blank titles, collisions, and metadata validation.
- **Title/identity search is weaker than full-text** → State the limitation in the UI and README; full-text search is a follow-up with the indexer.

## Migration Plan

- No data migration and no new frontmatter fields. Existing vaults open unchanged; `due_date` is read from existing notes.
- No cache migration because this change does not use SQLite.
- Rollout order: expose `due_date` and `core/search.py`, add the workspace shell and browser, add the Projects view, add the Review session, then update README and integration tests.
- Rollback is a code revert. Actions created through a confirmed review remain ordinary Markdown notes and need no cleanup.

## Open Questions

- Folder-tree navigation and tabs are deferrable; the type-grouped browser is the chosen first shape.
- Full-text search belongs to the indexer change; the browser search is title/identity only for now.
