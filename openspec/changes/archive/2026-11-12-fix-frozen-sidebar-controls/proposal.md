# Proposal

## Why

Selecting a browser section can crash the workspace with `RuntimeError: Frozen controls cannot be updated.` The
sidebar refresh mutates long-lived Flet controls in place, and Flet 1.1.2 can mark one of those controls as immutable
during reconciliation. The first click after that state fails at `tile.selected = active`, leaving the window running
but unable to switch sections.

## What Changes

- Clear stale toolkit immutability markers from the workspace view's own control tree before each dynamic refresh and
  before enabling or disabling controls.
- Keep the guard scoped to the workspace shell; it must not touch controls owned by another session, dialog, or page.
- Add regression tests that simulate an immutable section entry and prove a section switch and a background refresh
  still update the sidebar.
- Add no dependency, vault format, storage, network, or user-documentation change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `vault-browsing`: the workspace SHALL remain interactive across every refresh, including when the presentation
  toolkit has marked a sidebar control as immutable.

## Impact

- `src/afanes/ui/views/workspace.py`: the refresh and working-state guards.
- `tests/ui/test_workspace_view.py`: regression coverage for a frozen section entry and refresh scope.
- No change to `core/`, `models/`, `cli/`, the vault format, dependencies, or persisted data.
