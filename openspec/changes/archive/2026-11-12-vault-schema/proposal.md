# Proposal

## Why

Afanes stores all durable user data in the Markdown vault, but the vault has no format marker. A release cannot tell which on-disk schema wrote an existing folder, so a future format change cannot be detected or migrated safely. A versioned `afanes.yaml` at the vault root gives the application one explicit schema contract before 1.0 and a migration anchor afterwards.

## What Changes

- Add `afanes.yaml` at the vault root, containing exactly `schema_version: 1`.
- A folder is a vault only when it contains a valid `afanes.yaml`. Opening a folder without one is refused. **BREAKING** for vaults created before this change.
- Offer explicit adoption for an unversioned folder that contains all five default folders: `inbox/`, `trash/`, `reference/`, `projects/`, and `log/`. Adoption writes only `afanes.yaml`; it does not seed notes, folders, or the guide.
  - In the interface, the offer is a welcome-state action, or a workspace banner or dialog when changing vaults.
  - On the command line, `afanes vault adopt DIR` performs the same write, remembers the vault by default, and accepts `--no-remember`.
- New vaults write `afanes.yaml` during creation and report it.
- A valid schema 1 vault opens read-only. A read-only vault that already contains a valid file still opens for browsing; edits fail later as usual. Opening never creates the file.
- An invalid, malformed, extra-key, or unsupported schema file is refused and left untouched.
- The schema version is independent of the package version. Before 1.0, schema changes may be breaking; from 1.0 onward every bump ships with a forward migration. A newer schema is refused by an older application, and migrations are forward-only.
- Update the specs and documentation that describe vault acceptance, created-vault contents, and command output.

## Capabilities

### New Capabilities

- `vault-schema`: the vault settings file, its schema version, validation rules, adoption flow, and migration policy.

### Modified Capabilities

- `vault-selection`: a vault now requires a valid schema file; opening, changing vaults, and recovery gain the refusal and adoption behavior.
- `vault-templates`: a created vault now also contains `afanes.yaml`, and the existing “no marker file” rule must distinguish the schema file from template provenance.
- `command-line`: add `afanes vault adopt`, and include the schema file in creation output.
- `vault-layout`: clarify that requiring all five default folders when offering adoption is a compatibility heuristic, not a layout requirement for an already versioned vault.

## Impact

- `src/afanes/core/vault/`: a schema value object and store, plus open and creation integration.
- `src/afanes/core/errors.py`: schema validation and write errors.
- `src/afanes/ui/`: welcome and workspace adoption prompts, and schema refusal copy.
- `src/afanes/cli/`: the `vault adopt` command and the updated creation report.
- Tests under `tests/core/`, `tests/ui/`, and `tests/cli/`.
- Documentation: `README.md`, `RELEASE.md`, `AGENTS.md`, the first-vault, vault-format, troubleshooting, and command-line pages, and the API reference.
- No new dependency, network behavior, note-format change, or persistent index.
