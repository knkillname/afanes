# Design

## Context

See `proposal.md` - Why for motivation. The current implementation has three related shapes:

- `core/settings.py` pairs an anemic `Settings(vault)` dataclass with `load_settings`, `save_settings`, and `_settings_from_payload`. The parser reaches into a raw mapping, and the I/O functions repeatedly choose between a caller path and `settings_path()`.
- `core/vault.py` passes `vault_root` into nine public operations and several private helpers. The root is resolved and validated on every call, and callers can accidentally mix paths from different vaults.
- `ui/state.py` calls those free functions directly and keeps a bare `vault_root`. Two module-level helpers, `_read_body` and `_open_vault`, carry UI-facing error mapping outside the controller.

`NoteDocument` and `NameCatalog` already show the intended pattern: data and the rules that protect it live together. `links.py` is otherwise mostly pure transformations; only its Markdown parser construction is repeated per note.

Constraints: no behavior, vault format, settings payload, dependency, or platform change. The refactor must be reviewable as a sequence of small API migrations, with the existing suite as the compatibility contract.

## Goals / Non-Goals

**Goals:**

- Give each resource one owner: `SettingsStore` owns the settings file, `Vault` owns a resolved vault root, and `AppState` owns the active `Vault`.
- Put schema rules on the value object (`Settings.from_payload` / `to_payload`) and derive queries on the snapshot (`VaultSnapshot.inbox_notes`).
- Keep stateless transformations as module functions, and make that boundary explicit in `AGENTS.md`.
- Remove the settings-to-vault dependency by extracting the atomic writer.
- Keep every existing user-visible outcome, error message, ordering rule, and file format unchanged.

**Non-Goals:**

- No new features, UI redesign, spec delta, or frontmatter-format change.
- No dependency injection, service container, repository abstraction, or protocol layer for these concrete objects.
- No attempt to class-ify `normalize_name`, `safe_filename`, `parse_reference`, `classify_destination`, or the Markdown span helpers.
- No change to the SQLite/indexer area, CLI, packaging, or async model.
- No compatibility wrappers for removed public functions; the breaking API is recorded and migrated in one step.

## Decisions

### 1. Add an explicit object-boundary directive to `AGENTS.md`

Add a `#### Object boundaries` subsection under 4.3 with four roles:

| Role | Owns | Does not own | Reference examples |
| --- | --- | --- | --- |
| Value object | Immutable data and local invariants; validating factory | File I/O, environment, UI | `Settings`, `VaultNote`, `NoteDocument`, `NameCatalog` |
| Service object | One resource or cross-operation invariant; validated construction | Presentation, UI state | `Vault`, `SettingsStore` |
| Pure function | A stateless transformation | Hidden state, resource handles | `normalize_name`, `safe_filename`, `parse_reference` |
| Controller / view | UI state and presentation | Parsing, SQL, direct file I/O | `AppState`, `InboxView` |

The subsection will include these rules and a review checklist:

- Classify a new unit before writing it; if it spans two roles, split it.
- A function that repeats the same resource parameter across operations is a service waiting to be born.
- A data bag surrounded by free functions is not cohesive; move behavior onto the object or make the data immutable without behavior.
- Do not wrap a stateless transformation in a class merely to satisfy an "OOP" label.
- Services validate their resource at construction and raise domain exceptions.
- Methods express intent (`vault.capture(text)`), not filesystem steps.
- Tests exercise public methods; private helpers are not test subjects.

The existing "Cohesive objects over function bags" bullet will point to this subsection and add `Settings` and `Vault` to its examples. Section 3.1 gains `core/atomic.py`, and section 4.9 records that the atomic primitive lives there and is called by `core/vault.py` and `core/settings.py`.

Alternative considered: expand the existing bullet only. Rejected because a checklist is what future changes need at review time; a single paragraph has not prevented the current drift.

### 2. `Settings` owns its schema; `SettingsStore` owns the file

```python
@dataclasses.dataclass(frozen=True, slots=True)
class Settings:
    vault: Path

    @classmethod
    def from_payload(cls, payload: object, source: Path) -> Self: ...
    def to_payload(self) -> dict[str, object]: ...

@dataclasses.dataclass(frozen=True, slots=True)
class SettingsStore:
    path: Path

    @classmethod
    def default(cls) -> Self: ...
    def load(self) -> Settings | None: ...
    def save(self, settings: Settings) -> None: ...
```

- `from_payload` performs exactly the current version/object/vault validation and raises `ConfigurationError` with the same messages. `_settings_from_payload` is deleted, not delegated to.
- `to_payload` returns the versioned mapping. `save` resolves and expands the vault, rejects a non-directory, creates the parent with mode `0o700`, and writes the resolved path.
- `load` returns `None` for a missing file and raises for read, JSON, shape, version, or absolute-path failures.
- `config_directory()` and `settings_path()` remain module functions: they are platform policy, not an owned resource. `SettingsStore.default()` calls `settings_path()`.
- `load_settings` and `save_settings` are removed. Keeping them as wrappers would preserve the second obvious way and the function-bag shape.

