# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Writing style and copy gate.** Interface and command-line copy now follows the GNOME writing
  style: header capitalization for headings and short control labels, sentence capitalization for
  field labels and prose, no final period, neutral tone without first- or second-person pronouns,
  typographic apostrophes, and one-character ellipses. Ellipses mark only actions that open further
  input or a confirmation, and the picker titles and rename preview keep their own labels so the
  ellipsis stays unambiguous. A new no-baseline gate, `tests/ui/test_copy.py`, classifies every copy
  constant and checks both catalogs. Visible labels changed, so the shipped screenshots are
  refreshed with the wave 7 identity work. This implements the `establish-writing-style` OpenSpec
  change. README: no change required. Docs: updated.
- **Unified MVP gate.** `RELEASE.md` now defines `1.0.0` as a single gate: the existing six flows
  plus strict HIG conformance, English and Spanish, and note reminders. Linux native is the only
  release gate; macOS and Windows use the released wheel and `afanes --web`, and nightly
  `hatch check`, `hatch test`, and native builds are advisory and never blocking. An experimental
  native binary reaches the release page only when that platform's nightly tests and build both
  pass; it remains untested at runtime, unsigned, and unsupported. Artifacts are attached manually,
  with no PyPI publication, code signing, notarization, or auto-update. This implements the
  `unify-mvp-gate` OpenSpec change. README: updated. Docs: updated.
- **Global search has its own browser row.** The browser header now holds only the destination title,
  refresh, and destination actions, with a permanent full-width search row beneath it and a clear
  action. While a query is active the title reads **Search results**, destination-specific controls
  (Inbox composer, References action, Log date controls, Review queue) are hidden, and the grouped
  results no longer depend on the origin destination. `Ctrl+F` focuses the field, and `Esc` clears a
  non-empty query before closing the navigation drawer. This implements the `refine-browser-search`
  OpenSpec change. README: no change required. Docs: the workspace guide and interface standard were
  updated during implementation.
- **Breaking (UI):** the workspace is now a three-region shell with a navigation sidebar, a browser
  column, and a detail pane. The navigation holds destinations, counts, vault identity, and the
  primary menu (Change Vault…, Create Vault…, Close Vault, About Afanes); search is global and returns
  section-grouped results; the capture composer sits at the top of the Inbox browser; Review shows
  its snapshot queue as selectable cards; and the layout adapts at 1100 px and 1024 px down to a
  browse-to-detail stack. The OS title bar stays native. This implements the `adaptive-browser-shell`
  OpenSpec change. README: no change required. Docs: the interface standard, workspace, log, inbox,
  and review guides and the four screenshots were updated during implementation.
- **Connections, page navigation, and rewrite reports.** Connections omit a group with no visible
  item, and the completed-item reveal controls stay available when only hidden items remain. A page
  always opens at the top after browser selection, a link, a connection entry, or Back. Processing
  offers Log entry among its fixed outcomes, and every reference rewrite reports the notes it
  updated and skipped with vault-relative paths and reasons. A null `status` or `due_date` is treated
  as absent on every note type. This implements the `restore-workspace-conformance` OpenSpec change,
  which also closed the scenario-to-test audit. README: no change required. Docs: the pages,
  workspace, processing, and frontmatter pages were updated during implementation.
- **One affirmative action per surface.** Capture, Processing Preview, New Vault, New Reference,
  Rename, and review forms keep their affirmative control insensitive until the input is valid, and
  the action becomes available as the field changes. Each rendered surface shows at most one
  suggested or destructive action; inline confirmations put Cancel first; buttons combine an icon
  and a label only in a header bar; and list rows use the standard height. Disabled accent actions
  use a muted fill so they no longer look available. This implements the `control-hierarchy`
  OpenSpec change. README: no change required. Docs: the interface standard and the workspace and
  processing guides were updated during implementation.

## [0.7.0] - 2026-11-12

### Added

- **Strict Adwaita interface standard.** The interface now uses the libadwaita 1.8.0 palette, four
  surface roles, the neutral navigation-sidebar selection, and the GNOME standard type scale
  (`title-1` through `caption-heading`). Interface icons use outlined symbolic-style glyphs, the
  minimum window fits 1024x600, and `tests/ui/test_conformance.py` enforces the palette, surface,
  text-role, icon, and per-view action rules with a baseline that may only shrink. This implements
  the `establish-interface-standard` OpenSpec change. No runtime dependency or public API change.
  README: no change required. Docs: the interface standard page, workspace guide, and screenshots
  were updated.
