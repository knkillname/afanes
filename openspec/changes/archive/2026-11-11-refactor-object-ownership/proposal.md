# Proposal

## Why

The core code has grown into a mix of cohesive value objects and module-level helper functions. Behavior that belongs to a type often lives outside it: `links.py` threads a Markdown string through seventeen helpers, `vault.py` has twenty-one private module functions around a service that already owns the data, `search.py` has no owning type at all, and `ProcessingPlan.__post_init__` delegates its invariants to four free validators. The result is two places to read for one object, duplicated view helpers, and a 2,341-line `AppState` that satisfies "one class" without cohesion.

`AGENTS.md` already asks for service objects and object ownership, but the manual and the code disagree in practice. This change makes the ownership rule explicit, applies it across the codebase in one coordinated refactor, and adds a hard gate so the old style cannot return.

The change happens now because the domain and vault contracts are stable. Deferring it would force future feature work either to inherit the helper soup or to perform a piecemeal cleanup that is harder to review and easier to abandon.

## What Changes

- Adopt an ownership rule: behavior lives with the data it protects; a one-caller helper becomes a private method; a pure stateless transformation of built-in values may stay a function only in a named policy module; a helper shared by several classes becomes a shared component.
- **BREAKING** Replace the free query functions in `afanes.core.search` with three services: `Browser`, `ProjectBoard`, and `ReviewPlanner`.
- **BREAKING** Move Markdown rewriting from `links.rewrite_body_references` into `MarkdownBody`, and introduce `MarkdownRewrite`, `LinkLabel`, `EditBatch`, `ReferenceKey`, and `CatalogEntry`.
- **BREAKING** Move `allowed_statuses` to `NoteType`, move `scheme_for_note` to `ReferenceScheme.for_note`, and move reference parsing to a core `ReferenceParser`.
- **BREAKING** Replace `PageContent` with a `ParsedPage`/`UnparsedPage` composition union, and replace `PageDraft` with `NormalDraft`/`RawDraft` built around a shared `DraftCommon`.
- **BREAKING** Split `AppState` internally into `VaultSession`, `PageEditorState`, `ProcessingState`, `ReviewState`, and `BrowserState`, behind the existing `app_state` facade.
- Add a hard architecture test that rejects module-level functions with project-type parameters, one-caller private module helpers, duplicate view helpers, and uncontrolled `AppState` growth. The only allowlist entries are `names.py`, `atomic.py`, `ui/strings.py`, and the entry-point callbacks.
- Update `AGENTS.md` with the ownership rule, the decision tree, and the allowlist.
- Release as a major version with a migration note and no compatibility shims.

## Capabilities

### New Capabilities

None. This is a behavior-preserving architectural refactor. The change sets `skip_specs: true`; no product capability or requirement changes. The public Python API changes are recorded in the changelog migration note, not in the product specs.

### Modified Capabilities

None. Vault files, frontmatter, settings JSON, CLI behavior, and UI behavior are unchanged.

## Impact

- Affected code: `core/links.py`, `core/vault.py`, `core/search.py`, `core/processing.py`, `core/frontmatter.py`, `core/editing.py`, `core/settings.py`, `models/note.py`, `models/link.py`, `ui/state.py`, `ui/views/*`, `ui/components/*`, `__main__.py`, and `tests/core/test_architecture.py`.
- Affected APIs: the public Python methods and fields named above move or change shape. The release is `3.0.0` with a changelog migration note. User-visible behavior, CLI flags, vault layout, and file formats do not change.
- Dependencies: none added.
- Systems: the architecture gate becomes part of `hatch test`; no runtime network, telemetry, or cloud behavior is introduced. macOS, Linux, and Windows parity must be preserved.
