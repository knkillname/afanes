# Proposal

## Why

`src/afanes/core/vault.py` is 3,273 lines, and its single `Vault` class owns
about 60 methods across scanning, capture, processing, page writes, step
editing, category moves, renames, reference repair, and trash. `Vault` itself
holds one field, `root`, so it is a stateless service; the file grows because
every new write operation lands there. `AGENTS.md` section 4.3 asks a service
object to own one resource, but no gate covers `core/` services, and the module
has no natural pressure to split.

The cost is review and merge friction rather than a user-visible bug. A change
that touches rename logic and a change that touches processing both edit one
file and one class, so unrelated behavior is coupled at the diff level and a
reader has to hold the whole contract in mind.

## What Changes

- Decompose the module into cohesive service classes that share the resolved
  root and the containment rule:
  - `Vault`: open, create, layout, containment, scan, and read.
  - `VaultPages`: page create/write/recreate and label updates.
  - `VaultSteps`: tick, untick, plan, append, and owner changes.
  - `VaultProcessing`: processing and append-step plans and their application.
  - `VaultNaming`: rename, category move, reference repair, move, trash
    preview, and trash.
- Update every call site in the same change instead of keeping compatibility
  delegators on `Vault`. A delegator layer would preserve the 56-method surface
  the split is meant to remove, and it would double the code that has to stay
  correct. `CHANGELOG.md` records the migration with each moved method.
- Define the boundary in one place: every service calls the same containment
  helper and the same atomic write primitive, so the split cannot weaken path
  safety.
- Extend the architecture gate with a per-service method budget and a module
  length ceiling so the next oversized class or file fails review instead of
  growing unnoticed.

## Capabilities

None. This is a pure refactor; specs describe behavior and no behavior
changes. `skip_specs: true` is declared in `.openspec.yaml`.

### New Capabilities

- None.

### Modified Capabilities

- None.

## Impact

- `src/afanes/core/vault.py` splits into several modules under
  `src/afanes/core/`; import rules stay intact (`core` still never imports
  `ui` or `cli`).
- `src/afanes/ui/state.py`, `src/afanes/cli/vault.py`,
  `src/afanes/core/editing.py`, and `src/afanes/core/processing.py` adopt the
  new entry points.
- `tests/core/test_vault.py` and `tests/core/test_architecture.py` grow by
  module. Behavior-level tests should move without rewriting their assertions.
- `CHANGELOG.md` records the public Python API migration.
- No vault file, frontmatter key, UI copy, CLI flag, or dependency changes.

## Open Questions

None. The maintainer confirmed the full split, folding trash into naming, and
flat modules under `core/`.
