# Design

## Context

See `proposal.md` - Why. `AGENTS.md` 4.2 requires owned methods and allows only
a single script entry point to remain free. The gate still permits every function
in `core/names.py`, `core/atomic.py`, and `ui/strings.py` because those entries
allow whole files. Ruff selects `C90` but not `PLR`, so statement count, argument
count, and return count are not gated.

The current production inventory is:

| Rule | Findings | Methods |
| --- | ---: | --- |
| `PLR0915` too many statements (50) | 3 | `plan_processing` (53), `PageView.__init__` (109), `WorkspaceView.__init__` (80) |
| `PLR0913` too many arguments (5) | 10 | 3 overlap the statement offenders; 7 are argument-only |
| `PLR0911` too many returns (6) | 8 | all argument-independent |
| `C901` too complex (10) | 0 | already selected through `C90` |

That is twenty-one findings across eighteen unique production methods. Tests add
sixteen `PLR0913` findings, all from pytest fixture signatures.

The project already uses classmethod services for stateless work:
`VaultCommand.create`, `CommandLine.run`, `SettingsStore.default`, and
`TemplateCatalog.bundled`. The refactor follows that pattern rather than
introducing a new one.

The maintainer resolved the planning questions on 2026-11-13: measure statements
only, not lines; enable the full `PLR` family; exempt tests from `PLR0913`; make a
clean API break; and allow exactly one free function, `entrypoint`.

## Goals / Non-Goals

**Goals:**

- Remove every module-level function except `entrypoint()`.
- Give the name policy, atomic writes, and copy formatting one owning class each.
- Enable `PLR` and make `C901` explicit; set the statement budget to 50.
- Clear every production `PLR` finding across the eighteen methods.
- Split the two large view constructors into components plus thin builders.
- Keep behavior, vault output, and the UI identical.
- Record the API replacements for the pre-1.0 break.

**Non-Goals:**

- Refactoring line-heavy methods that are below 50 statements. The old
  nineteen-method line list is retired; `ProcessingView.__init__` (261 lines) is
  below the statement budget and stays as it is.
- Changing copy, layout, tokens, or any user-visible string.
- Adding a dependency, a service container, or dependency injection.
- A custom line-count gate or a long-method baseline.

## Decisions

### D1. Stateless owning classes use classmethods

`NamePolicy`, `AtomicWriter`, and `CopyFormatter` are classes with public
classmethods. A classmethod has an explicit owner, stays stateless, and matches
the existing service style. No module-level singleton is introduced, so there is
no new module state to reset.

Alternatives considered:

- module-level instances (`NAME_POLICY = NamePolicy()`): more object-like, but
  adds module state for a stateless service;
- instance methods created per call: needless allocation and noisier call sites;
- value objects for counts and names: over-models simple formatting and policy
  lookups.

### D2. Constants stay module-level data

`FORBIDDEN_CHARACTERS`, `RESERVED_DEVICE_NAMES`, `MAX_NAME_BYTES`, and the copy
constants remain module-level names. They are data, not behavior, and the import
rules already require constants to be read through their module. The owning
classes read them; they do not re-export them.

Alternatives considered:

- move every constant into its class: hides the public policy constants and
  duplicates the copy catalog's import path;
- a settings object per class: adds construction and state to a stateless rule.

### D3. `NamePolicy` keeps two private steps

`normalize`, `safe_filename`, and `unique` are public classmethods because
callers need them directly. `_avoid_reserved_device_name` and
`_truncate_to_utf8_bytes` remain private classmethods because they are internal
steps of `safe_filename` and `unique`; no caller uses them alone.

Alternatives considered:

- make every helper public: exposes encoding and reserved-name details that have
  no independent contract;
- leave them as module functions: violates the rule and keeps the gate debt.

### D4. `AtomicWriter` keeps two methods, not a mode flag

`write_text_atomic` and `write_text_exclusive` stay separate classmethods. They
differ in the publish step (`os.replace` versus `os.link` with an exclusive
fallback), and each method stays small and directly testable. A mode parameter
would make one method branch on two filesystem contracts.

Alternatives considered:

- one `write(path, text, *, replace: bool)`: a boolean that changes failure
  behavior and makes both paths harder to read;
- a writer instance per destination: the writer has no per-path state.

### D5. `CopyFormatter` owns formatting, not the catalog

