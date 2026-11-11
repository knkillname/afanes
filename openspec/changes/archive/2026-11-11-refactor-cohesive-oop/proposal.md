# Proposal

## Why

The first capture loop works, but its core APIs still read like a set of free functions around data bags. `_settings_from_payload` reaches into a raw mapping, `AppState` calls `load_settings`, `save_settings`, `scan_vault`, and `capture_note` directly, and every vault operation repeats the same root path. That shape invites the next feature to copy the pattern instead of extending an object that already protects the invariant.

The end-to-end capture suite now gives us a safety net. This is the right moment to refactor once, record the object-boundary rules in `AGENTS.md`, and make every later change follow them instead of scheduling another sweep.

## What Changes

- Add an **Object boundaries** directive to `AGENTS.md` section 4.3: value object, service object, pure function, and controller/view, with a review checklist and reference examples. Update the repository layout and file-I/O guidance for a shared atomic writer.
- **BREAKING** Replace the free-function settings API with a cohesive value object and store: `Settings.from_payload` / `Settings.to_payload` own the schema, and `SettingsStore` owns the settings file. Remove `load_settings`, `save_settings`, and `_settings_from_payload`.
- **BREAKING** Introduce a `Vault` service that owns the resolved root and exposes `scan`, `contained`, `read_body`, `create`, `capture`, `move`, `plan_rename`, `apply_rename`, `plan_deletion`, and `delete`. Move `inbox_notes` onto `VaultSnapshot` and remove the corresponding free functions.
- **BREAKING** Add a `ReferenceReader` that owns one configured Markdown parser per scan, replacing the free `extract_references`. Parse, classify, catalog, and rewrite behavior stay the same.
- Extract `write_text_atomic` into `core/atomic.py` so vault and settings share one atomic-write primitive without setting up a settings-to-vault dependency.
- Refactor `AppState` to hold a `Vault | None`, use `SettingsStore`, and keep `vault_root` as a read-only property for existing views.
- Update tests and architecture tests to exercise the new public surfaces. No vault format, settings JSON schema, UI copy, or user-visible workflow changes.

## Capabilities

### New Capabilities

None. This is a structural refactor with no spec-level behavior change.

### Modified Capabilities

None. Existing behavior remains governed by `inbox-capture`, `vault-selection`, `note-identity`, and `note-references`. The change sets `skip_specs: true` because it changes ownership and call sites, not requirements or observable behavior.

## Impact

Affected code: `src/afanes/core/settings.py`, `src/afanes/core/vault.py`, `src/afanes/core/links.py`, a new `src/afanes/core/atomic.py`, `src/afanes/ui/state.py`, `AGENTS.md`, and the corresponding tests.

No dependencies, vault files, settings payloads, CLI commands, or UI behavior change. The refactor does remove public Python functions, so the archive release should classify it as a breaking API change with the migration map recorded in `design.md`. The project remains offline-only and cross-platform.
