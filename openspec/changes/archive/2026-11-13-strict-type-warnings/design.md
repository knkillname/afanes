# Design

## Context

See `proposal.md` for motivation. The type gate is Pyrefly 1.4.1 with the `strict` preset configured in `pyproject.toml`. `hatch check` runs the `check` script in the `hatch-check-types` environment, which currently executes `pyrefly check` with the default `--min-severity=error`. Warning-level diagnostics are therefore hidden from the gate while the VS Code extension displays them.

The default development environment reports 203 warnings across six rules:

| Rule | Count | Area |
| --- | ---: | --- |
| `implicit-import` | 124 | 35 in `src`, 89 in `tests` |
| `implicit-any-lambda` | 42 | tests |
| `unnecessary-comparison` | 22 | tests |
| `redundant-cast` | 6 | tests |
| `untyped-import` | 5 | `src` |
| `unnecessary-type-conversion` | 4 | tests |

The `hatch-check-types` environment installs the `test` dependency group, which contains Hypothesis but not pytest, and the project runtime dependencies but not the test-only packages. As a result it also reports 32 `missing-import` errors for `pytest` regardless of the severity threshold.

## Goals / Non-Goals

**Goals:**

- Make `hatch check` fail on every warning, not just errors.
- Reach zero warnings without adding ignores or weakening assertions.
- Keep the development, CI-equivalent, and IDE results aligned.
- Keep the type-gate environment reproducible and able to resolve the whole test suite.

**Non-Goals:**

- Enabling every possible Pyrefly diagnostic. This change raises the failure threshold; it does not switch to the `all` preset.
- Changing runtime behavior, vault formats, or user-facing copy.
- Adding a second type checker or a new code-quality tool.

## Decisions

### Use `--min-severity=warn` as the gate threshold

The `check` script becomes `pyrefly check --min-severity=warn`. Pyrefly then reports warnings and returns a nonzero status when any are present. This captures future warning kinds automatically, unlike a fixed list of per-rule `"error"` mappings.

**Alternatives considered:** mapping each current warning kind to `"error"` in `[tool.pyrefly.errors]` (rejected: a new warning kind would still be hidden); using `preset = "all"` (rejected: it enables additional checks beyond the current warning set and would expand the change far beyond the request).

### Remove the `implicit-any-lambda` downgrade after fixing the lambdas

The current `implicit-any-lambda = "warn"` override exists because tests pass untyped lambdas to `monkeypatch.setattr`. Once those lambdas are replaced with annotated helpers, the override is no longer needed. Removing it keeps the configuration honest and lets the rule's normal severity apply.

**Alternatives considered:** keeping the override and relying only on `--min-severity=warn` (rejected: it leaves a permanent exception in the configuration for a problem that no longer exists).

### Fix implicit imports with explicit module imports

Every warning names a module that is reached through another module's import side effect. The fix is to import the module explicitly at the point that uses it. In `src/afanes/__main__.py`, the function-local `import afanes.ui.app` makes `afanes` local to the function and shadows the module-level `import afanes.ui.strings`; importing the app as `ui_app` avoids the shadowing. The remaining source fixes add `afanes.core.vault.snapshot`, `afanes.ui.state.session`, `afanes.core.vault.pages`, and `afanes.ui.state.browser` where they are used. Test modules add the corresponding explicit imports for `afanes.ui.theme`, `afanes.ui.state.browser`, `afanes.ui.state.processing`, `afanes.ui.state.status`, `afanes.core.editing`, `afanes.core.search`, `afanes.core.steps`, and `afanes.core.frontmatter`.

**Alternatives considered:** adding re-exports to `__init__.py` files (rejected: the project keeps `__init__.py` thin and requires explicit module imports); using ignores (rejected: it hides the dependency rather than making it explicit).

### Replace untyped lambdas with annotated test helpers

