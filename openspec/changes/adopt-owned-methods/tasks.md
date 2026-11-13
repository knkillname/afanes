# Tasks

## 1. Give the name policy an owner

- [x] 1.1 Add `NamePolicy` to `src/afanes/core/names.py` with public classmethods `normalize`, `safe_filename`, and `unique`, and private classmethods `_avoid_reserved_device_name` and `_truncate_to_utf8_bytes`; keep the policy constants module-level; verify `hatch test tests/core/test_names.py` passes with the classmethods.
- [x] 1.2 Update every `core/`, `ui/`, and `cli/` call site and docstring cross-reference from `normalize_name`, `safe_filename`, and `unique_name` to `NamePolicy`; verify `grep -rn "names\.\(normalize_name\|safe_filename\|unique_name\)" src tests` returns no output and the full suite passes.

## 2. Give atomic writes an owner

- [x] 2.1 Add `AtomicWriter` to `src/afanes/core/atomic.py` with public classmethods `write_text_atomic` and `write_text_exclusive`, preserving the current filesystem behavior; verify `hatch test tests/core/test_atomic.py` passes with the classmethods.
- [x] 2.2 Update every call site in `core/` and `ui/` from `afanes.core.atomic.write_text_*` to `AtomicWriter`; verify `grep -rn "atomic\.write_text_" src tests` returns no output and the full suite passes.

## 3. Give copy formatting an owner

- [ ] 3.1 Add `CopyFormatter` to `src/afanes/ui/strings.py` with public classmethods `log_entry_count`, `log_day_tooltip`, `reference_count`, `note_count`, `open_step_count`, and `review_pending`; keep the copy constants module-level; verify the formatting tests call the classmethods and pass.
- [ ] 3.2 Update every call site in `ui/` and `tests/` from `afanes.ui.strings.<helper>(` to `CopyFormatter`; verify `grep -rn "ui\.strings\.\(log_entry_count\|log_day_tooltip\|reference_count\|note_count\|open_step_count\|review_pending\)" src tests` returns no output and the full suite passes.

## 4. Reduce entry points to one free function

- [ ] 4.1 Replace `cli/main.py:main` with `CommandLine.main(cls, *args: str) -> int`; make `Launcher.dispatch` call `CommandLine.main(*argv)` and update `tests/cli/test_main.py`; verify the CLI tests pass.
- [ ] 4.2 Replace `__main__.py:main` with `Launcher.main(cls, *args: str) -> int`; add `entrypoint() -> int` as the sole free function, update the `__main__` block, and point `[project.scripts] afanes` at `afanes.__main__:entrypoint`; verify the launcher and CLI tests pass.
- [ ] 4.3 Move `__main__._port_number` to `LaunchOptions.port_number` as a staticmethod passed to `argparse`; update the parser and port tests; verify `hatch test -k "port or launch"` passes.
- [ ] 4.4 Rename `ui/app.py`'s `_Shell` to `AppShell`, add `async main(cls, page, launch_vault=None)` as a classmethod, remove `ui/app.py:main`, and update `Launcher` plus `tests/ui/test_app.py`; verify the UI app tests pass and `grep -rn "ui\.app\.main\|_Shell" src tests` returns no output.
- [ ] 4.5 Verify entry-point coverage: `grep -rn "^def \|^async def " src/afanes` lists only `src/afanes/__main__.py:def entrypoint`; record that the local `entry(page)` closures are the callback objects passed to `flet.run`.

## 5. Refactor the PLR findings

