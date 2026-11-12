# Design

## Context

See `proposal.md` for motivation. The constraints that shape this design are the existing layering rules and the current code shape.

The dependency graph is `models <- core <- ui`, with `models/` restricted to the standard library. `core/` must not import `ui/` or `cli/`, and `ui/` must not parse Markdown, run SQL, or write vault files. The architecture tests in `tests/core/test_architecture.py` already parse imports with `ast`; this change extends that test instead of adding a second linter.

The current ownership gap is concentrated in a few places:

| Area | Current shape | Consequence |
| --- | --- | --- |
| `core/links.py` | `rewrite_body_references` plus seventeen helpers threading `markdown` | The Markdown text has no owning object |
| `core/vault.py` | `Vault` plus twenty-one private module functions | The service's behavior is split across two scopes |
| `core/search.py` | Fifteen free query functions over `VaultSnapshot` | The snapshot has no query owner |
| `core/processing.py` | Four free validators taking `ProcessingPlan` | The plan does not own its invariants |
| `core/frontmatter.py` | `NoteDocument` plus `_body_title`/`_inline_text` | One-caller helpers live outside the document |
| `core/editing.py` | `PageLabels` plus two free due-date functions | The labels do not own their field |
| `ui/views/*` | Five copies of `_banner`, two of `_status_label` | Shared behavior has no shared home |
| `ui/state.py` | One 2,341-line `AppState` with about one hundred methods | "One class" without cohesion |

The existing public Python APIs are treated as public for release purposes. This change therefore ships as `3.0.0` without compatibility shims.

## Goals / Non-Goals

**Goals:**

- Give every behavior an owner: a method on the type it operates on, or a service that owns the resource.
- Turn one-caller module helpers into private methods and shared helpers into shared components.
- Replace tuple returns and sort keys with named value objects.
- Make `PageContent` and `PageDraft` composition unions that cannot represent invalid states.
- Replace the free query functions with three cohesive services.
- Split `AppState` internally while preserving one module-level `app_state` facade for views.
- Add a hard architecture gate that makes the ownership rule durable.
- Keep user-visible behavior, vault files, settings JSON, CLI flags, and UI behavior unchanged.
- Release `3.0.0` with a migration note and no shims.

**Non-Goals:**

- Changing product behavior, vault layout, frontmatter, note identity, or reference resolution.
- Moving `VaultNote`, `VaultFailure`, or the query result types into `models/`.
- Converting `names.py`, `atomic.py`, or `ui/strings.py` into classes.
- Adding compatibility shims for the old Python APIs.
- Changing the single-`AppState`-facade rule or introducing dependency injection.
- Reworking persistence, indexing, search, or the processing plan/apply state machine.
- Adding dependencies or touching the network.

## Decisions

### D1: Ownership rule, not "everything is a class"

The rule is:

1. If a function operates mainly on a project-defined type, it is a method on that type or on a service that owns the resource.
2. If exactly one method uses a helper, the helper is a private method of that method's class.
3. If a helper is duplicated across classes, it becomes a shared component.
4. A stateless transformation of built-in values may remain a function only in a named policy module and only when several independent callers use it.
5. A composite return of three or more meaningful values, or a tuple that crosses a module boundary, becomes a named value object.
6. If moving behavior would violate the import graph, introduce a value object or service in the allowed layer instead.

The only allowlisted free functions are `core/names.py` (name normalization and filename policy), `core/atomic.py` (the atomic write primitive), `ui/strings.py` (user-facing copy), and the entry-point callbacks (`main` in `ui/app.py` and `__main__.py`, plus the `argparse` type callback). Callbacks, entry points, and test functions are exempt by contract.

Alternatives considered:

- **Strict object graph.** Every function becomes a class method; `normalize_name`, `write_text_atomic`, and the string formatters become namespace classes. This fixes uniformity but adds ceremony without protecting an invariant. Rejected.
- **Review-only ownership.** Keep the current manual and rely on review. The current code already violates the manual, so review alone has failed. Rejected.
- **Current manual as written.** It permits pure functions and a role table, but it leaves the ownership of one-caller helpers to judgment. The gate in D7 makes the end state objective. Partially kept as the policy language.

