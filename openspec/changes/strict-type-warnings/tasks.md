# Tasks

## 1. Type-check environment and stubs

- [x] 1.1 Add `types-PyYAML==6.0.12.20261113` to the `dev` dependency group and switch `hatch-check-types` to `dependency-groups = ["dev"]`, removing the duplicate Pyrefly declaration; verify `hatch run hatch-check-types:check` no longer reports `missing-import` for pytest or PyYAML.
- [x] 1.2 Confirm the PyYAML stub license, offline behavior, and cross-platform impact in the change record; verify the package metadata reports Apache-2.0 and the type-check environment installs it without runtime code changes.

## 2. Source implicit imports

- [x] 2.1 Alias the function-local app import in `src/afanes/__main__.py` so `afanes` is not shadowed, and update both call sites; verify `pyrefly check --min-severity=warn` no longer reports `implicit-import` at lines 181 and 315.
- [x] 2.2 Add explicit module imports in `src/afanes/core/vault/pages.py`, `src/afanes/ui/app.py`, `src/afanes/ui/state/dialogs.py`, and `src/afanes/ui/views/workspace.py`; verify no `implicit-import` warnings remain under `src/` and `hatch test tests/core/test_architecture.py` passes.

## 3. Test implicit imports

- [x] 3.1 Add explicit imports for `afanes.ui.theme`, `afanes.ui.state.browser`, `afanes.ui.state.processing`, `afanes.ui.state.status`, `afanes.core.editing`, `afanes.core.search`, `afanes.core.steps`, and `afanes.core.frontmatter` where the affected test modules access them; verify no `implicit-import` warnings remain under `tests/` and the affected test modules pass.

## 4. Typed lambda helpers

- [x] 4.1 Add a generic `constant` callable helper and a typed `access_readable` helper to `tests/support.py`, with annotations that avoid `implicit-any-lambda`; verify Pyrefly reports no warning for the new helpers.
- [x] 4.2 Replace the constant-return and `classmethod` lambdas in `tests/cli/` and `tests/core/` with the typed helpers; verify no `implicit-any-lambda` warnings remain in those directories and the affected tests pass.
- [x] 4.3 Replace the remaining UI-test lambdas, including the `os.access` mode checks, with the typed helpers; verify no `implicit-any-lambda` warnings remain under `tests/ui/` and the affected tests pass.
- [x] 4.4 Remove the `implicit-any-lambda = "warn"` override from `[tool.pyrefly.errors]`; verify Pyrefly still reports no `implicit-any-lambda` diagnostics and the default type gate passes.

## 5. Assertion, cast, and conversion cleanup

- [x] 5.1 Replace the 22 boolean identity assertions with truthiness or negated truthiness after confirming each property is a boolean, not a nullable value; verify no `unnecessary-comparison` warnings remain and the affected UI tests pass.
- [x] 5.2 Remove the six redundant casts in `tests/ui/test_app.py` and the four unnecessary `str()` conversions in `tests/ui/test_app.py`, `tests/ui/test_page_view.py`, and `tests/ui/test_workspace_view.py`; verify no `redundant-cast` or `unnecessary-type-conversion` warnings remain and the affected tests pass.

## 6. Gate, documentation, and integration

- [x] 6.1 Change the `hatch-check-types` `check` script to `pyrefly check --min-severity=warn` and align `check-summarize`; verify `hatch check` exits zero with zero errors and zero warnings.
- [x] 6.2 Update `docs/develop/setup.md` to state that Pyrefly warnings fail the type gate and that the type-check environment uses the development dependency group; verify `hatch run docs:build` passes and record `README: no change required` if the landing page needs no edit.
- [x] 6.3 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, both vocabulary scans from `AGENTS.md` section 6.1, and `git diff --check`; verify every gate passes.
- [x] 6.4 Review the final diff for scoped changes, no runtime dependency additions, no new ignores, and preserved macOS, Linux, and Windows parity.

## Workflow follow-up

- Archive the change after the review requirements are satisfied.
- Run the post-archive release step in `AGENTS.md` section 5.3; this change is expected to remain under `Unreleased` unless the archive completes a larger milestone.
