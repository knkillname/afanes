# Proposal

## Why

`tests/core/test_architecture.py` caps `AppState` at ten annotated fields.
`AppState` declares seven, so the gate passes. The real contract is much
larger: 44 properties, 29 setters, 69 public command methods, and 2,802 lines
of class body. The field cap measures storage, not surface.

The five "collaborators" the facade delegates to are not services. Three of
them, `PageEditorState`, `ProcessingState`, and `ReviewState`, are mutable
dataclasses with 15, 6, and 6 fields and zero methods. `AGENTS.md` section 4.3
names "anemic data bags" as a defect and asks every unit to be a value object,
a service, a pure function, or a controller. These are neither: `AppState`
holds all the behavior and reaches into their fields, so adding a capability
adds another property, another setter, and another command to one class.

The result is that the ownership rule cannot fail for the reason it exists. A
reviewer cannot point at a number that says the facade has grown too wide.

## What Changes

- Measure the actual surface, not just the storage: public properties,
  setters, and command methods per class, plus the number of private fields a
  class exposes through the facade.
- Move each command group onto the collaborator that owns its data, so
  `PageEditorState`, `ProcessingState`, and `ReviewState` become controllers
  with their own behavior instead of field bags. `AppState` keeps the shared
  lock, the cross-cutting flags, and access to the controllers.
- Replace the field-only budget in `tests/core/test_architecture.py` with a
  combined rule: a field budget, a public-surface budget per class, and a
  requirement that every collaborator owns at least one command, so an anemic
  bag fails the gate. The confirmed budgets are 10 public names on
  `AppState` and 25 on any one domain controller.
- Turn `ui/state.py` into the `ui/state/` package, one module per controller,
  with the `app_state` singleton defined in `ui/state/__init__.py` so every
  existing `afanes.ui.state.app_state` import keeps working.
- Update `AGENTS.md` section 4.3 to state the new rule in the same terms the
  test enforces.
- The view call sites move to the domain controller that owns each command
  (`app_state.pages.save(...)` instead of a facade method). The change is
  mechanical and user-visible behavior does not change; leaving every call
  site untouched would preserve the 77-member surface the gate is meant to
  bound, so it is not an option.

## Capabilities

None. The change is internal architecture plus a test gate; no user-visible
behavior changes. `skip_specs: true` is declared in `.openspec.yaml`.

### New Capabilities

- None.

### Modified Capabilities

- None.

## Impact

- `src/afanes/ui/state/`: the module becomes a package with one controller per
  module and the `app_state` singleton in `__init__.py`.
- `tests/core/test_architecture.py`: new surface budget, the collaborator
  behavior rule, and the package path instead of `ui/state.py`.
- `tests/ui/test_state.py`: tests move with the commands they exercise.
- `AGENTS.md` section 4.3: rule text. Depends on `reconcile-repository-guide`
  for final numbering.
- `src/afanes/ui/views/` and `src/afanes/ui/app.py`: call sites move to the
  owning controller. No presentation behavior changes.

## Open Questions

None. The maintainer confirmed the budgets (10 central, 25 per domain), pruning
only unused setters, the package split, and the singleton at the package front
door.