- **Project roles and metadata name references.** A project may declare one optional `owner`, shown before `Asked
  by` and backed by a real note name. The owner, requester, and step owners now resolve through the `note:` catalog:
  renaming a note rewrites each matching value, moving it to trash leaves the value as an unresolved name, rename
  and trash previews count them, and browser search finds projects by role name. Role names are clickable in read
  mode; a missing name is shown as a broken link and creates a categorized reference after confirmation. The
  project header also offers owner and requester actions that set or clear either role with vault-name
  suggestions and write immediately. New role references always offer `person` and every template card category,
  default to `person`, and seed the note from the matching template card. Connections add **Owned projects** and
  show finished owned and requested projects behind the existing finished toggle. Project and Done now in the
  Processing Wizard accept optional Owner and Asked by names with vault suggestions. Append step is unchanged and
  does not copy the project owner. This implements the
  `add-project-roles` OpenSpec change. README: no change required. Docs: frontmatter, vault format, names and
  links, step metadata, projects and steps, pages and editing, workspace search, processing, and the
  capture-clarify-review guide were updated.
- **Versioned vaults.** Every vault root now carries `afanes.yaml` with `schema_version: 1`. Creation writes it
  before starter content, and opening a valid read-only vault remains read-only. An older writable folder with the
  five default folders can be adopted through the interface or `afanes vault adopt DIR`, which writes only that
  file. This implements the `vault-schema` OpenSpec change.
- **Connections.** Read mode lists the notes that link to the open page, the open steps owned by a person, and the
  projects they requested. Each completed view is opt-in, the section is read-only, and it is hidden when empty.
  This implements the `note-connections` OpenSpec change.

### Changed

- **Breaking:** a folder without a valid `afanes.yaml` is no longer opened as a vault. Invalid or unsupported
  settings files are refused and preserved byte for byte; a newer schema asks the user to update Afanes.
- **Renames rewrite role names.** Renaming a note now also rewrites a project's `owner` and `asked_by` values and
  every matching step owner, in the same atomic write as body links. A role name that matches no note remains in
  the file as a broken link. This implements the `add-project-roles` OpenSpec change.
- **One owner for page labels and template cards.** Editable frontmatter labels are written only by
  `PageLabels.apply_to`, and the processing, reference, and log forms share one template card picker. Vault files
  keep their unknown keys and newline style, and parsed note values are unchanged. This implements the
  `refactor-single-owner` OpenSpec change.

### Removed

- **Breaking:** the unused `PageEditorState.page_steps` property is removed to make room for the new
  `set_page_owner` command within the controller's public-name budget. Read steps from `page_body_blocks` or the
  scanned note instead. This implements the `add-project-roles` OpenSpec change.
- **Breaking:** the unused `ui.views.inbox.InboxView` class and its exclusive helpers are removed. The live
  workspace browser replaced that screen with `ui.views.workspace.WorkspaceView`; no user-visible workflow changed.
  This implements the `refactor-single-owner` OpenSpec change.

### Fixed

- Creating a role reference now refreshes the existing workspace instead of rebuilding the Flet page from
  inside the category dialog. Before this fix the new reference opened in edit mode but Done and Back
  stopped repainting because the client no longer applied updates. The same in-place refresh is used by
  the new-reference and new-log-entry dialogs. This implements the `add-project-roles` OpenSpec change.
- The read-mode owner and requester dialogs now save a typed name even when no suggestion is selected;
  previously the typed text was ignored and the unchanged role closed the dialog. The missing-role
  category dialog applies the same fix to a typed category. This implements the `add-project-roles`
  OpenSpec change.
- The page edit form gives its label controls an explicit height, puts every label in one wrapping row so
  Date shares the wide row, and lets the body and raw editors fill the rest of the page pane through a
  full-size mode host and parent-filling multiline fields with top-aligned text. The page pane also
  recovers from stale toolkit freeze markers after a dialog interaction, so Back and Cancel no longer
  raise `Frozen controls cannot be updated`. This implements the `add-project-roles` OpenSpec change.
- The log entry picker describes Empty as a log entry with no starter body instead of offering a reference
  category. This implements the `refactor-single-owner` OpenSpec change.
- The workspace sidebar recovers from a stale presentation freeze marker, so switching browser sections no longer
  raises `Frozen controls cannot be updated`. This implements the `fix-frozen-sidebar-controls` OpenSpec change.
- Guided review opens the Processing Wizard with the same reference template cards as processing from the Inbox:
  choosing Reference or Later lists every valid card and Empty, and the choices refresh when the wizard reopens.
  This implements the `fix-review-template-picker` OpenSpec change.

## [0.6.0] - 2026-11-12

### Added