The six helpers become `CopyFormatter` classmethods. The copy constants remain
the single catalog; the class is the behavior owner. `ui/strings.py` stays an
import leaf.

Alternatives considered:

- move formatting to each view: duplicates plural rules and count copy;
- move formatting to value objects: the note and step models should not own UI
  copy.

### D6. One free function: `entrypoint`

The only module-level function in `src/` is `afanes.__main__.entrypoint`. It
delegates to `Launcher.main` and is the target of the installed `afanes` script.

- `CommandLine.main(cls, *args: str) -> int` wraps `CommandLine.run`; the old
  `cli/main.py:main` disappears and callers use the classmethod.
- `Launcher.main(cls, *args: str) -> int` owns dispatch, option parsing, runtime
  checks, and the Flet launch. It returns an exit status instead of raising for
  a subcommand.
- `LaunchOptions.port_number` is a staticmethod passed to `argparse` as the
  `--port` type. It is an owned function object passed to a class, so it does
  not need the free-function exception.
- `AppShell` is the public name of the existing shell class. Its
  `async main(cls, page, launch_vault=None)` classmethod starts the shell; the
  local `entry(page)` closure in `Launcher` remains the object passed to
  `flet.run`.
- `entrypoint() -> int` reads `sys.argv[1:]`, calls `Launcher.main(*args)`, and
  returns its status. `pyproject.toml` points `afanes` at
  `afanes.__main__:entrypoint`.

Alternatives considered:

- keep the four current free functions: two are ordinary internal calls, not
  callback objects;
- keep a module-level `main` as the script target: would require the free
  function the change removes;
- wrap `entrypoint` in a class: the packaging contract still needs a module
  attribute to call.

### D7. The statement ruler replaces the line ruler

Ruff's `PLR0915` counts statements, not lines, and defaults to 50. The project
sets `[tool.ruff.lint.pylint] max-statements = 50` explicitly and selects `PLR`
in `extend-select`. `C901` becomes explicit in the select list even though `C90`
already enables it; the default complexity limit of 10 reports zero findings.

Tests add `PLR0913` to their per-file ignores because pytest fixture signatures
are not production API. No other test exemption is added.

The three statement offenders are split into public commands and small private
steps. `plan_processing` (53 statements) extracts validation, target resolution,
and note/non-note planning. `PageView.__init__` (109) and
`WorkspaceView.__init__` (80) are decomposed under D10. The other fifteen PLR
findings are fixed under D8 and D9.

The old nineteen-method line list is not the work plan. A method may be long in
lines and still below the statement budget; it stays unless it is hard to test
for another reason. No long-method baseline is introduced.

Alternatives considered:

- a custom line-count gate: measured the wrong property and produced the
  nineteen-method list;
- a baseline for the three statement offenders: the maintainer chose to refactor
  them now;
- a 50-statement rule for every method including tests: test fixtures and table
  tests would need artificial splitting for no production benefit.

### D8. Argument-heavy methods take value objects

Each `PLR0913` finding is fixed by grouping related parameters into a frozen
slotted value object with a domain name and invariants. The object is not a
generic bag; it represents a real request, draft, action set, or cell.

| Method | Value object |
| --- | --- |
| `Vault.create` | `NoteDraft` (title, type, category, directory, body, status) |
| `VaultProcessing.plan_processing` | `ProcessingRequest` (capture path, outcome, optional fields, snapshot) |
| `VaultProcessing._plan_non_note` | `ProcessingRequest` plus `ProcessingContext` |
| `Connections._index_project` | `ProjectIndex` accumulator |
| `VaultNaming._apply_reference_sites` | `ReferenceRewrite` |
| `LogTree._control_for` | `CalendarCell` plus `ControlLabels` |
| `StepText.__init__` | `StepTextOptions` |
| `ProcessingState.build_plan` | `ProcessingRequest` |
| `PageView.__init__` | `PageActions` |
| `WorkspaceView.__init__` | `WorkspaceActions` |

`NoteDraft` and `ProcessingRequest` are shared by core and UI state so the
request shape has one owner. `PageActions` and `WorkspaceActions` group callbacks
and pickers; they are value objects with named attributes, not service locators.

Alternatives considered:

- `noqa: PLR0913`: keeps the debt and silences the new gate;
- raising `max-args`: effectively disables the rule;
- one generic `**kwargs`: loses type safety and documentation.

