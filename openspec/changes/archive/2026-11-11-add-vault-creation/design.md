# Design

## Context

See `proposal.md` for motivation and the delta specs for required behavior.

Current state that shapes the approach:

- `Vault` is a frozen service object that validates an existing directory in `__post_init__` and owns
  every vault write. It already exposes `directory_for()`, which maps a note kind to its default
  folder and reuses an existing case variant **without creating anything**. `CATEGORY_DIRECTORIES`
  maps `person` to `people`; `trash/` is computed separately because it has no note type.
- `VaultOpener` in `ui/state.py` is the only path-validation entry point: `exists` → `is_dir` →
  `os.access(R_OK)` → `Vault`. It raises `VaultError` carrying UI copy, and it performs file I/O from
  the interface layer.
- The installed command is `afanes = "afanes.__main__:main"`. `__main__.py` parses launch options,
  checks the presentation runtime, and starts Flet. A test asserts the console-script target string,
  so changing it would break a documented contract for no gain.
- There is no `src/afanes/cli/` package. The architecture gate scans every module under `src/afanes`
  and rejects module-level functions outside an explicit allowlist.
- Opening and scanning are read-only today, and a missing remembered path is never recreated. That
  must survive this change unchanged.

## Goals / Non-Goals

**Goals:**

- One creation rule shared by the interface and the command line, with no duplicated path checks.
- A headless command surface that can grow without a second console script or a second entry point.
- Seeding expressed through the layout policy that already exists, not a parallel list.
- No new runtime dependency, no network access, no vault format change.

**Non-Goals:**

- Replacing the native directory dialog for opening.
- Making the seeded layout meaningful to a later scan, or introducing any marker, version, or
  initialized state.
- Deleting, rolling back, or repairing directories the application did not create.
- Adding commands beyond `vault create`.

## Decisions

### 1. Seeding is a convenience, never a state

A created vault is an ordinary directory with six empty folders. Nothing recorded anywhere says it
was created, so a later open cannot and must not treat it specially. This keeps `vault-selection`
and `vault-layout` internally consistent: any existing directory is still a vault, and the seeded
folders remain conveniences that can be deleted without consequence.

*Alternatives rejected:* a `.afanes` marker or a version file (creates a state to migrate and breaks
"no marker is created"); inferring "created" from the presence of the folders (fragile and false for
hand-made vaults); placeholder files to survive version control (pollutes the vault and makes
`inbox/` non-empty, which the Inbox empty state depends on).

### 2. Core owns validation and creation

`core/vault.py` gains:

```
Vault.open(path)    -> Vault     validate an existing directory
Vault.create_directory(path) -> VaultCreation  validate, create, seed
```

`Vault.create_directory` reuses the existing destination policy: `directory_for()` for the note destinations, one
subfolder beneath `reference/` per entry in `CATEGORY_DIRECTORIES`, plus
`_existing_directory(root, TRASH_DIRECTORY)` for trash. Seeding calls
`mkdir(parents=True, exist_ok=True)` on those paths, so it can never produce a case-variant
duplicate.

Seeding iterates the category map rather than naming `person`. A later change that makes reference
categories configurable therefore extends creation by extending the map, without editing the
creation code.

`ui/state.py.VaultOpener` stays as the interface's translation point and delegates to
`Vault.open`/`Vault.create_directory`, mapping domain errors to the strings the interface already owns. This
keeps its public surface intact, removes `os` and path I/O from the interface, and lets `__main__.py`
validate `--vault` through core without importing a `ui/` module.

*Alternatives rejected:* duplicating the checks in `cli/` (violates DRY and will drift); moving the
strings into core (puts user-facing copy in the domain layer); deleting `VaultOpener` (a public class
in a shipped module, so removal would force a breaking release for no user benefit).

### 3. Path failures are distinct exception types

`core/errors.py` gains four subclasses of `VaultError`, each mapping to one user-facing sentence:

| Exception | Raised when |
| --- | --- |
| `VaultMissingError` | the path does not exist |
| `VaultNotDirectoryError` | the path exists and is not a directory |
| `VaultUnreadableError` | the directory cannot be read |
| `VaultNotEmptyError` | creation was asked for a non-empty directory |

`Vault.__post_init__` raises the first two instead of a generic message, which is compatible with
every existing `except VaultError`. Callers format their own copy, so the interface and the command
line do not share presentation text.

*Alternatives rejected:* one error with a reason enum (more machinery for the same result); parsing
messages (brittle).

### 4. Creation policy: missing or empty, creating parents, no rollback

```
DIR missing, any parent depth      -> mkdir DIR and missing parents, seed, succeed
DIR exists and is an empty directory -> seed, succeed
DIR exists and is not empty        -> VaultNotEmptyError, nothing written
DIR exists and is a file           -> VaultNotDirectoryError
```

The target is resolved before the emptiness check, so a symlink cannot smuggle a populated directory
past the refusal. Missing intermediate folders are created with `mkdir(parents=True)`, so
`~/Notes/Afanes` works on a machine with no `Notes` folder yet.

