# Proposal

## Why

Afanes must reference notes by name so that moving a note between classification folders never breaks the graph, but the currently documented `[[Target]]` syntax is proprietary: it renders as literal brackets in every other Markdown tool, cannot be resolved outside Afanes, and makes the vault legible only to this application. That contradicts the principle that the Markdown files, not the cache or the app, are the source of truth. Standard Markdown link syntax with typed schemes keeps references name-based and human-guessable while leaving the body valid, navigable Markdown everywhere else.

## What Changes

- Replace the `[[Target]]` and `[[Target|Label]]` syntax with `[Label](scheme:Name)`.
- Introduce three schemes: `person`, `project`, and `note` (where `note` covers the `note`, `action`, and `reference` types).
- Make the filename stem the note's name, title, and identity. No separate title key and no stored `id` field.
- Treat the directory hierarchy as classification only. Moving a note between folders never changes its reference, so moves are free.
- Make renames app-owned. The application previews, confirms, and rewrites affected references, one atomic file write at a time, and reports partial results.
- Use the same `scheme:Name` form in frontmatter `people` and `project` values.
- Require explicit links only. Do not auto-link bare CamelCase words or bare names.
- Keep attachments and external URLs in standard Markdown forms.
- Sanitize names for cross-platform filenames at creation and rename time, and enforce per-scheme, vault-wide name uniqueness.
- **BREAKING**: the canonical vault format no longer recognizes `[[...]]` links. No vault exists yet, so no migration is required, but the documented format changes.

This change delivers the core reference and naming engine. Link rendering, the persistent cache, and CLI diagnostics consume it in later changes and are out of scope here.

## Capabilities

### New Capabilities

- `note-references`: the scheme link grammar, extraction of references from Markdown and frontmatter, resolution to notes, the unresolved and ambiguous failure states, and the distinction between internal references, external URLs, and attachment paths.
- `note-identity`: the filename as name, title, and identity; cross-platform name sanitization; per-scheme uniqueness; case and Unicode matching; the move-free and rename-owned behavior; and the boundary between app-managed structure and externally editable content.

### Modified Capabilities

None. No main specs exist yet, so both capabilities are introduced by this change.

## Impact

- `core/links.py`: reference extraction, destination classification, catalog building, and resolution replace wikilink parsing.
- `models/link.py`: a reference value object replaces the wikilink value object.
- `models/note.py`: the note type enum needed to map schemes to target types.
- `core/names.py`: name normalization, filename sanitization, and collision suffixing.
- `core/frontmatter.py`: a fence parser and safe YAML loading for metadata and reference values.
- `core/vault.py`: name sanitization, uniqueness checks, atomic writes, moves, and rename-with-reference-maintenance.
- `cli/doctor.py`, `core/indexer.py`, `core/search.py`, and `ui/`: later consumers of this engine; not built in this change.
- `pyproject.toml`: adds a CommonMark-compliant Markdown parser and PyYAML as pinned runtime dependencies.
- `AGENTS.md` sections 1.3, 2.4, 3.1, and 4.7: the canonical format, identity rules, and dependency list.
- No network access, accounts, telemetry, or new services.