- [ ] 5.1 Add frozen slotted `ProcessingRequest` and `ProcessingContext` value objects and make `VaultProcessing.plan_processing` take the request; split the method below 50 statements and extract validation, target resolution, and note/non-note planning; update `_plan_non_note`, `ProcessingState.build_plan`, callers, and tests; verify `hatch run ruff check --select PLR0915,PLR0913 src/afanes/core/vault/processing.py src/afanes/ui/state/processing.py` reports no findings.
- [ ] 5.2 Add a frozen slotted `PageActions` value object and extract the self-contained `PageView` blocks into small classes under `ui/components/`; update `tests/ui/` and verify the extracted components' tests pass.
- [ ] 5.3 Finish `PageView.__init__` as thin `_build_*` glue over the components; verify `ruff check --select PLR0915,PLR0913 src/afanes/ui/views/page.py` reports no findings and the page-view tests pass.
- [ ] 5.4 Add a frozen slotted `WorkspaceActions` value object and extract the self-contained `WorkspaceView` blocks into small classes under `ui/components/`; update `tests/ui/` and verify the extracted components' tests pass.
- [ ] 5.5 Finish `WorkspaceView.__init__` as thin `_build_*` glue over the components; verify `ruff check --select PLR0915,PLR0913 src/afanes/ui/views/workspace.py` reports no findings and the workspace-view tests pass.
- [ ] 5.6 Add a frozen slotted `NoteDraft` value object and make `Vault.create` take it; update `VaultCommand`, UI state, and tests; verify `ruff check --select PLR0913 src/afanes/core/vault/service.py` reports no findings.
- [ ] 5.7 Add a `ProjectIndex` accumulator for `Connections._index_project` and a frozen `ReferenceRewrite` value object for `VaultNaming._apply_reference_sites`; update callers and tests; verify both modules report no `PLR0913` findings.
- [ ] 5.8 Group `LogTree._control_for` into `CalendarCell` plus `ControlLabels`, and `StepText.__init__` into `StepTextOptions`; update callers and tests; verify both components report no `PLR0913` findings.
- [ ] 5.9 Reduce the return count in `core/frontmatter.py` and `core/links.py` by extracting decision methods; preserve behavior and add a regression test for each changed branch; verify both modules report no `PLR0911` findings.
- [ ] 5.10 Reduce the return count in `ui/state/dialogs.py` (two methods), `ui/state/navigation.py`, `ui/state/pages.py` (two methods), and `ui/views/workspace.py` by extracting decision methods; preserve behavior and add regression tests; verify all four modules report no `PLR0911` findings.
- [ ] 5.11 Run `hatch run ruff check --select PLR src` and confirm zero production findings; run `hatch run ruff check --select PLR tests` and confirm the only findings are the sixteen `PLR0913` test signatures that the configuration will exempt.

## 6. Enable the gates

- [ ] 6.1 Add `PLR` to `[tool.ruff.lint].extend-select`, make `C901` explicit, set `[tool.ruff.lint.pylint].max-statements = 50`, and add `PLR0913` to the `tests/**/*.py` per-file ignores; verify `hatch run ruff check src tests` and `hatch check` pass.
- [ ] 6.2 Reduce `FINAL_FUNCTION_ALLOWLIST` in `tests/core/test_architecture.py` to `{"__main__.py": frozenset({"entrypoint"})}`, simplify the type to `dict[str, frozenset[str]]`, remove the `None` branches from the module-function check, and update the docstring and exact-allowlist test; verify a temporary module-level function fails the gate and the real tree passes.
- [ ] 6.3 Verify `grep -rn "^def \|^async def " src/afanes` lists only `entrypoint`; confirm no leading-underscore helper was promoted solely to satisfy the gate.

## 7. Update the durable documents

- [ ] 7.1 Update `AGENTS.md` 4.2 so the gate bullet allows only `entrypoint`, records the `PLR` statement budget and the test exemption, and removes the migration-debt wording; verify the section no longer allows functions in `core/names.py`, `core/atomic.py`, or `ui/strings.py`.
- [ ] 7.2 Update `docs/develop/architecture.md`: remove the "pure function" unit category, state that a stateless transformation is a method on its owning object, and describe `NamePolicy`, `AtomicWriter`, `CopyFormatter`, `AppShell`, and the Ruff `PLR`/`C901` gate; verify `hatch run docs:build` passes.
- [ ] 7.3 Add one `Unreleased` entry under `Changed` naming the `adopt-owned-methods` change, the three owning classes, the entry-point consolidation, the Ruff `PLR`/`C901` gate, and every API replacement; include `README: no change required` and `Docs: updated`; verify no version bump.
- [ ] 7.4 Run `hatch check`, `hatch test --cover`, `hatch run docs:build`, `openspec validate --all --strict`, `openspec doctor`, and both vocabulary greps from `AGENTS.md` 6.1; verify every gate passes and coverage stays at or above 85%.
- [ ] 7.5 Run `git diff --check` and review the final diff: only the refactored modules, entry points, call sites, tests, `pyproject.toml`, `AGENTS.md`, `docs/develop/architecture.md`, `CHANGELOG.md`, and this change's artifacts; no behavior, vault, schema, dependency, or UI-copy change.

## Workflow follow-up

- Archive the change after the maintainer approves and every task is complete.
- Run the post-archive release workflow; keep the changelog entry under `Unreleased` unless a coherent milestone completes.
- Do not reintroduce a line-count gate or the retired nineteen-method baseline; future method-shape work starts from the Ruff `PLR` findings.