Alternative considered: a `Settings` class with `load`/`save` methods. Rejected because file I/O in the value object breaks the boundary and makes the path a hidden field.

### 3. `Vault` owns the resolved root; `VaultSnapshot` owns inbox queries

```python
@dataclasses.dataclass(frozen=True, slots=True)
class Vault:
    root: Path

    def __post_init__(self) -> None: ...       # resolve and validate the directory
    def contained(self, candidate: Path) -> Path: ...
    def scan(self) -> VaultSnapshot: ...
    def read_body(self, note_path: Path) -> str: ...
    def create(self, title: str, note_type: NoteType, *, directory=None, body="", status="inbox") -> Path: ...
    def capture(self, text: str) -> Path: ...
    def move(self, note_path: Path, destination_directory: Path, *, confirm=False) -> Path: ...
    def plan_rename(self, note_path: Path, new_title: str, *, snapshot=None) -> RenamePreview: ...
    def apply_rename(self, preview: RenamePreview, *, confirm=False) -> RenameReport: ...
    def plan_deletion(self, note_path: Path, *, snapshot=None) -> DeletionPreview: ...
    def delete(self, note_path: Path, *, confirm=False, snapshot=None) -> int: ...
```

- `Vault.__post_init__` resolves `root` once and raises `VaultError` when it is not a directory. `Vault.contained` replaces `contained_path(root, candidate)`.
- `scan` creates one `ReferenceReader` and uses it for every note in that scan. It returns the same `VaultSnapshot` values in the same deterministic order.
- `VaultSnapshot.inbox_notes()` is the existing `inbox_notes(snapshot)` logic moved onto the value object it queries.
- All operation bodies move without semantic changes: confirmation gates, collision checks, hashes, skip/unchanged/failed reporting, atomic writes, and error messages stay identical.
- `resolve_vault_root` and `contained_path` are removed. `Vault(root)` is the validating factory; `Vault(root).root` is the resolved path.
- `_note_paths`, `_find_note`, `_affected_sites`, `_resolves_to`, `_hash_for_note`, `_same_path`, `_rewrite_note`, and `_verify_rewrite` stay private module functions when they are stateless transformations over a snapshot/path. They are not turned into methods merely for style.

Alternative considered: keep a `VaultRoot` value object and a separate `Vault` service. Rejected as two objects for one invariant; the resolved root is the service's resource.

Alternative considered: keep the free functions and add a thin `Vault` facade. Rejected because it leaves two public APIs and does not fix the repeated-root shape.

### 4. `ReferenceReader` owns the Markdown parser; pure reference helpers stay functions

```python
class ReferenceReader:
    def __init__(self) -> None: ...
    def extract(self, markdown: str) -> list[NoteReference]: ...
```

- The reader holds one `MarkdownIt("commonmark")` instance and exposes extraction. `Vault.scan` reuses one reader for all notes; `_rewrite_note` and `_verify_rewrite` may create a reader for a one-off rewrite.
- `extract_references(markdown)` is removed. Tests and callers use `ReferenceReader().extract(markdown)`.
- `parse_reference`, `classify_destination`, `reference_key`, `rewrite_body_references`, and the private span/edit helpers remain module functions. They are stateless, and wrapping them would violate the new directive.
- `NameCatalog` stays a frozen value object with `from_entries` and `resolve`; it is already the reference shape.
- A reader is never shared across threads or scans. Each `Vault.scan` call owns its local reader.

Alternative considered: split `links.py` into `references.py` and `rewriting.py`. Rejected for this change because it adds import churn without changing ownership; the module's public surface is cohesive enough once parser state has an owner.

### 5. `AppState` owns the active `Vault`; views keep `vault_root`

```python
@dataclasses.dataclass(slots=True, eq=False)
class AppState:
    vault: Vault | None = None
    ...
    @property
    def vault_root(self) -> Path | None:
        return None if self.vault is None else self.vault.root
```

- `start`, `choose_vault`, `refresh`, `capture`, and `select_note` call `Vault` methods in worker threads. `choose_vault` still scans before saving settings, preserving the current failure order.
- `_open_vault` becomes a private method that returns a `Vault` and maps missing/file/unreadable paths to the existing UI strings. The module-level `_open_vault` and `_read_body` are removed; `Vault.read_body` replaces the latter.
- `_apply_snapshot` calls `snapshot.inbox_notes()`.
- `vault_root` remains a read-only property, so `InboxView` and `test_app`/`test_inbox_view` do not need a presentation change.
- `SettingsStore.default()` is called in `start` and `choose_vault`; patching `settings_path` in tests still controls the path.
- Tests that need to force a save failure patch `SettingsStore.save`, not a module free function.

Alternative considered: pass a `SettingsStore` or `Vault` into `AppState`. Rejected by the project's no-DI rule; the controller owns the concrete application state and tests patch public module behavior.