- **Log notes.** A fourth note type for dated entries. A log lives under `log/<year>/` or
  `log/<year>/<month>/`, holds one entry per exact date, and is created from **Today's entry**, an
  empty calendar day, or the plus on an empty month or year row.
- **Log workspace.** Entries appear in a month calendar and a collapsible year/month/day tree. The
  Entries/Everything switch is remembered per vault, and search filters the tree and the calendar
  together.
- **Note dates.** Every note carries an editable ISO date (`YYYY`, `YYYY-MM`, or `YYYY-MM-DD`),
  separate from a project's due date. New notes are stamped with their creation day; a malformed
  date shows the note as Undated instead of hiding it.
- **Automatic moves for dated notes.** Changing a log date, or converting a note to or from `log`,
  renames the file, moves it to the matching folder, and updates inbound links.
- **Project requester.** A project page shows an optional **Asked by** value.
- **Step cards.** Project read mode shows steps as cards with owners, planned and actual dates, and
  tags, plus date and owner actions directly on each step.
- **Category suggestions.** Reference edit mode suggests category labels already used in the vault
  and still accepts a new one.
- **Reference template cards.** A new reference can start from a card that carries a category and a
  starter body. Seven cards ship, and `templates/` is now reserved for them.
- **Documentation site.** A local Sphinx manual covers installation, the guide, the vault format,
  development, and the Python API.

### Changed

- The interface uses a white, boundary-separated design in light and dark mode, with a blue accent,
  green primary buttons, and a bottom status bar. The Markdown and raw editors fill the page pane.
- `README.md` is now a landing page; the manual moved to `docs/` and builds with
  `hatch run docs:build` or previews with `hatch run docs:serve`.
- Development dependencies add Sphinx, MyST, Furo, and the Mermaid extension. Runtime dependencies
  are unchanged.
- **Breaking:** a vault that used `templates/` for ordinary notes stops showing those notes until
  they are moved, because the folder now holds template cards.
- Public Python API moves: `PageLabels` and `DueDateText` are in `afanes.core.labels`; the reference
  repair, rename, rewrite, trash, and category-move preview and report types are in
  `afanes.core.vault.naming_reports`.

### Fixed

- The API reference renders classes, methods, attributes, and type aliases instead of raw autodoc
  markup.
- Review cards and project rows render step text as Markdown, so links and emphasis display
  correctly outside edit mode.
- The manual starts Afanes from a source checkout with Hatch instead of showing package-index
  instructions.

## [0.5.2] - 2026-11-12

### Added

- The first usable MVP now has one release-readiness definition: the five required flows, the capability spec and automated test behind each, the macOS, Linux, and Windows manual evidence, the excluded scope, and the `0.6.0` checkpoint before `1.0.0`. `README.md`, `AGENTS.md` section 5.3, and this changelog point at `RELEASE.md` instead of restating the criteria. This implements the `define-mvp-release` OpenSpec change.
- The no-index decision now has a measured baseline. `scripts/scan_benchmark.py` generates representative vaults and reports open, cold scan, and fingerprint timings with the environment that produced them; the 10,000-note cold-scan median on the reference machine is 12.0 seconds against a 15-second pass line, so the cold-scan question is closed for that size while refresh latency remains an observed cost. This implements the `measure-vault-scan` OpenSpec change.

### Changed