Because a mistyped path now builds a tree instead of failing, creation reports every directory it
creates, intermediate ones included. The interface shows the resolved path in the dialog preview and
the command prints the created directories on standard output, so a typo is visible immediately
rather than discovered days later.

Seeding is not rolled back. A partially seeded directory is still a valid vault, and deleting
directories the application just made is more dangerous than leaving them. The failure names the
folder that failed, and the created ones stay.

*Alternatives rejected:* requiring the parent to exist (a typo fails loudly, but it also blocks the
ordinary case of a first vault in a folder that does not exist yet, such as `~/Notes/Afanes`);
transactional temp-directory rename (fails on Windows when the target exists, and leaves a visible
temporary sibling); rollback with `rmdir` (recursive-delete risk for a cosmetic benefit);
idempotent seeding of any directory (silently turns a typo into "repair").

### 5. Dispatch from the installed entry point

```
afanes  (console script: afanes.__main__:main, unchanged)
   |
   +-- argv[0] is a recognized subcommand --> afanes.cli.main.main(argv)
   |                                          returns an exit status
   +-- otherwise --------------------------> LaunchOptions.parse -> GUI
```

Dispatch happens before the runtime check and before any Flet import, so `afanes vault create` works
on a machine with no GUI runtime installed. `Launcher.dispatch` is a static method on the existing
`Launcher` class, so the entry-point function allowlist does not grow.

`python -m afanes vault create DIR` works through the same path, satisfying the module-form
requirement.

*Alternatives rejected:* a second `afanes-cli` console script (two names for one product); argparse
subparsers wrapping the GUI options (the GUI parser must stay importable without the CLI and vice
versa); a dispatcher module with its own `main` (an extra allowlist entry and layer for no gain).

### 6. The CLI is a headless adapter

```
src/afanes/cli/
  __init__.py     package docstring only
  main.py         argparse parser, subcommand dispatch, `main` entry callback
  vault.py        VaultCommand.create: the vault create command
  strings.py      command messages and usage text
```

`cli/` imports `core/` and `models/` only. No Flet import, no `ui/` import, no display requirement,
no SQL. The command computes results through `Vault.create_directory` and `SettingsStore`, and writes to
standard output on success and standard error on failure. Exit codes: `0` success, `1` expected
failure, `2` usage error (argparse default).

The architecture gate gains exactly one entry, `"cli/main.py": frozenset({"main"})`, and its
exact-allowlist assertion; `AGENTS.md` section 4.3 is updated to list the same callback. New tests
assert that `cli/` imports neither `afanes.ui` nor `flet`, and the existing acyclicity test covers
the new package.

*Alternatives rejected:* implementing the command as a module-level function (the gate rejects it
outside the allowlist and it would bypass the ownership rule); putting creation in `__main__.py`
(mixes a graphical launcher with headless behavior).

### 7. Creation remembers by default

`afanes vault create DIR` writes preferences unless `--no-remember` is given, matching what the
interface does. A provisioning script that should not touch the user's remembered vault passes
`--no-remember`. When the vault is created but preferences cannot be written, the command reports
that the vault exists but was not remembered and exits `1`; the interface instead opens the created
vault for the session and reports the same fact, because refusing to open a directory that was just
created leaves the user with nothing to show for the action.

The settings write already goes through the atomic writer and is the only non-vault write in the
command.

### 8. Creation uses the picker on desktop and a typed path in a browser

A native directory dialog cannot return a folder that does not exist, but it can create one: every
supported platform's folder chooser has a new-folder action. The desktop creation action therefore
opens that dialog and seeds whatever folder it returns, so the desktop never asks for a typed path.

A browser session has no directory dialog, so it keeps a path field with a preview of the seeded
folders before anything is written.

```
welcome state
  desktop:  [Choose vault] -> native dialog -> open
            [New vault]    -> native dialog -> create + seed
  browser:  path field + [Open]
            [New vault]    -> path dialog with folder preview -> create + seed

vault open
  desktop:  [Change vault] -> open existing (picker) or New vault (picker)
  browser:  path dialog    -> Open or New vault
```

A picked folder that is not empty is refused after the dialog has closed, so the desktop reports it
as a banner over the welcome state or workspace. The browser dialog keeps an inline error because the
typed path is retryable without reopening it. Creation runs in a worker thread through
`asyncio.to_thread`, matching every other vault command.

This keeps the presentation difference to "opening uses a native dialog where one exists", which is
the difference `app-runtime` already permits.

### 9. Creation is available wherever a vault is chosen

The New vault action appears in the welcome state and in the change-vault action. Opening keeps the
native picker on desktop, so the change-vault control becomes a two-choice action: open an existing
folder through the picker, or name a new vault in the creation dialog. A browser session already
uses a path dialog for changing vaults, so it gains the New vault action beside Open.

