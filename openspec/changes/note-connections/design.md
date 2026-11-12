# Design

## Context

See `proposal.md` for motivation. The relevant current state:

- `VaultSnapshot` is an immutable, in-memory scan result. `snapshot.referrers(path)` already computes inbound
  reference counts, but it scans every note and every reference on each call.
- `VaultNote` keeps `body_references`, `steps`, and `title`, but it does not keep `asked_by`. The value is parsed into
  `NoteDocument` and then dropped by the scan.
- `VaultSession` owns the current snapshot and is reset when the vault closes.
- `AppState` is at its 10-field and 10-name budgets. `PageEditorState` is at its 25 public-name budget, and
  `PageDialogState` is at 24 of 25. `VaultSession` has room.
- `PageView.refresh()` runs after every user action and every background update, so it must not trigger a scan.

## Goals / Non-Goals

**Goals:**

- Derive inbound references, owned steps, and requested projects from one snapshot, with no file I/O.
- Keep the derivation out of `PageView.refresh()`'s hot path.
- Add no `AppState` field, no new controller, no dependency, and no vault-format change.
- Keep the section deterministic and read-only.

**Non-Goals:**

- A global "wanted pages", orphan, or link-graph view.
- Storing backlinks or derived data in the vault.
- Navigation to a specific step or highlighting a step inside a project.
- Aliases, redirects, or a persistent index.

## Decisions

### Decision: a read-only `core.connections` service

Add `src/afanes/core/connections.py` with a `Connections` service that owns one `VaultSnapshot`. It exposes one query,
`for_note(path)`, returning a frozen `ConnectionSet`.

Alternatives considered:

- **Extend `core/search.py`.** `search.py` is already 611 lines against a 900-line module ceiling. Connections are a
  different query shape from browsing, projects, and review, so a sibling module keeps both cohesive.
- **Add methods to `VaultSnapshot`.** The snapshot is a value object. Derived query logic belongs in a service, as
  `Browser`, `ProjectBoard`, and `ReviewPlanner` already do.
- **Reuse `referrers()` per page.** It is O(notes × references) per call and would run on every repaint.

The service is built once per snapshot, not once per page and not once per refresh.

### Decision: one index, built lazily and cached by snapshot identity

`Connections.__init__` builds three maps in one pass:

```
target note path -> referring notes        (deduplicated, sorted by alphabetical order)
target note path -> owned projects          (project, open steps, completed steps)
target note path -> requested projects      (open and finished lists)
```

`for_note(path)` is a dictionary lookup plus tuple construction.

`VaultSession` gains a `connections` property and two private cache fields. The property rebuilds the service only
when the current `snapshot` object is not the one the cache was built from. This makes a background refresh
self-invalidating without touching `apply_snapshot`, and it keeps the cost off scans that never open a page.

Alternatives considered:

- **Build in `apply_snapshot`.** Simple, but every background refresh pays the full index cost even when no page is
  open.
- **Cache in `PageEditorState`.** That class is at its public-name ceiling, and the cache would need explicit
  invalidation from the session on every refresh.
- **A module-level cache.** Mutable module state is forbidden in `core`, and it would leak between vaults and tests.

`PageView` reads `state.session.connections` and passes the open page path. It adds no public name to
`PageEditorState` and no field to `AppState`.

### Decision: add `asked_by` to the scanned note

`VaultNote` gains `asked_by: str | None`, populated from `NoteDocument.asked_by` in `Vault._read_note`. This is a
model change, not a vault-format change: `asked_by` is already parsed and preserved, and the scanned note simply
stops discarding it.

Alternatives considered:

- **Read the project file when the section renders.** Violates the read-only snapshot rule and makes page rendering do
  file I/O.
- **Keep a side map on the snapshot.** The data belongs on the note that declares it, and a parallel map would need
  its own invalidation and tests.

Only one production constructor and one test helper construct `VaultNote`, so the blast radius is small.

### Decision: unique resolution decides attribution

The service uses `NameCatalog.resolve` with `ReferenceScheme.NOTE` for body references, step owners, and `asked_by`.
Only a `RESOLVED` outcome with exactly one target attributes a relationship. `MISSING` and `AMBIGUOUS` contribute
nothing, which matches the existing reference rules. Owners and `asked_by` are not restricted to `category: person`;
any note with a matching name can be a hub.

Alternatives considered:

- **Match names manually.** Duplicates normalization and resolution policy and would drift from `note-references`.
- **Restrict owners and `asked_by` to person references.** Rejects valid uses such as a team reference and adds a
  rule the current ownership spec does not have.

### Decision: open and finished are split at build time

The index stores open steps and completed steps separately, and open projects and finished projects separately. A
finished item is one whose status is `done`, `cancelled`, or `archived`, matching `VaultNote.is_open_project`.
Referrers are not filtered by status: a link from a finished project is still a link.

The two "Show completed" controls are view-local booleans in `PageView`. They reset when the open page path changes
and are independent of each other. They are presentation state, not vault data, so they do not belong in a
controller.

### Decision: presentation reuses existing components and copy conventions

The section is a `Panel`-like block appended to the page content column after the body. Rows are `ft.TextButton`
controls with the display title as their only label; project headings are muted `ft.Text` values. The copy lives in
`ui/strings.py` and the spacing and typography come from `ui/theme.py`. Clicking a row calls the existing
`navigation.open_page` command, so dirty drafts, conflicts, and history keep their current rules.

## Risks / Trade-offs

- **[First page open pays the index cost on a very large vault]** → Build lazily once per snapshot and measure with
  `scripts/scan_benchmark.py`; the per-page query stays O(1). If the index build proves costly, it can move to a
  background task without changing the spec.
- **[`VaultNote` gains a field, so every future constructor must supply it]** → Give it a default of `None` and update
  the single production constructor and the test helper; the docstring records the new attribute.
- **[A project can be "finished" but still have open steps]** → Finished projects are excluded from `Owned steps`, so
  those steps do not appear. This is deliberate: a closed project is history, not current involvement.
- **[The section can duplicate a body "See also" list]** → The section is additive and clearly labeled; no attempt is
  made to detect or merge manual lists.
- **[The toggles reset when the page changes]** → The spec requires it; the reset is driven by the page path, so a
  background refresh does not collapse an expanded view.
- **[Ambiguous or missing names silently contribute nothing]** → This matches the existing reference contract; the
  section is not a diagnostics surface. Diagnostics remain in the link navigation and failure views.

## Migration Plan

None. The vault format is unchanged, no data is rewritten, and the first page opened after upgrade builds the index
from the existing scan. Rolling back removes the section and the cache; no user data is affected.
