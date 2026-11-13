# Proposal

## Why

`AGENTS.md` 4.2 requires object-oriented structure: every behavior is a method
with an owner, module-level functions are prohibited except a single script entry
point, and small public fruitful methods are preferred over large private
helpers. The code still has seventeen module-level functions, and the
architecture gate allows whole files (`core/names.py`, `core/atomic.py`,
`ui/strings.py`) so a new free function in those files passes. Ruff's
method-shape rules are not enabled: twenty-one production `PLR` findings across
eighteen methods show three methods above fifty statements, ten argument lists
above five parameters, and eight methods above six returns. Nothing prevents the
regression from returning.

## What Changes

- **Names.** Replace the functions in `core/names.py` with a `NamePolicy` class:
  `normalize`, `safe_filename`, and `unique` become public classmethods, and the
  reserved-name and byte-truncation helpers become private classmethods. The
  policy constants stay module-level data.
- **Atomic writes.** Replace the functions in `core/atomic.py` with an
  `AtomicWriter` class exposing `write_text_atomic` and
  `write_text_exclusive`. Both keep the current filesystem behavior.
- **Copy formatting.** Replace the six helper functions in `ui/strings.py` with
  a `CopyFormatter` class exposing `log_entry_count`, `log_day_tooltip`,
  `reference_count`, `note_count`, `open_step_count`, and `review_pending`. The
  copy constants stay module-level data.
- **Entry points.** Remove every module-level function except one.
  `CommandLine.main(cls, *args: str) -> int` and
  `Launcher.main(cls, *args: str) -> int` become classmethods;
  `LaunchOptions.port_number` becomes a staticmethod passed to `argparse`; the
  Flet shell becomes `AppShell.main`; and `entrypoint() -> int` in `__main__.py`
  is the only free function, used by the installed `afanes` script.
- **Method shape.** Enable Ruff `PLR` and make `C901` explicit (it is already
  selected through `C90`), set `max-statements = 50`, and exempt tests from
  `PLR0913`. Refactor the twenty-one production findings across eighteen
  methods: split the three statement offenders, group argument-heavy signatures
  into frozen value objects, and reduce return counts by extracting decision
  methods. No `noqa` suppressions.
- **Architecture gate.** `FINAL_FUNCTION_ALLOWLIST` becomes
  `{"__main__.py": frozenset({"entrypoint"})}`; every other module has zero
  module-level functions.
- **BREAKING (API).** The old functions and argument lists are replaced. There
  are no compatibility aliases; the changelog lists every replacement.
- **Documentation.** Update `AGENTS.md` 4.2, `docs/develop/architecture.md`, and
  `CHANGELOG.md`.

No user-visible behavior, vault format, schema, dependency, or UI change is
intended.

## Capabilities

### New Capabilities

None. This is a behavior-preserving refactor; `skip_specs: true` records that no
capability requirement changes.

### Modified Capabilities

None.

## Impact

- `src/afanes/core/names.py`, `core/atomic.py`, `ui/strings.py`: new owning
  classes.
- Method-shape refactors in `core/connections.py`, `core/frontmatter.py`,
  `core/links.py`, `core/vault/naming.py`, `core/vault/processing.py`,
  `core/vault/service.py`, `ui/components/log_tree.py`,
  `ui/components/step_text.py`, `ui/state/dialogs.py`,
  `ui/state/navigation.py`, `ui/state/pages.py`, `ui/state/processing.py`,
  `ui/views/page.py`, and `ui/views/workspace.py`.
- Entry-point changes in `ui/app.py`, `cli/main.py`, `__main__.py`, and
  `pyproject.toml`.
- Every caller, docstring cross-reference, and affected test.
- `tests/core/test_architecture.py`: the final allowlist contains only
  `entrypoint`.
- Ruff configuration in `pyproject.toml`; `AGENTS.md` 4.2;
  `docs/develop/architecture.md`; `CHANGELOG.md`.
- **BREAKING (API):** free functions become classmethods and several
  argument-heavy signatures take one value object. The project is pre-1.0; the
  changelog records each replacement.
- No dependency, vault, schema, or runtime behavior change.