Creating a second vault while one is open is a normal vault switch: the new vault is scanned and
remembered, and the previous vault is never written. Creation is never the only way to change
vaults, so no existing flow is removed.

### 10. Success output is a structured summary

The command prints the created vault path, the parent folders it created when there were any, the
seeded folder names, and whether the vault is now the remembered one. That is enough for a user to
spot a mistyped path without printing nine absolute paths, and it needs no machine-readable mode.

*Alternatives rejected:* one line per created directory (noisy for the common case); one summary
line (hides intermediate folders, which is the exact evidence a typo needs); a `--json` flag (no
consumer exists, and project policy requires a spec before adding machine-readable output).

## Data flow

```
UI:   dialog text -> AppState.create_vault(Path)
                        -> asyncio.to_thread(Vault.create_directory)
                        -> SettingsStore.save            (failure: keep vault, report)
                        -> vault.scan -> state update

CLI:  argparse -> VaultCommand.create(Path, remember)
                        -> Vault.create_directory
                        -> SettingsStore.save            (failure: exit 1)
                        -> print summary -> exit 0
```

Both paths call the same two core operations, so behavior cannot diverge except in copy and the
settings-failure handling documented above.

## Failure modes and recovery

| Failure | Behavior |
| --- | --- |
| Non-empty target | Refused before any write; the existing contents are untouched |
| Target is a file | Refused; the file is untouched |
| Parent missing | Created along with the vault; every created directory is reported |
| Target unreadable after creation | Reported; the directory stays, no note is written |
| Seeding fails midway | Reported with the failing folder; earlier folders stay; the vault is still usable |
| Preferences cannot be written | UI opens the vault for the session and says so; CLI exits `1` |
| Another process creates the target between check and seed | The seed runs inside a now non-empty directory; harmless, no data is lost |
| Creation in a browser session | Same core path; no native dialog involved |

No cache invalidation and no vault migration: creation produces ordinary folders.

## Cross-platform notes

- `mkdir()` uses the platform default mode; the restrictive `0o700` belongs to the settings
  directory, not to vault content.
- The six seeded names are safe on Windows, are not reserved device names, and have no trailing dot
  or space.
- On case-insensitive filesystems an empty target cannot already hold a case variant, so seeding
  cannot create a duplicate. Case-variant reuse still governs note writes.
- `os.access(R_OK)` does not reflect Windows ACLs. This limitation already exists in `VaultOpener`
  and is unchanged; a readability failure surfaces on the first read instead.
- The target is resolved before validating, so a symlinked path is created inside its real parent
  and a symlink to a populated directory is refused.
- UI creation blocks in a worker thread; the command blocks normally.

## Test strategy

- `tests/core/test_vault.py`: creation at a missing path, at an empty directory, with missing
  intermediate folders, refusal for a non-empty directory and a file, exactly six seeded folders, no
  files, and seeded folders resolving to the same paths `directory_for()` predicts. A Hypothesis
  property asserts every seeded path stays inside the resolved root for generated directory names.
- `tests/core/test_architecture.py`: the new allowlist entry, `cli/` importing neither `afanes.ui`
  nor `flet`, and the acyclic graph.
- `tests/cli/test_main.py`: dispatch from `afanes` with and without a subcommand, usage errors
  exiting `2`, creation exiting `0` with output on standard output, each refusal exiting `1` with
  output on standard error, settings written by default, untouched with `--no-remember`, and a
  settings failure exiting `1` while leaving the vault in place.
- `tests/ui/test_state.py`: `create_vault` success, refusal, and settings-failure behavior.
- `tests/ui/test_app.py`: desktop creation through the directory picker, browser creation through the
  path dialog with its folder preview and inline error, and cancellation writing nothing in both.
- `tests/ui/test_launch.py`: existing launch-option behavior is unchanged, and the console-script
  target assertion still holds.

## Migration

No data migration. Existing vaults open unchanged. Rolling back the change leaves every created
vault valid, because a vault was always just a directory; nothing in the vault records that Afanes
created it.

## Risks / Trade-offs

- **A mistyped path builds intermediate folders.** → Every directory the application creates is
  reported, intermediate ones included, and the dialog preview shows the resolved path before the
  user confirms.
- **Seeded folders vanish in version control.** Git does not track empty directories, so a cloned
  vault has no seed. → Documented as a caveat; lazy creation keeps the vault usable.
- **Two desktop routes produce cosmetically different vaults.** Picker plus the dialog's New Folder
  gives an unseeded vault; New vault gives a seeded one. → Behavior is identical; README states
  which route seeds.
- **A generated path replaces the remembered vault by default from the CLI.** → `--no-remember` is
  documented in the command help and the README; the write is atomic.
- **The refusal for a non-empty directory is inconvenient for reprovisioning scripts.** → It is
  deliberate, exits `1`, and the message points at opening the folder instead.
- **`VaultOpener` remains as a translation wrapper.** → It is four lines of mapping and keeps a
  public surface stable; removing it is a separate, deliberate breaking change.