### D2: Gate-first big-bang refactor

The change is one OpenSpec change with one major release. The architecture gate lands first with a temporary allowlist. Modules are fixed one group at a time, and each allowlist entry is removed when its group passes. The final allowlist is only the four entries in D1.

Alternatives considered:

- **Bottom-up with the gate last.** Lower initial noise, but the gate cannot prevent drift during a long branch.
- **Risk-first.** Doing the unions and the `AppState` split first surfaces the hard problems early, but it destabilizes the types that the rest of the refactor depends on.
- **Module-by-module.** Coherent increments, but cross-cutting types such as `NoteOrder`, `ReferenceKey`, and `MarkdownBody` would be introduced late and force rework.

The gate-first order keeps progress measurable and makes the shrinking allowlist the definition of completion.

### D3: `search.py` becomes three services

`Browser`, `ProjectBoard`, and `ReviewPlanner` each hold a `VaultSnapshot` and own one query concern:

| Service | Public methods | Private helpers |
| --- | --- | --- |
| `Browser` | `groups()`, `filter(query)` | `_section_for(note)`, `_sorted(notes)` |
| `ProjectBoard` | `summaries()`, `groups()` | `_attributed(action)`, `_summary(project, actions)`, `_stage(note)` |
| `ReviewPlanner` | `queue()`, `pending_count()` | `_inbox_items()`, `_project_items()` |

The result types (`BrowserSection`, `ProjectStage`, `ReviewItem`, `BrowserGroup`, `BrowserListing`, `ProjectSummary`, `ProjectGroup`) stay in `core/search.py` next to the services. The services import `VaultSnapshot` and `VaultNote` from `core/vault.py`; the vault module never imports search, so there is no cycle.

Alternatives considered:

- **One `VaultQueries` service.** Less code, but it becomes a god object as the query surface grows.
- **Methods on `VaultSnapshot`.** The most literal reading of "method on the type," but `vault.py` would need the result types from `search.py`, which is a cycle. It would force `VaultNote` and the result types into `models/`, turning presentation groupings into model types.
- **Free functions plus a snapshot parameter.** The status quo; rejected by the ownership rule.

### D4: `AppState` becomes a facade over five collaborators

`AppState` remains the single module-level object and the only thing views import. It owns the shared `asyncio.Lock`, the global `message`/`busy`/`session_active` flags, and the public command surface. Its collaborators are created inside it, not injected:

| Collaborator | Owns |
| --- | --- |
| `VaultSession` | Vault lifecycle, scan snapshot, notes/failures, capture, open/change vault, session gating |
| `BrowserState` | Active section, browser query, browser listing |
| `PageEditorState` | Page union, editing mode, history, conflict/ambiguity, pending labels, type-change sites, repair/rename/trash previews, autosave state |
| `ProcessingState` | Processing note/body/plan/result |
| `ReviewState` | Review session, queue navigation, next-action creation, project status actions |

Collaborators are plain stateful objects. They do not perform file I/O directly; they call the `Vault` service and the query services. The facade owns the lock and serializes commands. Collaborator methods are not independently locked, which avoids nested-lock deadlocks. The facade's public methods delegate to the collaborator that owns the workflow, so views do not need a wholesale rewrite.

Views that reached into the page union use facade properties such as `page_mode`, `page_body`, `page_labels`, `page_raw_text`, `page_is_new`, and `page_is_dirty`. This keeps the union out of the presentation layer and preserves the "views are presentational" rule.

Alternatives considered:

- **Leave `AppState` as one class.** Already one class, still a god object; rejected.
- **Split and expose multiple singletons.** Violates the single-`AppState` rule and forces views to coordinate state.
- **Inject collaborators.** Violates the no-dependency-injection rule. The facade constructs them.

### D5: Aggressive naming for tuple returns and sort keys

Every project-defined tuple return and sort key becomes a frozen, slotted value object. The standard library's own tuples (for example, `Path.rglob` results or mapping items) are not project tuples and are exempt.