### D9. Return-count methods extract decisions

The eight `PLR0911` methods keep a single exit or return a small result object.
Decision branches move into small public or private methods that return a value,
so each guard is testable. The methods are in `core/frontmatter.py`,
`core/links.py`, `ui/state/dialogs.py` (two), `ui/state/navigation.py`,
`ui/state/pages.py` (two), and `ui/views/workspace.py`. No `noqa` is added.

Alternatives considered:

- raise the return limit: hides the branching the rule is meant to surface;
- suppress per method: same problem with more configuration.

### D10. View constructors become components plus thin builders

Self-contained visual blocks move into small classes under `ui/components/` with
public commands. Only layout glue stays on the view as small private `_build_*`
methods. `PageView` and `WorkspaceView` take one actions value object each, so
their constructors no longer carry six or ten parameters.

This follows the existing `ui/components/` pattern and keeps behavior testable
without making every visual fragment a separate class. The three banned view
helpers (`_banner`, `_status_label`, `_panel`, `_card`) stay out of views.

Alternatives considered:

- private builders only: smallest file churn, but testable sections stay hidden;
- one class per section: more wiring for tiny blocks;
- split by lifecycle phase: keeps the section logic in one large constructor.

### D11. No spec delta; prove parity with tests

The refactor changes no user-visible behavior, so the change sets
`skip_specs: true`. Existing tests for names, atomic writes, copy formatting,
method behavior, and the architecture gate are updated to the owning classes and
value objects and must pass unchanged in behavior. The public Python API changes
are recorded as **BREAKING (API)** with the replacements.

Alternatives considered:

- a spec delta: specs describe behavior, and none changes;
- keep compatibility aliases: the project is pre-1.0 and the aliases would be
  free functions, recreating the debt.

### D12. Update the durable documents

`AGENTS.md` 4.2 changes the gate bullet from a file allowlist to the single
`entrypoint` exception, records the `PLR` statement budget, and removes the
migration-debt wording. `docs/develop/architecture.md` drops the "pure function"
category and describes the owning classes and the Ruff gate. `CHANGELOG.md`
records the API replacements.

Alternatives considered:

- leave the architecture page: it would still teach the retired category;
- leave `AGENTS.md`: the gate description would contradict the code.

## Risks / Trade-offs

- [Call-site churn across core, UI, CLI, and tests] -> Mechanical replacements;
  run the full suite after each owning class and entry point lands.
- [The public API break surprises a downstream user] -> Pre-1.0; list every
  replacement in the changelog and the proposal.
- [Value objects become anemic parameter bags] -> Name them by domain role and
  give them validation or derived behavior where they have invariants.
- [Return-count refactors change branch order] -> Preserve the existing tests and
  add a regression test for every changed decision path.
- [Renaming the shell class touches many UI tests] -> One mechanical rename;
  keep the class behavior unchanged.
- [Sphinx autodoc changes the rendered API] -> Run `hatch run docs:build` and fix
  warnings in the same change.
- [Enabling `PLR` exposes a new rule after the refactor] -> Clear every `PLR`
  finding, not only the three rules that fire today, before the final gate.

## Migration Plan

1. Add `NamePolicy`, update every call site and the names tests.
2. Add `AtomicWriter`, update every call site and the atomic tests.
3. Add `CopyFormatter`, update every call site and the copy/UI tests.
4. Move the entry points: `CommandLine.main`, `Launcher.main`, `entrypoint`,
   `LaunchOptions.port_number`, and `AppShell.main`; update the script target.
5. Split the three statement offenders and introduce the value objects from D8.
6. Fix the eight return-count methods from D9.
7. Enable `PLR`, make `C901` explicit, set `max-statements = 50`, and exempt
   tests from `PLR0913`.
8. Tighten the architecture gate to `__main__.py::entrypoint` only.
9. Update `AGENTS.md` 4.2, `docs/develop/architecture.md`, and `CHANGELOG.md`.
10. Run `hatch check`, `hatch test --cover`, `hatch run docs:build`,
    `openspec validate --all --strict`, `openspec doctor`, and the vocabulary
    greps.
11. Rollback is a code revert; no vault or schema migration happens.

## Open Questions

None. The maintainer resolved scope, metric, PLR breadth, compatibility, entry
points, and view decomposition on 2026-11-13.
