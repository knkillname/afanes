# Proposal

## Why

Starting Afanes currently requires the module form `hatch run python -m afanes`, which is awkward to
type and does not resemble how someone starts an installed application. The package already has a
validated entry point in `afanes.__main__`, so exposing it as an installed command is a small,
low-risk usability improvement.

## What Changes

- Declare a console script named `afanes` in `pyproject.toml` that points at the existing
  `afanes.__main__:main` entry point.
- Keep `python -m afanes` working unchanged; the console script is an additional supported form.
- Document the `afanes` command in the README for both the source-checkout workflow and an installed
  package.
- Add a test that asserts the declared entry point resolves to the launch function.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `app-runtime`: add a requirement that installing the package provides an `afanes` launch command
  with the same options and presentation behavior as the module form.

## Impact

- `pyproject.toml`: new `[project.scripts]` entry.
- `README.md`: development and installation launch instructions.
- `tests/ui/test_launch.py` or a packaging test: verify the console-script target.
- No dependency, vault format, index, or UI behavior changes. No runtime network access is added.