| Type | Home | Replaces |
| --- | --- | --- |
| `MarkdownRewrite(text, count)` | `core/links.py` | `rewrite_body_references` return pair |
| `LinkLabel(label, next_index)` | `core/links.py` | `_link_label` return pair |
| `EditBatch(edits, count)` | `core/links.py` | `_collect_inline_edits` and `_collect_definition_edits` pairs |
| `ReferenceKey(scheme, name)` | `core/links.py` | `reference_key` |
| `CatalogEntry(path, note_type, category)` | `core/links.py` | `NameCatalog.from_entries` input tuple |
| `FrontmatterSplit(raw, body, has_frontmatter)` | `core/frontmatter.py` | `_split_frontmatter` triple |
| `ProcessingTarget(note_type, status)` | `core/processing.py` | `_processing_target` pair |
| `DueDateText(text, date, error)` | `core/editing.py` | `parse_due_date` and `due_date_text_from_raw` |
| `NoteOrder(undated, due, status_rank, title_key, name_key, path_key)` | `core/vault.py` | Three sort-key tuples in `search.py` and `vault.py` |

`NoteOrder` uses `@dataclass(frozen=True, slots=True, order=True)`. `VaultNote.order` returns it; `ProjectSummary` and action ordering use the same type with the appropriate `status_rank`. `ReferenceKey.from_reference` owns the normalization that currently lives in `reference_key`. `ProcessingTarget.from_outcome` owns the outcome-to-status rule currently spread across `_processing_target`, `ProcessingPlan`, and `Vault`.

Alternatives considered:

- **Threshold-based naming.** Name only public or three-field tuples. This leaves the duplicated sort-key policy and the cryptic `FrontmatterSplit` boolean in place.
- **Public API only.** Smallest change, but the private tuple soup remains and the architecture gate is harder to state.

The aggressive choice is consistent across public and private return positions and makes the gate simple: no project-defined tuple returns survive.

### D6: Composition unions for pages and drafts

`PageContent` and `PageDraft` become explicit composition unions.

```text
PageFile(path, relative_path, text, content_hash)
ParsedPage(file: PageFile, document: NoteDocument)
UnparsedPage(file: PageFile, failure: str)
PageContent = ParsedPage | UnparsedPage

DraftCommon(path, identity, reference, baseline_body,
            baseline_labels, baseline_raw_text, baseline_hash)
NormalDraft(common: DraftCommon, body: str, labels: PageLabels,
            source: NoteDocument)
RawDraft(common: DraftCommon, raw_text: str)
PageDraft = NormalDraft | RawDraft
```

`PageFile` and the `PageContent` union live in `core/vault.py`. `DraftCommon` and the `PageDraft` union live in `core/editing.py`. Each case exposes read-only `path`, `relative_path`, `text`, and `content_hash` properties that delegate to `PageFile`, so call sites that only need the shared fields do not need to know the union shape.

Factories move to the case that owns the data:

- `ParsedPage.to_draft(reference)` returns a `NormalDraft`.
- `UnparsedPage.to_draft(reference)` returns a `RawDraft`.
- `NormalDraft.new(reference)` replaces `PageDraft.new`.
- `NormalDraft` owns `with_body` and `with_labels`; `RawDraft` owns `with_raw_text`.
- `is_new`, `is_dirty`, `display_title`, `to_text`, `as_new`, and `after_write` are defined per case. Shared baseline bookkeeping lives on `DraftCommon`.

Alternatives considered:

- **Shallow base plus subclasses.** Less plumbing and flat field access, but it uses inheritance and leaves a constructible base unless abstract methods are added. The project prefers composition.
- **Protocol plus independent dataclasses.** No inheritance, but the shared fields are duplicated and runtime narrowing is awkward with data protocols.
- **Validated optional fields.** The current shape; it rejects invalid states only if a constructor check is added, and it does not make them unrepresentable. Rejected when the union option was chosen.

### D7: Hard architecture gate

The gate is a set of tests in `tests/core/test_architecture.py`. It enforces the end state, not a heuristic about callers:

- `core/` has no module-level functions outside `names.py` and `atomic.py`.
- `models/` has no module-level functions.
- `ui/views/` has no module-level functions; the `build_*` helpers become classmethods or are replaced by `View(...).build()` at the call site.
- `ui/state.py` has no module-level functions; `open_vault` becomes `VaultOpener.open`.
- `ui/` has no module-level functions outside `ui/strings.py` and the `ui/app.py` entry point.
- `__main__.py` has no module-level functions outside `main` and the `argparse` type callback `_port_number`.
- No view module defines its own `_banner`, `_status_label`, `_panel`, or `_card`; those live in `ui/components/`.
- `AppState` has at most ten instance fields: the five collaborators, the lock, and the global flags. The collaborators own the rest.

The gate is intentionally blunt. It makes the finish line objective and prevents a new module-level helper from slipping in after the refactor. The one-caller rule remains a review rule during implementation, but the final state is stronger: no module-level helpers at all outside the policy modules and entry points.

Alternatives considered:

- **AST heuristics for one-caller helpers and project-type parameters.** More nuanced, but brittle around callbacks, sort keys, decorators, and tests. The blunt end-state gate is easier to trust.
- **Review-only.** Rejected; the current manual already says the ownership rule and the code drifted.
- **A custom Ruff rule.** Forbidden; the project does not add a second linter.

### D8: Major release without shims

The release is `3.0.0`. The changelog `Changed` section lists the moved APIs and the union changes, with a migration note. No compatibility shims are added: they would keep the free functions alive and preserve the duplication the change removes.

The affected public APIs include:

| Old | New |
| --- | --- |
| `search.browse_groups(snapshot)` | `Browser(snapshot).groups()` |
| `search.project_groups(snapshot)` | `ProjectBoard(snapshot).groups()` |
| `search.review_queue(snapshot)` | `ReviewPlanner(snapshot).queue()` |
| `links.rewrite_body_references(...)` | `MarkdownBody(...).rewrite_references(...)` |
| `links.reference_key(reference)` | `ReferenceKey.from_reference(reference)` |
| `links.scheme_for_note(type, category)` | `ReferenceScheme.for_note(type, category)` |
| `models.note.allowed_statuses(type)` | `NoteType.allowed_statuses` |
| `PageContent.document` / `.failure` | `ParsedPage.document` / `UnparsedPage.failure` |
| `PageDraft.labels` / `.source` / `.raw_text` | `NormalDraft` / `RawDraft` cases |
| `state.open_vault(path)` | `VaultOpener.open(path)` |
| `__main__.parse_launch_options(argv)` | `LaunchOptions.parse(argv)` |

Alternatives considered:

- **Patch release with no migration note.** Contradicts the 1.0.0 precedent, where a comparable core API refactor was a major release.
- **Minor release with deprecation shims.** Backward compatible, but the shims keep the old free functions and delay the cleanup.

### D9: Implementation order inside the change

The order is:

1. Update `AGENTS.md` and add the gate with a temporary allowlist.
2. Add the leaf value objects and model methods: `NoteType.allowed_statuses`, `ReferenceScheme.for_note`, `ReferenceKey`, `NoteOrder`, `MarkdownBody`/`MarkdownRewrite`, `LinkLabel`, `EditBatch`, `CatalogEntry`, `ProcessingTarget`, `FrontmatterSplit`, `DueDateText`.
3. Move the `vault.py` helpers into `Vault`, `VaultSnapshot`, and `VaultNote`.
4. Replace `PageContent` and `PageDraft` with the composition unions.
5. Extract `Browser`, `ProjectBoard`, and `ReviewPlanner` from `search.py`.
6. Extract the shared UI components (`Banner`, `StatusLabel`, `Panel`).
7. Split `AppState` behind its facade.
8. Clean up the remaining public functions: `LaunchOptions.parse`, `VaultOpener.open`, `SettingsStore` path classmethods, and the view builder classmethods.
9. Run the gate with the minimal allowlist, update the changelog and README, and release `3.0.0`.

