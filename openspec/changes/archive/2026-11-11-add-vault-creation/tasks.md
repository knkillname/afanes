# Tasks

## 1. Core path validation

- [x] 1.1 Add `VaultMissingError`, `VaultNotDirectoryError`, and `VaultUnreadableError` to `core/errors.py`, subclassing `VaultError`; verify `hatch test tests/core/test_errors.py` covers each type and its inheritance.
- [x] 1.2 Raise the specific errors from `Vault.__post_init__` instead of one generic message; verify `hatch test tests/core/test_vault.py` passes, including the existing `except VaultError` expectations.
- [x] 1.3 Add `Vault.open(path)` that validates existence, directory-ness, and readability and returns the resolved service; verify `hatch test tests/core/test_vault.py -k open` covers a missing path, a file, an unreadable directory, and a relative path.
- [x] 1.4 Make `ui/state.py.VaultOpener.open` delegate to `Vault.open` and translate each domain error to its existing string, removing `os` and path I/O from the interface; verify `hatch test tests/ui/test_state.py` passes unchanged.
- [x] 1.5 Make `Launcher.checked_vault` use `Vault.open` and remove the `afanes.ui.state` import from `__main__.py`; verify `hatch test tests/ui/test_launch.py::TestLaunchVault` passes and `hatch run python -m afanes --vault /missing` exits `1` with one message.

## 2. Core vault creation

- [x] 2.1 Add `VaultNotEmptyError` to `core/errors.py`; verify `hatch test tests/core/test_errors.py` covers it.
- [x] 2.2 Implement `Vault.create_directory(path)` with the documented policy: a missing path created together with any missing intermediate folders, an existing empty directory, non-empty refusal, file refusal, and resolution before the emptiness check; verify `hatch test tests/core/test_vault.py -k create` asserts each outcome, that created intermediate folders are reported, and that a refused path leaves the filesystem unchanged.
- [x] 2.3 Seed the default folders inside `Vault.create_directory` by reusing `directory_for()` for the note destinations, iterating `CATEGORY_DIRECTORIES` for the reference subfolders, and reusing the existing directory lookup for `trash/`; verify a test asserts exactly `inbox/`, `trash/`, `reference/`, `reference/people/`, `projects/`, and `actions/` exist, no files exist, and every seeded path equals what `directory_for()` predicts.
- [x] 2.4 Add a Hypothesis property test that every seeded path stays inside the resolved target for generated directory names; verify `hatch test tests/core/test_vault.py -k create` passes and no seeded path escapes the root.

## 3. Command-line surface

- [x] 3.1 Create `src/afanes/cli/` with `__init__.py`, `main.py`, `vault.py`, and `strings.py`, plus `tests/cli/__init__.py`; verify `hatch run python -c "import afanes.cli.main"` succeeds and a test asserts neither `afanes.ui` nor `flet` is imported by the package.
- [x] 3.2 Define the `vault` subcommand with a `create` action taking `DIR` and `--no-remember`; verify `hatch test tests/cli/test_main.py -k usage` asserts unknown subcommands and missing arguments exit `2`.
- [x] 3.3 Implement the create command through `Vault.create_directory` and `SettingsStore.save`, printing the structured summary on standard output, failures on standard error, and the settings-failure path; verify `hatch test tests/cli/test_main.py` covers exit `0` with the vault path, created parent folders, seeded folders, and remembered state, each refusal exiting `1`, remembering by default, `--no-remember` leaving preferences untouched, and a preferences failure exiting `1` while the vault stays in place.
- [x] 3.4 Add `"cli/main.py": frozenset({"main"})` to the architecture allowlist and its exact-allowlist assertion, add `cli/` import rules against `afanes.ui` and `flet`, and list the same callback in `AGENTS.md` section 4.3; verify `hatch test tests/core/test_architecture.py` passes.
- [x] 3.5 Document `afanes vault create DIR`, `--no-remember`, the seeded folders, and the exit codes in `README.md`; verify the documented commands match `hatch run python -m afanes vault create --help` output.