`tests/support.py` gains a generic `constant` helper that returns an annotated callable ignoring its arguments, plus a small typed `access_readable` helper for the `os.access` monkeypatches that compare the mode. Constant-return lambdas become `constant(value)`; classmethod patches become `classmethod(constant(value))`; the access checks use the typed helper. A lambda cannot carry parameter annotations, so replacing it with a named helper is the only way to remove the diagnostic rather than suppress it.

**Alternatives considered:** `# pyrefly: ignore[implicit-any-lambda]` comments (rejected: the request is to fix warnings, not hide them); a callable object with `__call__` (rejected: more machinery than a small helper function).

### Use truthiness for boolean assertions

The `unnecessary-comparison` warnings are all `assert <bool> is True` or `assert <bool> is False` after Pyrefly has narrowed the value to a literal. Changing them to `assert value` and `assert not value` preserves the test intent for boolean Flet and state properties and removes the identity comparison. Each site is checked to confirm the property is a boolean rather than a nullable value where `None` must remain distinguishable.

**Alternatives considered:** `typing.cast` to a wider type (rejected: it obscures the assertion); per-line ignores (rejected: it suppresses a real simplification).

### Remove redundant casts and conversions

The six `redundant-cast` warnings are casts to the type Pyrefly already inferred, and the four `unnecessary-type-conversion` warnings are `str()` calls on values already typed `str`. The casts and calls are removed directly.

### Add `types-PyYAML` to the development group

PyYAML has no inline types. The five `untyped-import` warnings in `core/frontmatter.py`, `core/steps.py`, and `core/vault/schema.py` are removed by installing the `types-PyYAML` stub package.

Dependency review:

- **Need:** type information for the existing PyYAML runtime dependency.
- **Alternatives:** ignoring `untyped-import` (rejected: weakens the gate for a real third-party boundary); adding runtime annotations inside Afanes (rejected: the stubs already describe the public PyYAML API).
- **License:** Apache-2.0, verified from the package metadata.
- **Offline behavior:** development-only stubs; no runtime import, network call, or packaged artifact.
- **Cross-platform:** pure-Python stub distribution with no platform-specific code.

The package is pinned in the `dev` dependency group, which also becomes the source for the type-check environment.

### Let the type-check environment use the development group

`hatch-check-types` changes from `dependency-groups = ["test"]` plus a separate `dependencies = ["pyrefly==1.4.1"]` to `dependency-groups = ["dev"]`. The `dev` group already includes Pyrefly, pytest, the pytest plugins, Hypothesis, and the runtime packages, so the type checker can resolve every project include. This removes the duplicate Pyrefly declaration and the current 32 missing-import errors.

**Alternatives considered:** adding only pytest and `types-PyYAML` to the existing minimal environment (rejected: duplicates dependency declarations and leaves the type environment diverging from the development environment).

## Risks / Trade-offs

- **A new warning blocks the gate immediately** → This is the intended policy. Fix it or revise the change; do not lower the threshold silently.
- **Boolean assertion rewrites can change `None` handling** → Inspect each property; if a property is nullable, keep an explicit comparison through a typed local variable instead of using truthiness.
- **Adding module imports can introduce an import cycle** → Add imports only at existing dependency boundaries and run `tests/core/test_architecture.py` plus the full suite.
- **The stub package can lag PyYAML** → Pin the current release and verify `hatch check` resolves all three PyYAML import sites; bump the stub pin separately if a later PyYAML release changes the API.
- **The type environment becomes larger** → It uses the same development dependencies as the local environment, which is the trade-off for consistent results.

## Migration Plan

1. Update the dependency group and type-check environment.
2. Add the stubs and remove the `implicit-any-lambda` override.
3. Fix source and test warnings in small groups, running `hatch check` after each group.
4. Confirm `hatch check` exits zero with `--min-severity=warn`, then run the full test suite.
5. No runtime migration or rollback path is needed; reverting the `pyproject.toml` threshold restores the previous gate.
