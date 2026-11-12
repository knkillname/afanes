# Design

## Context

See `proposal.md` - Why. Measured from the current `src/afanes/core/vault.py`
(3,273 lines):

| Cluster | Methods | Method lines | Examples |
| --- | --- | --- | --- |
| Lifecycle and scan | 13 | 363 | `open`, `create`, `scan`, `scan_fingerprint`, `read_page` |
| Processing | 11 | 377 | `plan_processing`, `apply_processing`, `plan_append_step` |
| Pages | 7 | 397 | `create_page`, `write_page`, `set_status`, `recreate_page` |
| Steps | 6 | 228 | `tick_step`, `untick_step`, `plan_step`, `append_step` |
| Naming and repair | 9 | 502 | `plan_rename`, `apply_rename`, `plan_category_move` |
| Trash | 2 | 92 | `plan_trash`, `trash` |
| Capture | 1 | 46 | `capture` |
| Shared helpers | 6 | 85 | `_rewrite_note`, `_verify_rewrite` |

`Vault` holds one field, `root`, so every service can share it without
carrying state. About 1,100 of the file's lines are module-level dataclasses:
the snapshot types (`VaultNote`, `VaultSnapshot`, `VaultFailure`, path and
ordering value objects, page result types) and the preview and report types.

## Goals / Non-Goals

**Goals:**

- One module per cohesive write concern, each small enough to review alone.
- Path containment, atomic writes, and external-edit detection stay in one
  place, so a split cannot weaken safety.
- Import graph stays acyclic and inside the `core` layer.

**Non-Goals:**

- Changing any behavior, exception, or file format.
- Adding an index, cache, or new public command.
- Moving types to `models/`; that package is standard-library-only and these
  types depend on `NoteDocument` and `ProjectStep`.

## Decisions

### D1. Split by the resource each service writes

The cut follows the operation, not the line count, so a service owns one kind
of mutation:

| Module | Class | Owns |
| --- | --- | --- |
| `core/vault.py` | `Vault` | open, create, layout, containment, scan, read |
| `core/vault_snapshot.py` | value types | snapshot, note, failure, path, ordering, page results |
| `core/vault_pages.py` | `VaultPages` | capture, create, write, recreate, label changes |
| `core/vault_steps.py` | `VaultSteps` | tick, untick, plan, append, owners |
| `core/vault_processing.py` | `VaultProcessing` | processing and append-step plans and apply |
| `core/vault_naming.py` | `VaultNaming` | rename, category move, repair, trash |

Trash folds into naming: it is 92 lines and reuses the preview/report shapes
and the containment rule. A separate `VaultTrash` would be a module for two
methods.

The alternative - splitting by line count into a `part1`/`part2` pair - was
rejected because it recreates the same coupling under new names.

### D2. Services depend on `Vault`, never the reverse

`Vault` keeps the resolved root, `contained()`, the atomic write call, and the
hash comparison. Every other service takes a `Vault` in its constructor and
calls those primitives:

```
Vault  <--- VaultPages
       <--- VaultSteps
       <--- VaultProcessing
       <--- VaultNaming
```

Consumers construct the service they need (`VaultPages(vault)`), and
`VaultSession` holds the set it needs. `Vault` does not import its siblings and
does not expose factory properties, so the import graph stays acyclic and the
architecture test keeps passing.

The alternative - a `VaultService` base class holding the plumbing - was
rejected because it turns shared safety code into inheritance, and the project
prefers composition.

### D3. No compatibility delegators

Update every call site in the same change. Keeping `Vault.plan_rename(...)` as
a delegator would preserve the 56-method surface and give two places to fix for
every future bug. `CHANGELOG.md` lists each moved method with its replacement,
which satisfies the "breaking change needs a migration note" rule for a 0.x
release.

### D4. Move result types with their producer

`RenamePreview`, `RenameReport`, `RewriteReport`, `RewriteFailure`,
`ReferenceRepairPreview`, `CategoryMovePreview`, and `TrashPreview` move to
`vault_naming.py`. `VaultCreation` stays with `Vault`. Public imports in
`ui/state.py` and tests update mechanically.

### D5. Extend the gate with a service budget

Add to `tests/core/test_architecture.py`:

- No class in `core/` defines more than 20 public methods. The current `Vault`
  defines 32 public methods (56 methods including private helpers); the largest
  split service should land near 10-12.
- No module under `core/` exceeds 900 lines. This is a coarse tripwire, not a
  style rule.
- `core/vault.py` must not import `core/vault_pages`,
  `core/vault_steps`, `core/vault_processing`, or `core/vault_naming`, which
  encodes D2.

The alternative - trusting reviewers to notice growth - was rejected for the
same reason as the other gates: the repository already shows that explicit
tests are what hold.

## Risks / Trade-offs

- [A mechanical rename touches many tests] -> Behavior-level assertions move
  unchanged; only the import and constructor change. Land one module per
  commit.
- [Splitting weakens the single safety path] -> D2 puts containment and atomic
  writes only on `Vault`; the gate in D5 enforces the direction.
- [A new import cycle] -> `test_import_graph_is_acyclic` already fails the
  build; the split is designed around it.
- [Public API break for library users] -> Recorded in `CHANGELOG.md` under
  `Changed` with replacements. The project is pre-1.0 and the guide permits
  breaking changes through an approved change.
- [The provisional budgets are arbitrary] -> Numbers are reviewed after the
  split; the gate's job is to force the conversation.

## Migration Plan

1. Extract `vault_snapshot.py` first; it has no behavior and unblocks the rest.
2. Extract `VaultNaming`, then `VaultProcessing`, then `VaultPages`, then
   `VaultSteps`. Run `hatch test tests/core/test_vault.py` after each.
3. Remove the old methods from `Vault` as each service lands.
4. Add the gate and the migration note.
5. Run `hatch check`, `hatch test --cover`, and `openspec validate --all
   --strict`.

## Open Questions

None. The maintainer confirmed the full split, folding trash into naming, the
900-line ceiling, and flat modules under `core/`.