- The repository guide now uses contiguous section numbers and a citation test that fails when a live document points at a missing section. The type-checking, error and logging, and concurrency rules that tooling cannot enforce are restored, and `openspec/config.yaml` describes the in-memory snapshot instead of a SQLite cache that does not exist. This implements the `reconcile-repository-guide` OpenSpec change.
- The oversized `Vault` service is split into one service per write concern. Each service takes a `Vault` and shares its containment, layout, and atomic-write primitives; `Vault` keeps only open, create, layout, containment, scan, and read. Public Python API migrations:
  - `Vault.capture(text)` is `VaultPages(vault).capture(text)`.
  - `Vault.create_page(...)` is `VaultPages(vault).create_page(...)`.
  - `Vault.write_page(...)` is `VaultPages(vault).write_page(...)`.
  - `Vault.recreate_page(...)` is `VaultPages(vault).recreate_page(...)`.
  - `Vault.set_status(...)` is `VaultPages(vault).set_status(...)`.
  - `Vault.tick_step(...)` is `VaultSteps(vault).tick_step(...)`.
  - `Vault.untick_step(...)` is `VaultSteps(vault).untick_step(...)`.
  - `Vault.plan_step(...)` is `VaultSteps(vault).plan_step(...)`.
  - `Vault.set_step_owners(...)` is `VaultSteps(vault).set_step_owners(...)`.
  - `Vault.append_step(...)` is `VaultSteps(vault).append_step(...)`.
  - `Vault.plan_processing(...)` is `VaultProcessing(vault).plan_processing(...)`.
  - `Vault.plan_append_step(...)` is `VaultProcessing(vault).plan_append_step(...)`.
  - `Vault.apply_processing(...)` is `VaultProcessing(vault).apply_processing(...)`.
  - `Vault.move(...)` is `VaultNaming(vault).move(...)`.
  - `Vault.plan_category_move(...)` is `VaultNaming(vault).plan_category_move(...)`.
  - `Vault.apply_category_move(...)` is `VaultNaming(vault).apply_category_move(...)`.
  - `Vault.plan_rename(...)` is `VaultNaming(vault).plan_rename(...)`.
  - `Vault.apply_rename(...)` is `VaultNaming(vault).apply_rename(...)`.
  - `Vault.plan_reference_repair(...)` is `VaultNaming(vault).plan_reference_repair(...)`.
  - `Vault.apply_reference_repair(...)` is `VaultNaming(vault).apply_reference_repair(...)`.
  - `Vault.plan_trash(...)` is `VaultNaming(vault).plan_trash(...)`.
  - `Vault.trash(...)` is `VaultNaming(vault).trash(...)`.
- Snapshot value types moved to `afanes.core.vault.snapshot`: `VaultNote`, `VaultFailure`, `VaultSnapshot`, `LinkTarget`, `LinkOutcome`, `ReferenceSite`, `NoteOrder`, `InboxOrder`, `VaultPath`, `NotePath`, `PageFile`, `ParsedPage`, `UnparsedPage`, and `PageContent`.
- Naming preview and report types moved to `afanes.core.vault.naming`: `ReferenceRepairPreview`, `RenamePreview`, `RewriteFailure`, `RewriteReport`, `RenameReport`, `TrashPreview`, and `CategoryMovePreview`.
- The vault services now live under the `afanes.core.vault` package: `Vault` and `VaultCreation` are in `afanes.core.vault.service`, and the snapshot, naming, pages, steps, and processing concerns keep their current names under `afanes.core.vault.{snapshot,naming,pages,steps,processing}`. The flat `core/vault.py` and `core/vault_*.py` modules are removed; imports change from `afanes.core.vault_naming` to `afanes.core.vault.naming` and from `afanes.core.vault.Vault` to `afanes.core.vault.service.Vault`. This implements the `nest-vault-package` OpenSpec change.
- `afanes.ui.state` is now a package. `app_state` keeps its path, but the `AppState` type moves to `afanes.ui.state.controller`, and the commands move to the controller that owns the data. Public Python API migrations:
  - `AppState` is imported from `afanes.ui.state.controller`; `afanes.ui.state.app_state` is unchanged.
  - `app_state.start/choose_vault/open_vault_path/open_vault_for_run/create_vault/close_vault/change_vault/refresh/refresh_workspace(...)` are `app_state.workspace.*(...)`.
  - `app_state.capture/select_note/note_title/assignment_candidates/template_summaries(...)` are `app_state.session.*(...)`.
  - `app_state.set_section/set_browser_query(...)` are `app_state.browser.set_section/set_query(...)`; `browser_listing`, `project_groups`, `review_pending_count`, and `review_due_count` are `app_state.browser.listing()`, `project_groups()`, `pending_count()`, and `due_count()`.
  - `app_state.open_page/back/follow_link/choose_candidate/clear_ambiguous/open_failure(...)` are `app_state.navigation.*(...)`; the history stack and ambiguous candidates move with them.
  - `app_state.page_*` queries, `edit_page`, `done_editing`, `autosave`, `set_page_body`, `toggle_page_step`, and `set_page_raw_text(...)` are `app_state.pages.*(...)`.
  - `app_state.set_page_type/set_page_category/set_page_status/set_page_due_date`, the category and type confirmations, `apply_repair`, the rename commands, and the trash commands are `app_state.dialogs.*(...)`; `reload_page`, `overwrite_page`, and `recreate_page` also live there.
  - `app_state.begin_processing/plan_processing/apply_processing/cancel_processing/finish_processing(...)` are `app_state.processing.begin/build_plan/apply/cancel/finish(...)`. A review caller records a processed capture with `app_state.review.record_processed()`.
  - `app_state.start_review/review_next/review_skip/...` are `app_state.review.start/next/skip/...(...)`.
  - `app_state.message`, `busy`, and `session_active` are `app_state.status.*`; writes go through `show_message`, `clear_message`, `set_busy`, `begin_session`, and `release_session`.
  - `page_is_new` is removed; `preview_body`, `selected`, `notes`, and `failures` are read through `app_state.session`.
  - The architecture gate now enforces a 10-name combined `AppState` facade, 25 public commands per domain controller, and a command on every class that declares state fields. This implements the `widen-app-state-gate` OpenSpec change.


