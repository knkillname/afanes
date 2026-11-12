# Proposal

## Why

References are visible only in the direction they were written. A reader can follow a link out of a page but cannot
see which pages point back, which projects a person is involved in, or which projects they asked for. The scan
already resolves every reference and already computes inbound reference counts for destructive previews, but the
interface never exposes that knowledge during reading.

## What Changes

- Add a read-only **Connections** section at the end of the page body in read mode, on every parsed note, hidden when
  it has nothing to show.
- Show three subsections:
  - **Linked from**: notes whose body references uniquely resolve to this page, each listed once by display title.
  - **Owned steps**: open steps across projects that name this page as an owner, grouped by project; completed steps
    appear behind a "Show completed" toggle.
  - **Requested projects**: projects whose `asked_by` resolves to this page, open projects first; finished projects
    appear behind the same kind of toggle.
- Resolve `asked_by` against the same name catalog as step owners. An unmatched value stays plain text on the project
  and appears in no Connections section.
- Keep the section read-only: clicking a linked note opens it, and clicking an owned step opens its project at the top.
- Reuse the existing snapshot and name resolution. The change adds no index, dependency, network call, or vault-write
  path, and it does not change the vault format.

## Capabilities

### New Capabilities

- `note-connections`: how a page derives and presents inbound references, owned steps, and requested projects from
  the current snapshot.

### Modified Capabilities

- `note-editing`: read mode gains a Connections section at the end of the page body, shown on every parsed note and
  hidden when empty.

## Impact

- `src/afanes/core/`: a read-only service that derives the three connection kinds from `VaultSnapshot`, without file
  I/O.
- `src/afanes/ui/state/`: the open page exposes the derived connections without adding a new `AppState` controller.
- `src/afanes/ui/views/page.py`: renders the section and its toggles in read mode.
- `src/afanes/ui/strings.py` and `src/afanes/ui/theme.py`: the new copy and presentation constants.
- `docs/guide/pages-and-editing.md` and `docs/reference/names-and-links.md`: describe the section and its relationship
  to references and ownership.
- Tests under `tests/core/` and `tests/ui/`.
- No dependency, vault format, storage, or network impact.