## 4. Entry-point dispatch

- [x] 4.1 Add `Launcher.dispatch` and dispatch from `main` before the runtime check and any Flet import, keeping the console-script target unchanged; verify `hatch test tests/ui/test_launch.py` passes, including the target assertion, and `hatch run python -m afanes vault create <tmp>/vault exits 0`.
- [x] 4.2 Verify a bare `afanes` and `afanes --web/--vault/--port` still reach the graphical launch path; verify `hatch test tests/ui/test_launch.py -k "options or dispatch"` passes and no window opens during a subcommand run.

## 5. Interface creation

- [x] 5.1 Add `AppState.create_vault(path)` that resolves, creates and seeds in a worker thread, scans, and saves preferences, opening the vault even when preferences cannot be saved; verify `hatch test tests/ui/test_state.py -k create` covers success, each refusal message, and the preferences-failure branch.
- [x] 5.2 Add the action, dialog title and body, folder preview, and error copy to `ui/strings.py` using neutral vocabulary; verify the compliance check from `AGENTS.md` section 6.6 returns no matches.
- [x] 5.3 Add the creation dialog to `_Shell` for both presentations, keeping it open to show an inline error and writing nothing on cancel; verify `hatch test tests/ui/test_app.py -k create` covers the preview text, an inline refusal error, and a cancelled dialog leaving the filesystem and preferences untouched.
- [x] 5.4 Add the New vault action to the welcome state and to the change-vault action in both presentations, leaving the picker and typed-path open flow unchanged; verify `hatch test tests/ui/test_app.py -k welcome` covers creating a first vault, creating a second vault while one is open, the previous vault staying unmodified, and opening still creating nothing.
- [x] 5.5 Document the creation flow, including creating a second vault from the change-vault action, and the caveat that a vault made through the dialog's New Folder is not seeded, in `README.md`; verify the documented steps match the rendered dialog copy.

## 6. Integration and gates

- [x] 6.1 Extend `tests/core/test_integration.py` with a flow that creates a vault, captures into `inbox/`, processes the capture, and reads the result back; verify `hatch test tests/core/test_integration.py` passes.
- [x] 6.2 Run `hatch check` and resolve every lint, format, and type finding; verify the command exits `0`.
- [x] 6.3 Run `hatch test --cover` and confirm coverage is at least 85%; verify the command exits `0`.
- [x] 6.4 Run `openspec validate --all --strict` and `openspec doctor`; verify both exit `0` with no relationship problems.
- [x] 6.5 Run the vocabulary compliance checks from `AGENTS.md` section 6.6; verify both commands return no matches outside `AGENTS.md`.

## 7. Directory-picker creation revision

- [x] 7.1 Replace the desktop creation dialog with the native directory dialog, keeping the browser path dialog, and verify `hatch test tests/ui/test_app.py -k "creation or change"` covers picking, cancelling, refusal, and browser submission.
- [x] 7.2 Update the `vault-selection` delta, `design.md`, and `README.md` for picker-based desktop creation, and verify `openspec validate add-vault-creation --strict` passes.
- [x] 7.3 Run `hatch check`, `hatch test --cover`, and the vocabulary compliance checks; verify they pass.

## Workflow follow-up

- Propose a follow-up change for configurable reference categories (`places` and user-defined
  nouns), covering the note format, validation, the folder mapping, the extended seed set, and the
  affected specs. Seeding already iterates the category map, so creation should need no rework.
- Archive the change after the project's review requirements are satisfied.
- Run the post-archive release workflow in `AGENTS.md` section 5.8: choose the minor bump for a new command and user-visible workflow, run `hatch version minor`, update `CHANGELOG.md`, review `README.md`, rerun every gate, and commit as `chore(release): vX.Y.Z` with the change name in the body.