## [0.5.1] - 2026-11-11

### Added

- Packaged desktop builds: `flet build linux|macos|windows --build-version "$(hatch version)"` bundles the Flet client, records the project version in the artifact, and starts without contacting a remote origin. The README documents the build command, the Flutter SDK and native toolchain prerequisites, the per-platform rule, the output directory, and the offline launch check; `src/main.py` is the packaged launcher. Linux was built and launched with networking unavailable, and its captured note matched a source run byte for byte. This implements the `close-mvp-gaps` OpenSpec change.
- The workspace follows edits made outside the application without a manual refresh. A stat fingerprint limits the work to a rescan only after a change; the browser, project rows, and review queue update, a clean page reloads, a dirty draft raises the existing conflict state, and a deleted page is reported. Background refresh is read-only, preserves user-visible messages, and leaves a processing or review flow on its note.
- New vaults can start from bundled **Personal**, **Work**, or **Study** starter content, or from a blank vault that still receives a `Getting started` guide note. Creation shows the templates with descriptions and a preview in both presentations, and `afanes vault create --template ID` reproduces the choice headlessly. Dates in starter content are relative to creation, so examples stay current while a new vault still opens with nothing to review. `afanes vault templates` lists the catalog. This implements the `add-vault-templates` OpenSpec change.
- **Change vault → Close vault** saves an open page draft, forgets the remembered vault, and returns to the welcome screen, so the next launch starts there. This implements the `add-close-vault` OpenSpec change.

### Changed

- The repository documentation now describes the real module tree and marks the planned SQLite index and the `afanes index` and `afanes doctor` commands as planned instead of present.
- The change-vault menu now distinguishes **Open another vault** from **Create a new vault**, and closing is a separate action.

- Releases are now versioned for pre-1.0 development: `0.5.0` is the current milestone and `1.0.0` is reserved for the first usable MVP. Earlier entries were renumbered from the previous `1.x`–`4.x` labels, which never corresponded to a tag or a shipped release.

## [0.5.0] - 2026-11-11

### Added

- A three-type note model: `note` is an unclarified capture, `reference` is non-actionable knowledge, and `project` is an outcome whose body holds its steps. Person pages are ordinary references with a `category` label.
- Project steps as Markdown task list items in the project body, with optional `owners`, `plan`, `actual`, and `tags` in a trailing flow-style YAML comment. Ticking a step records the current date; unticking removes it and keeps the plan.
- Free-form reference categories that select a folder under `reference/` without selecting a reference scheme. Category changes preview the move, preserve identity, and keep inbound references resolved.
- Processing outcomes **Append step** and **Done now**, alongside Trash, Later, Reference, and Project. Append step writes the capture's first line and detail into an existing project and then trashes the capture.
- Guided review of due or overdue own steps and waiting steps, with do it now, postpone, delegate, reassign, open project, and skip actions. A launch digest reports due work and opens the session without writing to the vault.
- Browser search across display titles, identities, prose bodies, and step text, with results grouped by reference category label and a Needs attention group for misplaced captures.
- Step controls in the page: tick, untick, plan, reassign owners, and append a step.

### Changed

