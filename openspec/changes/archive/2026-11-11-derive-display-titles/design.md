# Design

## Context

See `proposal.md` - Why. The current identity rule is absolute: a note's filename stem is its name, display title, and identity. Sanitization therefore rewrites the visible name, and the Inbox can only show the cleaned-up filename.

The behavior in this change follows a convention used by desktop wikis such as Zim: the first level-1 heading is the title, the page name is the identity and the fallback title, and a page name is stable while its heading can be rewritten. This change borrows the title rule, not the hierarchical namespace model.

Constraints that shape the approach:

- Vault files remain authoritative; the title is derived from the body and is never stored separately.
- `core/` and `models/` stay free of Flet; the UI forwards intent and renders values.
- Existing notes must keep parsing and must not be rewritten.
- The capture queue stays minimal: no new frontmatter key, no inferred structure.
- Matching stays case- and whitespace-insensitive through the existing name normalization.

## Goals / Non-Goals

**Goals:**

- Derive a display title from the first level-1 heading, falling back to the identity.
- Keep identity, uniqueness, and reference resolution on the filename stem.
- Keep the original wording of a capture visible even when the filename is sanitized.
- Let the Processing Wizard suggest pages by title or identity while storing identities.
- Leave every existing vault file unchanged.

**Non-Goals:**

- A `title:` frontmatter key or any second source of truth.
- The note editor, link-driven page creation, and the explicit ID rename screen.
- Renaming that offers to update the heading when it matches the old identity.
- Storing titles in the SQLite index; that belongs to the views/index change.
- Changing reference resolution to match titles.

## Decisions

### 1. Identity remains the filename; the title is derived

`NoteDocument` gains a derived `title: str | None`. `VaultNote.title` is that value, falling back to the scanned filename stem. `NoteDocument` does not know about paths, so the fallback belongs to the vault layer. This keeps the value object free of filesystem concerns and the display fallback in one place.

Alternative rejected: a `title:` frontmatter key. It would create two names that can disagree, add a format surface, and require validation and migration. The H1 already exists in the document and is readable without Afanes.

### 2. Title extraction uses the Markdown parser, not a regex

The first `heading_open` token with tag `h1` in the body supplies the title. Its inline content is flattened to plain text so a heading such as `# **Ada** Lovelace` displays as `Ada Lovelace`. Code blocks, blockquotes, and escaped lines are handled by the parser, so a `#` inside a fenced block is never a title.

Setext headings (`Title` followed by `===`) are level-1 headings in CommonMark and therefore count. If the first level-1 heading has blank text, the note falls back to its identity rather than searching for a later heading. The title is trimmed; internal whitespace and case are preserved.

Alternative rejected: a line-oriented regex. It cannot distinguish a heading from a fenced code block without duplicating the Markdown grammar.

### 3. Capture inserts the heading marker

`Vault.capture` finds the first non-blank line and inserts `# ` at its start unless the line's first non-whitespace character is already `#`. The rest of the captured text is untouched, leading blank lines included. The existing newline normalization and atomic write still apply.

This is a capture policy, so it lives in `Vault.capture`, not in `NoteDocument`. `NoteDocument` only derives a title from whatever body it receives. A capture whose first line is already a heading is left as typed, including `##` or deeper, which means it falls back to the identity until the user edits it.

Alternative rejected: deriving the title from the first line when no H1 exists. That would make the first line a second title source and contradict the fallback rule.

### 4. Display uses the title everywhere a page is named

- The Inbox list shows `VaultNote.title` as the primary text and the vault-relative path as the secondary text. Duplicate titles remain distinguishable by path.
- The Inbox preview header shows the title; the rendered body still contains the H1, so the heading appears in both places. That duplication is normal for a document viewer and keeps a note without an H1 readable.
- The Processing Wizard's capture panel shows the title instead of the filename stem.
- The Processing Wizard's people and project fields suggest pages by title or identity.

Reference resolution, uniqueness checks, rename targets, and collision messages continue to use the identity. A title never appears in a link destination.

### 5. Suggestions are presentation over a core query

The wizard keeps free-text inputs. Under each field, a suggestion list shows matching pages as the user types. A suggestion displays the title and, when it differs, the identity; selecting it replaces the active comma-separated token with the page identity. The project field uses the same rule for its single value.

The matching query lives in `VaultSnapshot.assignment_candidates(scheme, query)`: it filters notes by scheme, normalizes the query and each candidate's identity and title with `afanes.core.names.normalize_name`, and returns substring matches ordered by title then identity. It is pure in-memory work, so the UI never parses names and the vault is not rescanned per keystroke. Free text that matches no page stays as typed and is reported as unresolved, preserving the existing ability to assign a page that does not exist yet.

Alternatives rejected: a strict picker removes unresolved assignment; an exact-title match on submit would silently resolve titles, which is the ambiguity this change is trying to avoid. A dedicated `title:` index is unnecessary until the views/index change needs one.

`AppState` retains the last `VaultSnapshot` so the suggestion query and the Inbox list share one scan. The view asks the controller for candidates; the controller owns the scheme selection.

### 6. No migration and no writes

Existing notes are parsed as they are. A note with an H1 displays that heading; a note without one displays its filename. A legacy `title:` key is unknown frontmatter, preserved but ignored. No file is rewritten by this change, so rollback is a code revert.

## Risks / Trade-offs

- **A mid-document H1 becomes a title.** A document with an intro paragraph and a later `# Section` displays `Section` as its title. Mitigation: the rule is documented, the fallback is the identity, and the editor change will let the heading be edited.
- **Duplicate titles in the Inbox.** Repeated captures with the same first line produce the same title. Mitigation: the secondary line is the vault-relative path, and assignment suggestions show identities.
- **Extra Markdown parse per note.** Title extraction parses the body in addition to reference extraction. Mitigation: one parse per note per scan; the future index can cache titles.
- **Capture bodies change shape.** New captures start with `#`, so tests and clients that expect the raw text need updating. Existing notes are untouched.
- **Suggestions are O(notes) per keystroke.** Acceptable for a local vault; the future SQLite index can back the query when vaults grow.
- **Existing `title:` keys are ignored.** A vault that used `title:` for display will now show the H1 or the filename. Mitigation: documented in `README.md`; the key remains in the file and can be migrated manually.

## Migration Plan

1. Back up the vault, as with any behavior change.
2. Install the new version. No file rewrite is required.
3. Review notes whose first H1 differs from the filename; the new title is intentional under this rule.
4. Rollback: revert the application. The vault was not modified, so all notes remain valid.

## Open Questions

- Whether future views should sort by display title or by identity. Deferrable; this change only affects naming and display.
- Whether the SQLite index should store a normalized title column for search. Deferrable to the views/index change.
