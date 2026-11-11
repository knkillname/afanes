# Proposal

## Why

Afanes has a reference engine but no way to put a thought into a vault or see it afterward. The first runnable slice is the capture loop: choose a vault, dump a thought, see it in the Inbox, and read it. Without that loop the engine has no user-facing entry point, and the architecture remains unproven against the GUI toolkit.

## What Changes

- Add a desktop entry point, `python -m afanes`, built on Flet, with a first-run welcome screen that selects a vault and remembers it.
- Add platform-aware settings storage: a versioned JSON file in the user's configuration directory, written atomically and recoverable when missing or corrupt.
- Make `inbox/` the capture queue. The Inbox view lists every note under that directory, recursively, newest first.
- Add capture: the first non-blank line becomes the filename, the full text becomes the body, and the note is written as `type: note` with no `status` key.
- Add a read-only rendered Markdown preview; link taps are inert in this change.
- Extend `create_note` to accept `status=None` without changing its existing default, and add a `capture_note` workflow that applies the capture rule.
- Report notes that cannot be parsed in a warning banner while still showing the readable ones.
- Update `AGENTS.md` so `status` is optional until processing begins and the Inbox is documented as a folder rather than a status.
- Add Flet as a pinned runtime dependency and its desktop client to the development environment. Packaging and the one-time client provisioning are documented, but producing a distributable build is out of scope.

No **BREAKING** changes: existing callers of `create_note` keep the current default behavior.

## Capabilities

### New Capabilities

- `vault-selection`: choosing a vault on first run, persisting it outside the vault, reopening it on later launches, changing it, and recovering from a missing or corrupt configuration.
- `inbox-capture`: capturing a thought into `inbox/`, deriving the filename, listing notes newest first, previewing a note read-only, and reporting unreadable notes.

### Modified Capabilities

None. `note-identity` and `note-references` keep their current requirements; the new behavior composes with them.

## Impact

- `src/afanes/__main__.py` (new): GUI entry point.
- `src/afanes/core/settings.py` (new): platform configuration paths, settings load and save.
- `src/afanes/core/vault.py`: `create_note` accepts `status=None`, plus `capture_note` and inbox path helpers.
- `src/afanes/ui/` (new): `app.py`, `state.py`, `theme.py`, `strings.py`, and `views/inbox.py`.
- `pyproject.toml`: pinned Flet runtime dependency and `flet-desktop` in the development group.
- `AGENTS.md` sections 1.3 and 1.4: `status` becomes optional until processing; the Inbox is described as the `inbox/` folder.
- `README.md`: development launch instructions and first-run behavior.
- Tests for settings, capture, inbox filtering and ordering, and `AppState`; no rendered window is required.
- No indexer, CLI, editing, Processing Wizard, packaging, accounts, telemetry, or runtime network access.