- The frontmatter contract now recognizes only `type`, `category`, `status`, and `due_date`; `category` is valid only on references and `due_date` only on projects. Unknown keys are still preserved.
- Project rows, the Projects workspace, and review cards report open steps and the first unchecked step in document order instead of action notes.
- `Vault.plan_processing` accepts `today` and returns `ProcessingPlan | AppendStepPlan`; it no longer accepts `people`.
- Public Python API migrations for the three-note model:
  - `NoteType.ACTION` was removed. A single actionable unit is a step; use a one-step project or Append step.
  - `ReferenceCategory` was replaced by `CategoryLabel`, a validated free-form label with case-insensitive equality.
  - `ReferenceScheme.PERSON` was removed, and `ReferenceScheme.for_note(note_type, category)` is `ReferenceScheme.for_note(note_type)`; every reference resolves through `note:`.
  - `ACTION_STATUSES` was removed; use `PROJECT_STATUSES`.
  - `CatalogEntry.category` was removed because categories no longer select a scheme.
  - `NoteDocument.references` was removed and `NoteDocument.category` is `CategoryLabel | None`; `NoteDocument.due_date` was added as `datetime.date | None`. `NoteDocument.rewrite_references(old, new)` is `MarkdownBody(document.body).rewrite_references(old, new)`.
  - `VaultNote.action_order()` was removed; use `VaultNote.open_steps()` and `VaultNote.next_step()`. `VaultNote.is_open_action()` was removed because steps are not notes.
  - `Vault.create_project_action(...)` was removed; use `Vault.append_step(...)` for an existing project, or `Vault.plan_step(...)`.
  - `ProcessingOutcome.ACTION` was removed; `ProcessingOutcome.APPEND_STEP` and `ProcessingOutcome.DONE_NOW` were added.
  - `ProcessingPlan.target_category`, `.people`, `.project`, and `.unresolved_references` were removed, and `.body_override` was added. Append step uses `AppendStepPlan`.
  - `PageLabels.with_people` and `PageLabels.with_project` were removed, and `PageLabels.with_category` takes `CategoryLabel | None`.
  - `search.ProjectSummary.open_actions` and `.next_action` are `search.ProjectSummary.open_steps` and `.next_step`. `search.ReviewPlanner` accepts `today=` and exposes `due_count()`.
- This release was built and tested against Flet 1.1.2, markdown-it-py 4.3.0, and PyYAML 6.0.3. The oldest supported versions are tested in the same run.

### Removed

- The `people` and `project` frontmatter keys, the `action` and `person` note types, and the `person:` reference scheme. There is no automatic migration; repair affected notes by hand in raw rescue mode.
- The `actions/` default folder and the `reference/people/` seed.

## [0.4.3] - 2026-11-11

### Added

- **New vault** action on the welcome state and in Change vault, so a first run can provision a vault instead of requiring an existing folder. It creates missing folders in the path, seeds the default layout, remembers the vault, and opens it; a folder that already contains entries or a path that names a file is refused without writing anything.
- `afanes vault create DIR` creates and seeds a vault headlessly, prints the created vault, parent folders, seeded folders, and whether the vault was remembered, and supports `--no-remember`. The installed `afanes` command now dispatches a recognized subcommand and starts the interface otherwise, and the command surface keeps the documented exit codes and display-free guarantees. This release implements the `add-vault-creation` OpenSpec change.

### Changed

- Vault path validation lives in the core layer, so the interface and the command line share one rule instead of duplicating it.

## [0.4.2] - 2026-11-11

### Changed

- The Python API now gives each behavior an owner instead of exposing module-level helper functions. Vault files, frontmatter, settings JSON, CLI flags, and user-visible interface behavior are unchanged.
- Query functions moved to services: `search.browse_groups(snapshot)` is `Browser(snapshot).groups()`; `search.filter_notes(notes, query)` is `Browser.filter_notes(notes, query)`; `search.project_summaries(snapshot)` is `ProjectBoard(snapshot).summaries()`; `search.project_groups(snapshot)` is `ProjectBoard(snapshot).groups()`; `search.review_queue(snapshot)` is `ReviewPlanner(snapshot).queue()`; `search.review_pending_count(snapshot)` is `ReviewPlanner(snapshot).pending_count()`; and `search.is_open_project`/`is_open_action` are `VaultNote.is_open_project`/`VaultNote.is_open_action`.
- Reference helpers moved to their owning types: `links.rewrite_body_references(markdown, old, new)` is `MarkdownBody(markdown).rewrite_references(old, new)`; `links.reference_key(reference)` is `ReferenceKey.from_reference(reference)`; `links.scheme_for_note(type, category)` is `ReferenceScheme.for_note(type, category)`; `links.parse_reference(destination)` is `ReferenceParser().parse(destination)`; `links.classify_destination(destination)` is `DestinationKind.classify(destination)`; `models.note.allowed_statuses(type)` is `NoteType.allowed_statuses`; and `vault.is_inbox_path(relative)` is `VaultNote.is_inbox` or `VaultPath(relative).is_inbox`.
- Page and draft shapes are explicit unions: `PageContent.document`/`.failure` are `ParsedPage.document`/`UnparsedPage.failure`; `PageDraft.from_page` is `PageDraftFactory.from_page`; `PageDraft.new` is `NormalDraft.new`; and `PageDraft.labels`/`.source`/`.raw_text` are the `NormalDraft`/`RawDraft` cases. `Vault.read_page` returns `ParsedPage | UnparsedPage`.
- Entry-point helpers moved to services: `state.open_vault(path)` is `VaultOpener.open(path)`; `__main__.parse_launch_options(argv)` is `LaunchOptions.parse(argv)`; `settings.config_directory()` is `SettingsStore.config_directory()`; and `settings.settings_path()` is `SettingsStore.settings_path()`.