### 6. Extract `write_text_atomic` into `core/atomic.py`

- Move the existing function and its docstring unchanged to `src/afanes/core/atomic.py`.
- `core/vault.py` and `core/settings.py` import `afanes.core.atomic` and call it. `settings.py` no longer imports `afanes.core.vault`.
- The function remains a module function: it is a stateless low-level primitive with no resource to own. This is a deliberate example of the pure/stateless side of the directive.
- Tests for the writer move to `tests/core/test_atomic.py`; vault/settings tests stop importing the writer from `vault.py`.
- Architecture tests assert `atomic.py` is a leaf apart from the shared error module, and that `settings.py` does not import `vault.py`.

Alternative considered: leave the writer in `vault.py`. Rejected because it forces app settings to depend on the vault module for an unrelated primitive and obscures the vault service boundary.

### 7. Migration order

1. Add the `AGENTS.md` directive and `core/atomic.py` with its tests; migrate vault/settings imports.
2. Refactor settings, then vault, then links, keeping targeted tests green after each slice.
3. Move `AppState` onto the new objects and update its tests.
4. Add the architecture assertions, then run the full gates.

Each slice is independently revertible. There is no data migration: settings JSON and vault files are unchanged.

## Risks / Trade-offs

- **Large mechanical diff hides a behavior change** -> Keep operation bodies unchanged, run the targeted suite after every slice, and finish with `hatch check`, `hatch test --cover`, and strict OpenSpec validation. The existing behavior specs are the acceptance baseline.
- **Public Python API break** -> The proposal marks it **BREAKING** and this design includes a complete old-to-new migration map. The archive release workflow must classify the bump accordingly.
- **`Vault` construction performs filesystem validation** -> This is intentional service validation. Construct it near the I/O boundary or in a worker thread; do not construct it during module import.
- **Frozen `Vault` with a resolved root** -> Use `object.__setattr__` in `__post_init__` or a classmethod factory. Add a test that `Vault` stores the resolved path and rejects missing/file roots.
- **Parser reuse introduces cross-note state** -> `ReferenceReader` is local to one scan, never global or shared across threads. Add a test that one reader extracts correctly from two documents.
- **Test patch targets move** -> Update tests to patch `SettingsStore` / `Vault` public methods and `afanes.core.atomic.write_text_atomic`; never patch new private helpers.
- **Removing wrappers breaks downstream imports** -> Record the mapping in the release notes/changelog and keep the migration explicit rather than silently aliasing old names.

## Migration Plan

Old to new:

| Old | New |
| --- | --- |
| `load_settings(path)` | `SettingsStore(path).load()` |
| `save_settings(settings, path)` | `SettingsStore(path).save(settings)` |
| `_settings_from_payload(payload, source)` | `Settings.from_payload(payload, source)` |
| `resolve_vault_root(root)` | `Vault(root).root` |
| `contained_path(root, candidate)` | `Vault(root).contained(candidate)` |
| `scan_vault(root)` | `Vault(root).scan()` |
| `inbox_notes(snapshot)` | `snapshot.inbox_notes()` |
| `create_note(root, ...)` | `Vault(root).create(...)` |
| `capture_note(root, text)` | `Vault(root).capture(text)` |
| `move_note(root, ...)` | `Vault(root).move(...)` |
| `plan_rename(root, ...)` | `Vault(root).plan_rename(...)` |
| `apply_rename(root, ...)` | `Vault(root).apply_rename(...)` |
| `plan_deletion(root, ...)` | `Vault(root).plan_deletion(...)` |
| `delete_note(root, ...)` | `Vault(root).delete(...)` |
| `extract_references(markdown)` | `ReferenceReader().extract(markdown)` |
| `write_text_atomic` from `core.vault` | `afanes.core.atomic.write_text_atomic` |

Rollback is a normal revert. Settings files and vault notes need no conversion; reopening either format with the previous code is safe.

## Verification

Implementation review on 2026-11-11:

- The settings payload remains `{"version": 1, "vault": "<absolute path>"}`. Error messages are unchanged except for the local expression that supplies the same path.
- Vault operation bodies moved without logic changes. Confirmation gates, collision checks, optimistic content hashes, skip/unchanged/failed reporting, and error text are preserved.
- Inbox ordering moved to `VaultSnapshot.inbox_notes` with the same modification-time, case-folded name, and relative-path tie-breakers.
- The atomic writer moved unchanged to `core/atomic.py`; both vault and settings writes use it.
- Platform path selection, UTF-8/LF handling, and case-insensitive inbox matching are unchanged.
- `pyproject.toml` has no diff, no network clients were added, and the only `urllib` use remains `urllib.parse` for URL parsing.
- Gates: `hatch check` passed with zero type errors; `hatch test --cover` passed 318 tests at 92%; `openspec validate --all --strict` and `openspec doctor` passed; the vocabulary compliance check was clean.

## Open Questions

None.
