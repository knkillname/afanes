# Design

## Context

See `proposal.md` for motivation and the delta specs for the behavior contract.

Current state that shapes the approach:

- `Vault` in `src/afanes/core/vault/service.py` resolves and validates a root, scans notes, and owns `create_directory`. `Vault.open()` is currently read-only, and `create_directory()` is the only creation path.
- The scan reads only `*.md` files, so a root `afanes.yaml` is naturally excluded from notes, the browser, name uniqueness, and reference resolution.
- Application preferences live in `core/settings.py` as a separate, versioned JSON file outside the vault. They must not be merged with the vault schema.
- The interface opens a vault through `VaultOpener.open()` in `ui/state/session.py`; `WorkspaceController` in `ui/state/workspace.py` owns choose/change/create and remembers the vault through `SettingsStore`.
- The shell in `ui/app.py` renders the welcome or workspace and already composes the workspace with an optional launch digest. `ui/components/panel.py` and `ui/components/banner.py` provide the shared surfaces for actionable panels and warnings.
- The command surface has `afanes vault create` and `afanes vault templates`; `vault create` remembers by default and accepts `--no-remember`.
- Hard constraints: no free functions outside the architecture allowlist, a 900-line ceiling per core module, a 20-public-method ceiling per core class, and a 25-public-name ceiling per UI state class. `service.py` is currently 850 lines.
- There is no migration runner. This change records the baseline and the policy; the runner arrives with the first post-1.0 schema bump.

## Goals / Non-Goals

**Goals:**

- One explicit, strictly validated schema file at the vault root.
- Refuse unversioned vaults; offer adoption only for folders with the five default folders.
- Write the file during creation, before starter content.
- Add the explicit UI and CLI adoption paths without automatic writes on open.
- Keep opening a versioned vault read-only and keep application preferences separate.
- Fit the existing architecture gates and UI budgets.

**Non-Goals:**

- A migration runner, migration registry, backups, or downgrade support.
- Automatic schema creation while opening or scanning.
- A general settings editor or a schema version display in the workspace.
- Moving application preferences into the vault.
- Cross-process locking for concurrent first adoption or future migrations.

## Decisions

### Decision: a separate `core/vault/schema.py` service

Add the module with:

- `VaultSchema`, a frozen slotted value object carrying the schema version.
- `VaultSchemaStore`, a service owning one vault root and the settings file.
- `VaultSchemaAdoption`, a frozen result carrying the path, schema, and whether the file was created.
- Public policy constants: `SCHEMA_FILENAME = "afanes.yaml"` and `CURRENT_SCHEMA_VERSION = 1`.

`VaultSchemaStore` validates its root and resolves the fixed root path itself. It does not import `Vault`, so `service.py` can import `schema.py` without a cycle; the store reads the default-folder constants from `core/vault/snapshot.py`.

Alternatives considered:

- **Put the logic on `Vault`.** `service.py` is already at 850 of 900 lines and `Vault` has a public-method budget. The settings file is its own concern, so a sibling module keeps both cohesive.
- **Put it in `core/settings.py`.** That module owns machine-local application preferences and is deliberately independent of vault paths; an architecture test already asserts it does not import the vault service. Mixing the two would reverse that separation.
- **Use JSON for consistency with application preferences.** The vault is a human-owned YAML ecosystem, and `afanes.yaml` should be readable beside the notes. YAML also matches the frontmatter tooling already present.

`Vault.open()` calls `require()` after its existing path checks. `Vault.create_directory()` calls `create_current()` after the root directory exists and before `_seed_layout()`. This makes the open gate central rather than repeating it in every caller, and keeps creation atomic enough that a partially created folder still has a schema.

### Decision: exact file, strict shape, safe parsing

The store accepts only the exact root file `afanes.yaml`, as a regular file. It rejects symlinks and directories. It reads a byte-capped file, decodes UTF-8 with an optional BOM, and parses with a safe YAML loader.

The parsed value must be a mapping whose keys are exactly `{"schema_version"}` and whose value is an integer, not a boolean, equal to `CURRENT_SCHEMA_VERSION`. A private loader rejects duplicate mapping keys so a repeated `schema_version` cannot slip through PyYAML's last-value behavior. Extra keys, malformed YAML, a missing key, a non-integer value, and any other version raise a specific schema error.

