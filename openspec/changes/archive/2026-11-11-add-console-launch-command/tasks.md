# Tasks

## 1. Declare the console command

- [x] 1.1 Add `[project.scripts]` with `afanes = "afanes.__main__:main"` to `pyproject.toml` and verify the built wheel declares the entry point (`hatch build`, then inspect `entry_points.txt` in the new wheel under `dist/`)
- [x] 1.2 Add a test that parses `pyproject.toml`, asserts the `afanes` script targets `afanes.__main__:main`, and asserts the target resolves to a callable; verify it passes with `hatch test tests/ui/test_launch.py`

## 2. Document the launch command

- [x] 2.1 Update the development, installed-package, and browser sections of `README.md` to show `afanes` alongside `python -m afanes`, and verify each documented command matches an option accepted by `afanes --help`

## 3. Verification

- [x] 3.1 Refresh the development environment and confirm `hatch run afanes --help` prints the launch help (run `hatch env create` if the command is not on the environment path)
- [x] 3.2 Run `hatch check`, `hatch test --cover`, and `openspec validate --all --strict`; verify all pass
- [x] 3.3 Run the vocabulary compliance check in AGENTS.md section 6.6; verify it reports no prohibited terms

## Workflow follow-up

- Archive the change after the user approves the implemented result.
- Run the post-archive release workflow in AGENTS.md section 5.8, including the changelog entry for the new launch command.
