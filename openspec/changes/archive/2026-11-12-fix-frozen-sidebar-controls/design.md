# Design

## Context

See `proposal.md` for the crash. Relevant current state:

- `WorkspaceView` builds every sidebar, status, and browser control once in `__init__` and mutates those same objects
  from `_refresh_dynamic()`, `_set_working()`, `_refresh_failures()`, and `_refresh_banners()`.
- Flet 1.1.2 controls are dataclasses with descriptor-backed properties. Their `Prop.__set__` raises
  `RuntimeError("Frozen controls cannot be updated.")` when the instance carries a `_frozen` marker.
- `_frozen` is a Flet lifecycle marker. It is set for controls rendered by the declarative component API and can leak
  onto an imperative control during reconciliation. Afanes builds its shell imperatively, so a marker on a workspace
  control is stale state, not an ownership contract.
- `PageView.refresh()` also mutates long-lived controls, but it is reached through `_refresh_main()` inside the guarded
  workspace refresh and through page actions that have not shown the crash.

## Goals / Non-Goals

**Goals:**

- Make a section switch, search, explicit refresh, command update, and background scan resilient to a stale `_frozen`
  marker on any control the workspace owns.
- Keep the recovery scoped to one workspace instance and leave controls outside its tree untouched.
- Add a regression test that fails with the reported `RuntimeError` before the fix.

**Non-Goals:**

- Replace the imperative Flet shell with the declarative component API.
- Rebuild the workspace or sidebar on every refresh, which would lose focus, scroll position, and control identity.
- Change Flet versions, add a dependency, or work around unrelated Flet lifecycle errors.
- Change any vault file, scan result, or persisted preference.

## Decisions

### Decision: clear stale freeze markers at the workspace boundary

Add a private `_own_controls()` method to `WorkspaceView`. It walks the control tree rooted at `self.root` and deletes
`_frozen` from every `ft.Control` instance it finds. `_refresh_dynamic()` and `_set_working()` call it before their
first mutation.

This is a narrow compatibility guard: the view owns that tree, and deleting a stale marker restores Flet's imperative
in-place diff for those controls. It covers every mutation site in the view, including the reported
`tile.selected = active`, without wrapping each assignment.

Alternatives considered:

- **Catch `RuntimeError` around each property assignment.** Rejected: there are dozens of assignments across the view,
  and catching midway can leave the sidebar partially updated.
- **Rebuild the sidebar controls on every refresh.** Rejected: it drops focus and scroll position, changes event-handler
  identity, and is more code than the guard. The refresh path is also the hot path for background scans.
- **Clear markers on the whole page.** Rejected: the workspace does not own dialogs, services, or a second session's
  controls, and the spec requires the recovery to stay scoped.
- **Use Flet's public API.** Flet 1.1.2 exposes no unfreeze operation; the marker is only reachable through the
  instance attribute. The workaround is documented so it can be removed when Flet stops freezing imperative controls.

### Decision: walk the tree, not a hand-maintained control list

The walk follows control values inside dataclass fields, including `controls`, `content`, `leading`, `trailing`,
`actions`, and `items`, plus lists and mappings of controls. A hand-maintained list of mutable controls would silently
miss a newly added control. The walk uses a visited-id set and runs only when the workspace repaints, so its cost is
proportional to the visible tree and far below a scan.

The walk checks `dataclasses.is_dataclass` and `isinstance(value, ft.Control)` so plain values, event handlers, and
Flet value objects are ignored.

### Decision: guard both refresh and working-state changes

`_set_working()` mutates action buttons, the capture field, and the section tiles before and after a command. A stale
marker there would fail before `_refresh_dynamic()` runs. Both entry points call the guard, covering the command path
and the scan path.

### Decision: recovery is read-only and invisible

The guard changes Flet object metadata only. It does not scan, read, write, move, or delete a note and does not change
the state that drives the UI. After the marker is cleared, the existing refresh assignments update the controls as
before, so the reader sees the same sidebar with no extra message.

## Risks / Trade-offs

- **[Private Flet attribute]** → The guard reads and deletes `_frozen`, a Flet implementation detail. It is isolated in
  one method with a comment naming the Flet versions affected; a Flet upgrade that removes the marker makes the guard a
  harmless no-op.
- **[Tree walk cost]** → The walk visits every visible control on each refresh. The tree is bounded by the open sidebar
  and page; the scan and file I/O remain the dominant costs. The walk uses a visited set to avoid repeated subtrees.
- **[Masking a real ownership contract]** → If a future Flet version freezes controls intentionally even in imperative
  mode, clearing the marker could allow an unsupported mutation. The design keeps the guard at the view boundary and
  documents the assumption; revisiting it belongs with any move to declarative components.
- **[PageView markers outside a workspace refresh]** → Page actions refresh the page view directly. The spec covers the
  workspace shell; the page view keeps its current behavior and can receive the same guard later if a page-level
  marker appears.

## Migration Plan

None. The vault format and persisted data are unchanged. Rolling back removes the guard and its tests; no user data is
affected.

## Documentation

README: no change required. The fix is internal to the workspace shell and does not change installation, usage,
features, platforms, configuration, or documented behavior.

Docs: no change required. The fix restores the section switching and background refresh behavior already described in
`docs/guide/workspace.md`; no user-facing command, setting, or workflow changes.
