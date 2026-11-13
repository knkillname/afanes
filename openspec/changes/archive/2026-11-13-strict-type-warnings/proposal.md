# Proposal

## Why

The type gate currently fails only on Pyrefly errors. The IDE shows warning-level diagnostics that the gate hides, so the local editor and `hatch check` disagree about whether the tree is clean. There are 203 warnings in the default development environment, including 124 implicit imports that contradict the explicit-module import rule.

## What Changes

- Make the type gate fail on warning-level diagnostics, using `pyrefly check --min-severity=warn`.
- Fix every existing warning instead of suppressing it:
  - add the missing explicit module imports;
  - replace untyped lambdas in tests with annotated helpers;
  - replace redundant boolean identity assertions;
  - remove redundant casts and string conversions;
  - add type stubs for PyYAML.
- Repair the `hatch-check-types` environment so the gate can resolve the test suite. It currently installs the `test` dependency group, which has Hypothesis but not pytest, so `hatch check` reports missing imports for test modules.
- No user-facing behavior, vault format, or runtime dependency changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a tooling and code-quality change; it does not alter documented system behavior.

## Impact

- `pyproject.toml`: type-gate script, type-check environment, and `types-PyYAML` in the development dependency group.
- `src/afanes/__main__.py`, `src/afanes/core/vault/pages.py`, `src/afanes/ui/app.py`, `src/afanes/ui/state/dialogs.py`, and `src/afanes/ui/views/workspace.py`: explicit imports and local-import shadowing.
- Test modules under `tests/core/`, `tests/cli/`, and `tests/ui/`: explicit imports, typed replacement helpers, and assertion cleanups.
- `docs/develop/setup.md`: warnings-as-errors policy and the type-check environment.
- `README.md`: no change required; installation, quick start, and features are unaffected.
- No runtime network, telemetry, schema, or persistence change.