Error taxonomy:

- `VaultSchemaError(VaultError)`: base for every schema failure.
- `VaultSchemaMissingError`: no exact settings file.
- `VaultSchemaInvalidError`: the file exists but does not match the version 1 shape.
- `VaultSchemaUnsupportedError`: the file declares another version; the message distinguishes older from newer.
- `VaultSchemaWriteError`: the file cannot be written.
- `VaultSchemaNotAdoptableError`: adoption was requested for a folder that does not meet the compatibility rule.

Alternatives considered:

- **Preserve unknown keys.** Rejected by the agreed contract: the schema version describes the whole file, so any new key requires a new version.
- **Use `yaml.safe_load` directly.** It is safe from code execution but silently accepts duplicate keys and large alias graphs. A private loader plus a byte cap keeps the contract strict and bounded.
- **Accept any case variant of the filename.** Rejected: the filename is exact. The consequence is documented rather than guessed.

### Decision: exclusive creation, atomic replacement for future migrations

Adoption and creation must not overwrite an existing `afanes.yaml`. Add `write_text_exclusive()` to `core/atomic.py`: write and fsync a temporary file in the destination directory, then publish it with `os.link()` so an existing target raises `FileExistsError`. On filesystems where hard links are unavailable, fall back to an exclusive open (`O_CREAT | O_EXCL`) and remove a partial file on failure.

`write_text_atomic()` remains the writer for future schema migrations, where replacing the file is intended. Adoption never uses the replacing writer.

Alternatives considered:

- **Check for absence, then call `write_text_atomic()`.** `os.replace` would still overwrite a file created concurrently. The exclusive publisher makes the guarantee real.
- **Use only an exclusive open.** It preserves no-overwrite but leaves a partial file after a crash. The temporary-file plus link path keeps the file atomic where the filesystem supports it.
- **Use locking.** There is no cross-process lock yet; exclusive creation is enough for the current version because every writer produces the same schema 1 content. Future migrations will need a real lock.

### Decision: adoption is a read-only check plus an explicit write

`VaultSchemaStore.is_adoptable()` performs a read-only check: the root exists and is writable, the exact settings file is absent, and all five default folders exist as directories, matched case-insensitively. `templates/` is optional and extra folders are allowed.

`adopt()` rechecks, writes only the settings file, and returns `VaultSchemaAdoption`. If the exact file appears concurrently, the store loads it: a valid file returns `created=False`; an invalid file is refused and preserved. No notes, folders, guide, or cards are written.

Alternatives considered:

- **Seed missing folders or the guide during adoption.** Rejected: a folder with only some default folders is not compatible, and adoption must not turn into creation.
- **Treat a malformed file as missing.** Rejected: it would overwrite a file the application does not understand.

### Decision: open and create integrate at the core gate

`Vault.open()` reads and validates the schema after the existing root checks. It still never writes. A valid read-only vault therefore opens; a missing, invalid, or unsupported schema refuses the vault.

`Vault.create_directory()` writes the schema before seeding folders and starter content, and `VaultCreation` gains `settings_file: Path` so every caller can report it. If a later starter-content write fails, the schema remains and the partial folder can be opened as a vault, matching the existing partial-creation behavior.

Alternatives considered:

- **Validate only in the UI and CLI.** Easier on `service.py`, but a future headless caller could bypass the gate. The schema is part of what it means to open a vault, so the gate belongs with `open`.
- **Write the schema after the notes.** A failure would leave notes in a folder that cannot be opened. Writing first makes partial creation recoverable.

### Decision: one UI field and one controller command

`VaultSession` gains `adoption_target: Path | None`, taking its public surface from 21 to 22 of the 25-name budget. `WorkspaceController` gains `adopt_vault(path)`.

On a missing schema, `WorkspaceController._open_vault_state()` runs `is_adoptable()` in a worker thread. If true, it sets `adoption_target` and shows the adoption offer; if false, it shows the normal refusal message. Invalid and unsupported schemas map to actionable messages. `VaultOpener.open()` continues to translate path errors, but schema errors propagate so the controller can distinguish “missing and adoptable” from “missing and not adoptable.”