### Added

- A hard object-ownership architecture gate that rejects module-level helpers outside the policy modules and entry points, duplicate view helpers, and uncontrolled `AppState` growth.
- `Banner`, `StatusLabel`, `Panel`, and `Card` components shared by the interface views.

## [0.4.1] - 2026-11-11

### Added

- An installed `afanes` command launches the application, with the same `--web`, `--vault DIR`, and `--port N` options as `python -m afanes`; the module form remains available. This release implements the `add-console-launch-command` OpenSpec change.

## [0.4.0] - 2026-11-11

### Added

- A browser presentation: `python -m afanes --web` serves the workspace from a loopback-only local server, so Afanes runs on machines that block the native Flet client. `--vault DIR` opens a folder for a single run, and `--port N` chooses the listening port.

### Changed

- A browser session asks for an absolute vault path on the welcome screen and in the Change vault action, because browsers cannot return a directory path from a file dialog, and allows one active session at a time.
- A missing runtime is reported with the install command instead of being installed at startup, and a failed desktop launch names `--web` rather than switching presentation silently.
- This release implements the `web-runtime` OpenSpec change.

## [0.3.4] - 2026-11-11

### Added

- Optional runtime installs: `afanes[desktop]` for the native window and `afanes[web]` for the browser runtime, so an environment can install only the runtime it needs and omit the native client.

### Changed

- Runtime dependencies now use compatible-release ranges instead of exact pins. Afanes supports Flet 1.0.4 and later 1.x releases, and installs resolve on artifact mirrors that do not carry the newest release.
- This release was built and tested against Flet 1.1.2, markdown-it-py 4.3.0, and PyYAML 6.0.3. The oldest supported versions are tested in the same run.

## [0.3.3] - 2026-11-11

### Added

- A persistent workspace browser that lists every parsed note under Inbox, Projects, Actions, People, References, or Notes, with section counts, title-and-identity search, and a separate section for unreadable notes.
- A Projects view grouped by Active, Waiting, Later, and Closed, showing each project's status, optional due date, open action count, and computed next action.
- A guided Review queue for pending Inbox captures and open projects, reusing the Processing Wizard and adding project next-step cards with next-action creation, done, later, and skip choices.
- `VaultNote.due_date` plus read-only browsing, project, and review queries in `afanes.core.search`.
- `Vault.create_project_action` and `Vault.set_status` for creating a project-linked action and changing a note's status safely.

### Changed

- The startup screen is now the workspace shell: capture, browser, page reading, processing, and review share one layout instead of switching between full screens.
- A project's next action is computed from its open actions, choosing the earliest due date, then active before waiting, then display title.
- Browser search covers display titles and identities only; note bodies are not searched.
- This release implements the `add-review-workspace` OpenSpec change.

## [0.3.2] - 2026-11-11

### Added

- A page pane beside the Inbox with read and edit modes, live internal links, a shared Back history, and raw rescue for unreadable notes.
- Page creation from unresolved links, deriving type and folder from the `note:`, `person:`, or `project:` scheme and writing only after the first content.
- Raw Markdown body editing plus type, category, status, due date, people, and project labels, with page suggestions and inline validation.
- Autosave every 30 seconds and on Done, Back, or navigation, with external-edit detection and reload, overwrite, recreate, or discard recovery.
- Previewed type and category changes that list the inbound references which would become unresolved.
- Previewed rename and trash actions from the page; a rename updates a matching level-1 heading with the identity.
- A safe-identity repair prompt for unsafe reference names, with vault-wide reference rewriting.

### Changed

- Selecting an Inbox note opens the page pane; internal links navigate while external, attachment, and unsafe destinations remain inert.
- The Inbox failure banner lists unreadable notes as actions that open raw rescue mode.

## [0.3.1] - 2026-11-11

### Added

- Page display titles derived from the first level-1 heading in a note body, falling back to the filename identity when no heading exists.
- Inbox entries and previews show display titles, with the vault-relative path as the secondary line.
- People and project assignment fields suggest existing pages by display title or identity and store the page identity.

### Changed

- Captures write the first non-blank line as a level-1 heading, preserving the original wording when the filename is sanitized.
- The filename stem is the note identity and reference name; it no longer doubles as the display title. No `title:` frontmatter key is introduced.

## [0.3.0] - 2026-11-11

### Added

