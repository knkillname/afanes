# Proposal

## Why

A vault is only accepted when the folder already exists, so the first run asks a new user for
something they may not have, and a browser session — which offers no directory dialog — has no way
forward at all. Nothing can provision a vault: not the interface, not the installed command, not any
other entry point.

## What Changes

- Add a **New vault** action to the welcome state and to the change-vault action in both
  presentations. It takes a path, creates the directory, seeds the default folders, remembers the
  vault, and opens it.
- Refuse creation into an existing non-empty folder or onto a file. Missing intermediate folders are
  created along with the vault and reported, so a mistyped path is visible immediately rather than
  discovered later.
- Seed `inbox/`, `trash/`, `reference/`, `reference/people/`, `projects/`, and `actions/` by reusing
  the destination policy that already defines those folders for note writes.
- Add `afanes vault create DIR` as the first headless subcommand, with `--no-remember`, documented
  exit codes, and no graphical dependency.
- Make the installed `afanes` command dispatch a recognized subcommand and start the interface
  otherwise. `python -m afanes` keeps its current behavior, and the console-script target is
  unchanged.
- Move vault path validation from the interface controller into core so the interface and the
  command share one rule, and add the creation operation beside it.
- No marker file, no "initialized" state, and no placeholder files. A seeded vault remains an
  ordinary directory of Markdown files.

Non-goals: `vault list`, `vault info`, or `vault remove` subcommands; a flag that skips the default
folders; placeholder files that survive version control; onboarding sample notes; creating a
remembered vault automatically during recovery; user-defined reference categories such as `places`,
which is a separate change to the note format and validation. Seeding is written against the
category map so that change can extend it without touching creation.

## Capabilities

### New Capabilities

- `command-line`: the installed command surface, how it dispatches headless subcommands, and the
  exit codes, output stream, and display-free guarantees every command holds.

### Modified Capabilities

- `app-runtime`: the installed `afanes` command starts the interface when no subcommand is given and
  dispatches recognized subcommands headlessly.
- `vault-selection`: a vault can be created on request at a missing or empty path, in both
  presentations, and remembered like a chosen one.
- `vault-layout`: creating a vault seeds the default folders, and lazy creation distinguishes an
  explicit creation from an implicit write.

## Impact

- **Core**: new vault open and create operations, distinct domain errors for a missing,
  non-directory, or unreadable vault path, and seeded folders computed from the existing destination
  policy. No frontmatter, index, or SQLite change.
- **Command line**: a new `afanes/cli/` package plus a dispatch branch in the installed entry point.
- **Interface**: a creation dialog in the welcome state, a create command on the controller, and
  reuse of the existing path dialog for desktop creation.
- **Tests**: core creation and refusal cases, command exit codes, both presentations, and
  architecture gates for the new package.
- **Documentation**: README command usage and creation flow, plus a changelog entry.
- **Compatibility**: no vault format change and existing vaults open unchanged. `--web`, `--vault`,
  and `--port` keep their current meaning.