The shell renders a shared `Panel` above the welcome or workspace when `adoption_target` is set. The panel carries the explanation and two actions: **Create afanes.yaml and open** and **Cancel**. Confirming calls `adopt_vault()` and re-renders; cancelling clears the target. The current vault remains open until adoption succeeds. The panel uses the existing `Panel` component and the copy/theme leaves; no view defines a duplicate banner, panel, or card helper.

`adopt_vault()` commits the current page, writes the schema and opens the adopted folder in a worker thread, remembers it through the existing preference path, and reports a remember failure without discarding the adopted vault. On a write failure it keeps the current vault and leaves the target available for retry.

Alternatives considered:

- **A modal dialog.** Rejected for the welcome/launch case: the agreed behavior is a non-intrusive message with an action. The shared panel also works in the workspace.
- **A controller field on `AppState`.** `AppState` is at its field and surface budgets. The adoption target belongs to the vault session, not the application facade.
- **A view-local boolean.** The target has to survive the open attempt and a re-render; session state is the correct owner.

### Decision: CLI adopt mirrors create

`afanes vault adopt DIR` uses the same parser group and preference behavior as `vault create`. It writes only the settings file, reports the path, settings file, schema version, and remembered status, and exits `0`. `--no-remember` leaves preferences unchanged. A missing default folder, a read-only folder, or an invalid settings file is refused with exit `1`; an already versioned folder is reported unchanged with exit `0`. If the schema is written but preferences cannot be saved, the command reports the adoption but exits `1`, matching `vault create`.

The `vault create` report adds the settings file. Both commands stay in `cli/` and never import the interface or Flet.

### Decision: documentation and release language change, the read-only-open rule does not

Opening a versioned vault remains read-only, so `AGENTS.md` section 4.5 keeps its “startup and scanning are read-only” rule. The manual gains the schema file and adoption rule in the project snapshot, and the docs update the old “any existing directory is a vault” language.

`README.md`, `RELEASE.md`, `docs/getting-started/first-vault.md`, `docs/reference/vault-format.md`, `docs/reference/troubleshooting.md`, `docs/guide/command-line.md`, and `docs/api/vault.md` are updated. The application preferences file is explicitly described as separate and unchanged.

## Risks / Trade-offs

- **A pre-change vault on read-only media cannot be opened.** → Accepted before 1.0. The docs explain that it must be versioned from a writable location first.
- **The five-folder compatibility rule rejects a trimmed or custom-layout pre-change vault.** → Accepted; adoption is a strict opt-in, not a general importer. The message suggests creating a new vault or adding the file manually.
- **An exact-case `Afanes.yaml` is ignored, and adoption can create a second file.** → The docs state the exact filename. The strict contract was chosen over case-insensitive guessing.
- **A concurrent adoption from two processes could race.** → The exclusive writer makes the first write win; the second sees the valid file and reports “already a vault.” Future migrations, which change the content, will need a cross-process lock.
- **`Vault.open()` now depends on the settings file, so a malformed file blocks opening.** → Intentional: the file is safer to refuse than to guess. Invalid files are never rewritten.
- **`service.py` is close to the 900-line ceiling.** → Keep all parsing, policy, and writing in `schema.py`; `service.py` gains only the import, two calls, and the `VaultCreation` field.
- **An adoption panel adds presentation state.** → One session field and one controller command stay inside the budgets; the shared `Panel` avoids duplicate view helpers.
- **The schema version is not yet exercised by a migration.** → The spec fixes the migration policy now; the first post-1.0 bump supplies the runner.

## Migration Plan

1. New vaults are created with `afanes.yaml` version 1.
2. Existing writable vaults with all five default folders are adopted through the UI or `afanes vault adopt`; only the schema file is written.
3. Existing vaults that cannot be adopted are refused with an actionable message; their Markdown is unchanged and remains readable in any editor.
4. Rolling back is safe: an older application ignores `afanes.yaml` because it is not a note, and no note content was rewritten.
5. Future schema migrations read the recorded version, migrate forward, and write the new version. No migration runner or backup policy is added by this change.

## Open Questions

None. The migration runner, backup location, and cross-process lock are deliberately deferred to the first post-1.0 schema change.