- A processing model that clarifies an inbox capture into Trash, Later, Reference, Action, or Project, with preview, confirmation, metadata, and atomic apply.
- A default vault layout: `inbox/`, `trash/`, `reference/` with category folders, `projects/`, and `actions/`.
- Recoverable trash under `trash/`; trashed notes are excluded from scans and reference resolution.
- Reference categories: people are `type: reference` notes with `category: person`, with a path for future categories such as places.
- A Processing Wizard in the desktop interface and a Process action in the Inbox.
- Main specifications for the `processing`, `vault-layout`, and `reference-categories` capabilities.

### Changed

- `NoteType` now contains `note`, `action`, `project`, and `reference`; `person` is no longer a standalone type.
- `person:` references resolve to reference notes with `category: person`; `note:` covers notes, actions, and uncategorized references. One note belongs to one scheme.
- Status vocabulary is `active`, `waiting`, `done`, `cancelled`, `archived`, and `later`; `inbox` is no longer a status.
- Default creation destinations follow the new vault layout, with case-insensitive folder reuse and lazy creation.
- Vault deletion is replaced by recoverable `Vault.plan_trash` and `Vault.trash` operations.

### Removed

- The public `Vault.plan_deletion` and `Vault.delete` methods. Use `Vault.plan_trash` and `Vault.trash` instead.
- `NoteType.PERSON`; convert legacy notes to `type: reference` with `category: person`.
- `status: inbox`; captures have no status and the folder is the queue.

## [0.2.1] - 2026-11-11

### Changed

- Core settings, vault, and reference APIs now use cohesive `SettingsStore`, `Vault`, and `ReferenceReader` objects. Vault files, settings JSON, and user-visible behavior are unchanged.
- The shared atomic text writer now lives in `afanes.core.atomic`; vault and settings writes both use it.
- `AGENTS.md` now defines object boundaries for value objects, service objects, pure functions, and controllers, with a review checklist.

### Removed

- The public free-function helpers `load_settings`, `save_settings`, `resolve_vault_root`, `contained_path`, `scan_vault`, `inbox_notes`, `create_note`, `capture_note`, `move_note`, `plan_rename`, `apply_rename`, `plan_deletion`, `delete_note`, and `extract_references`. Use the corresponding `SettingsStore`, `Vault`, `VaultSnapshot`, and `ReferenceReader` methods instead. This is a breaking Python API change; vault and settings formats are unaffected.

## [0.2.0] - 2026-11-10

### Added

- First-run vault selection with a folder picker; the chosen vault is remembered outside the vault and reopened on later launches.
- An Inbox that captures raw thoughts as notes under `inbox/`, lists them newest first, refreshes external changes, and previews Markdown read-only with inert links.
- Recoverable startup and scanning behavior for missing or unreadable vaults, corrupt settings, and notes that cannot be parsed.
- A Flet 1.1.2 desktop interface with keyboard capture and light and dark theme support.
- Main specifications for the `vault-selection` and `inbox-capture` capabilities.

### Fixed

- Filename sanitization is now idempotent when a forbidden character exposes a leading space, such as `.|0`.

## [0.1.0] - 2026-11-10

### Added

- A changelog following Keep a Changelog 1.1.0.
- Name-based note references in standard Markdown using `person:`, `project:`, and `note:` schemes, with resolved, unresolved, and ambiguous outcomes.
- Filename-based note identity with per-scheme uniqueness, cross-platform sanitization, and reference-preserving directory moves and renames.
- Read-only vault scanning and atomic note creation, move, rename, deletion, and inbound-reference reporting.
- Runtime dependencies on `markdown-it-py` for CommonMark parsing and `PyYAML` for safe frontmatter handling.

### Changed

- The canonical vault format now uses scheme references instead of bracket links; `AGENTS.md` and the README document the new format.
- The operating manual now requires strict NumPy-style docstrings for every public API, including all parameters, return values, raised exceptions, and public attributes.
- Archiving an OpenSpec change now bumps the version, updates the changelog and README, runs the quality gates, and creates a release commit.
- OpenSpec project context now records the offline, neutral-vocabulary, docstring, and cross-platform constraints, and archive guidance carries the release steps.
- The project license is now consistently AGPL-3.0-or-later across the LICENSE file, package metadata, README, and source headers.

### Security

- Active URL schemes such as `javascript:` are classified as unsafe and never resolve as internal references.

## [0.0.1] - 2026-11-10

### Added

- Initial Python 3.13 package layout under `src/afanes/` with Hatch build and development environments.
- Ruff, Pyrefly, pytest, Hypothesis, and coverage configuration.
- OpenSpec workspace with the `spec-driven` schema, workflow skills, and slash commands.
- `AGENTS.md` operating manual, MIT licensing, and baseline README.