This order puts the cross-cutting types before their dependents, keeps the unions before the `AppState` split, and leaves the facade rewrite until the page and query types are stable.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| A big-bang branch is long and hard to review | Gate-first shrink, one module group per commit, narrow tests after each task, full gates before the release |
| The temporary allowlist becomes permanent | The final test asserts the allowlist has only the four policy/entry entries; each phase removes its entry |
| The `AppState` split changes async behavior or deadlocks | The facade owns the single lock; collaborators are synchronous state holders; split last; integration tests cover capture, edit, process, review, and recovery |
| The unions add nested access and plumbing | `PageFile`/`DraftCommon` keep shared data in one place; cases expose flat read-only properties; keep each case small |
| Aggressive naming creates many tiny classes | Every new type is frozen, slotted, documented, and placed next to its owner; no behavior is added beyond the named concept |
| A major release surprises Python API consumers | The changelog migration note lists every moved API; the product behavior is unchanged; the version makes the break explicit |
| The gate rejects a legitimate future helper | The allowlist is deliberately tiny; new policy functions require an OpenSpec change and an allowlist update, which is the intended friction |
| Performance regresses from extra objects in hot loops | `NoteOrder`/`ReferenceKey` are created once per item or reference; measure the scan and sort paths if a regression appears |

## Migration Plan

No on-disk migration is needed. Vault files, frontmatter, settings JSON, note identity, and reference resolution are unchanged. The release is a Python API migration only.

The implementation sequence is D9. The architecture gate is added first with a temporary allowlist that names every module still pending. Each phase removes its entry. The final gate must pass with only `core/names.py`, `core/atomic.py`, `ui/strings.py`, and the entry-point callbacks.

Rollback is per phase: each phase is a separate commit, so a failed phase can be reverted without reverting the completed phases. The old public APIs remain until the final removal task, and the major release happens only after every gate passes. If the released package must be rolled back, users can reinstall `2.6.0`; no vault migration was performed.

Release steps follow `AGENTS.md` section 5.8: `hatch version major`, changelog entry and migration note, README review, full gates, and one `chore(release): v3.0.0` commit. The change is archived with `--skip-specs` because there is no product behavior delta; the release workflow still runs.

## Testing and Verification

- **Architecture:** the new gate tests described in D7 run as part of `hatch test`. They cover `core/`, `models/`, `ui/views/`, `ui/state.py`, `__main__.py`, duplicate view helpers, and the `AppState` field budget.
- **Value objects:** unit tests for `ReferenceKey`, `MarkdownRewrite`, `LinkLabel`, `EditBatch`, `CatalogEntry`, `FrontmatterSplit`, `ProcessingTarget`, `DueDateText`, and `NoteOrder`, including ordering and equality behavior.
- **Unions:** tests construct `ParsedPage`/`UnparsedPage` and `NormalDraft`/`RawDraft`, verify the shared property surface, verify that invalid combinations cannot be constructed, and cover `to_draft`, `to_text`, `is_dirty`, `display_title`, `as_new`, and `after_write`.
- **Services:** `Browser`, `ProjectBoard`, and `ReviewPlanner` tests use the existing snapshot fixtures and assert the same outcomes as the old free functions.
- **`AppState`:** tests exercise the facade commands, not the collaborators directly. The singleton is reset between tests. Integration tests cover capture, open, edit, autosave, conflict recovery, processing, review, rename, trash, and repair.
- **Regression:** every behavior currently covered by `tests/core/test_search.py`, `tests/core/test_editing.py`, `tests/core/test_vault.py`, and the UI tests must remain covered after the move. Tests target public methods, never private helpers.
- **Coverage:** at least 85% overall; parser, link, and vault modules at 90% or higher.
- **Gates:** `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the compliance check.

## Cross-Platform, Offline, and Privacy

- No new dependencies and no runtime network, telemetry, analytics, or cloud calls.
- Path containment, case-insensitive directory reuse, reserved Windows names, and atomic writes are unchanged.
- The `PageFile` composition keeps the same raw text and content hash, so external-edit detection is unchanged.
- Tests use `tmp_path` and fixture vaults; no real vault, home directory, or user data is touched.
- No prohibited vocabulary appears in code, tests, UI copy, specs, or the changelog.
- macOS, Linux, and Windows behavior must be reviewed for the path and UI changes; the refactor must not introduce OS-specific assumptions.

## Open Questions

None. All structural decisions were resolved before implementation.
