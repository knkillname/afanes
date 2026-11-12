# Tasks

## 1. Core schema module

- [x] 1.1 Add `src/afanes/core/vault/schema.py` with `VaultSchema`, `VaultSchemaStore`, `VaultSchemaAdoption`, the schema filename/version constants, the private duplicate-key-safe YAML loader, and the load/require/validate/adopt/create operations; add the schema error types to `src/afanes/core/errors.py`; verify the module imports and the architecture gate passes with `hatch test tests/core/test_architecture.py`.
- [x] 1.2 Add `write_text_exclusive()` to `src/afanes/core/atomic.py` using a temporary file and a no-overwrite publish step with an exclusive-open fallback; add tests in `tests/core/test_atomic.py` for success, an existing target, and a failed publish; verify `hatch test tests/core/test_atomic.py` passes.
- [x] 1.3 Add `tests/core/vault/test_schema.py` covering the exact filename, valid version 1, extra keys, malformed YAML, duplicate keys, a missing or non-integer version, newer/older versions, the size cap, symlink and directory refusal, and byte-for-byte preservation of invalid files; verify `hatch test tests/core/vault/test_schema.py` passes.
- [x] 1.4 Extend `tests/core/vault/test_schema.py` for `is_adoptable()` and `adopt()`: all five default folders, case-insensitive folder names, optional `templates/`, extra folders, a missing folder, a read-only folder, an existing valid file, an existing invalid file, writing only `afanes.yaml`, and never overwriting; verify `hatch test tests/core/vault/test_schema.py` passes.
- [x] 1.5 Document the file name, exact version 1 shape, validation, adoption rule, and migration policy in `docs/reference/vault-format.md`, and add `afanes.core.vault.schema` to `docs/api/vault.md`; verify `hatch run docs:build` passes.

## 2. Vault open and creation integration

- [x] 2.1 Make `Vault.open()` read and require the schema after its existing path checks, update its docstring to state that it reads the settings file and never writes, and add service tests for a missing schema, an invalid schema, a newer schema, a valid read-only vault that opens, and an unversioned folder that stays unwritten; verify `hatch test tests/core/vault/test_service.py` passes.
- [x] 2.2 Write the schema in `Vault.create_directory()` after the root exists and before `_seed_layout()` and starter content; add `settings_file` to `VaultCreation`; update exact creation-tree assertions and add tests for settings written before starter content and a partial creation that remains openable; verify `hatch test tests/core/vault/test_service.py` passes.
- [x] 2.3 Run the architecture gate after the `service.py` changes and confirm the module stays under the 900-line ceiling and `Vault` stays within its public-method budget with `hatch test tests/core/test_architecture.py`.

## 3. Interface adoption flow

- [x] 3.1 Add `adoption_target: Path | None` to `VaultSession`, clear it in `reset()`, and document it; verify `hatch test tests/ui/test_state.py` passes.
- [x] 3.2 Add `WorkspaceController.adopt_vault()` and handle `VaultSchemaMissingError` in `_open_vault_state()` by checking `is_adoptable()` in a worker thread; map missing, invalid, unsupported, read-only, and incompatible cases to distinct UI messages; add state tests for the welcome offer, the change-vault offer, the current vault staying open, declining, successful adoption, adoption write failure, remember failure, and a second session writing nothing; verify `hatch test tests/ui/test_state.py` passes.
- [x] 3.3 Render the shared `Panel` above the welcome or workspace when `adoption_target` is set, with **Create afanes.yaml and open** and **Cancel** actions; add the copy to `ui/strings.py`, spacing to `ui/theme.py`, and app/theme tests for both actions and the hidden state; verify `hatch test tests/ui/test_app.py` and `hatch test tests/ui/test_theme.py` pass.
- [x] 3.4 Update the `--vault` launch tests for an unversioned adoptable folder, an unversioned incompatible folder, an invalid schema, and a valid read-only vault; verify `hatch test tests/ui/test_launch.py` passes.
- [x] 3.5 Update `docs/getting-started/first-vault.md` and `docs/reference/troubleshooting.md` for adoption, refusal, and read-only behavior; verify `hatch run docs:build` passes.

## 4. Command-line adoption

- [x] 4.1 Add `afanes vault adopt DIR` to the parser and `VaultCommand.adopt()`, including `--no-remember`, success output, already-a-vault reporting, and expected failures; add the copy to `cli/strings.py` and tests for adoption success, remembering by default, `--no-remember`, a missing folder, a read-only folder, an invalid settings file, an already versioned folder, and a preference-write failure; verify `hatch test tests/cli/test_main.py` passes.
- [x] 4.2 Include `settings_file` in the `vault create` report and add a CLI test that the output names it; verify `hatch test tests/cli/test_main.py` passes.
- [x] 4.3 Document `afanes vault adopt` and the updated creation output in `docs/guide/command-line.md`; verify `hatch run docs:build` passes.

## 5. Repository documentation and policy

- [x] 5.1 Update `README.md`, `RELEASE.md`, and `AGENTS.md` for the versioned-vault rule, adoption, and the schema file; keep the read-only-open rule and cross-reference the new policy; verify `hatch test tests/core/test_architecture.py` and `hatch run docs:build` pass.
- [x] 5.2 Review the updated docs for stale “any existing directory is a vault” or “opening writes nothing without a schema” language and update any remaining page; verify `hatch test tests/docs/test_style.py` passes.

## 6. Integration gates

- [x] 6.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, and `openspec doctor`; verify all pass and coverage remains at or above 85 percent.
- [x] 6.2 Run the two compliance grep commands from `AGENTS.md` section 6.1 and confirm both exit with status 1 and no output; verify no prohibited vocabulary, `print`, traceback, or runtime network call was introduced.

## Workflow follow-up

- Apply the change with `/opsx-apply` after approval.
- Archive the change after implementation, review, and the project gates pass; run the post-archive release workflow and add the `CHANGELOG.md` entry then.
