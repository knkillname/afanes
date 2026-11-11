# Proposal

## Why

Afanes currently uses the filename stem as the name, the display title, and the identity. That works until a title needs characters a filename cannot hold, or until a title should change without breaking every link to the page. It also makes the Inbox show a sanitized filename instead of the words the user actually wrote. Deriving the display title from the document's first level-1 heading keeps identity stable and makes the vault read the way it was written.

## What Changes

- The display title becomes the first level-1 Markdown heading in the body, falling back to the filename ID when there is none. No `title:` frontmatter key is introduced.
- **BREAKING** for the display model: the filename stem becomes the identity only. It is no longer the display title, so a note whose first H1 differs from its filename is shown under the heading.
- Captures write the first non-blank line as a level-1 heading in the body. The original wording survives even when the filename is sanitized.
- The Inbox lists and previews pages by display title, with the vault-relative path as the secondary line.
- The Processing Wizard's people and project inputs autocomplete by title or ID and always store IDs. Free text is still accepted so a reference to a page that does not exist yet remains possible.
- Existing notes are not rewritten. A note without an H1 simply displays its ID.

Out of scope for this change: the note editor, link-driven page creation, the explicit ID rename screen, and the rename heading rule. Those belong to the following pages-and-editing change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `note-identity`: the filename becomes identity only; the first H1 becomes the display title; name sanitization derives the ID rather than the title.
- `inbox-capture`: capture templates the first line as an H1, and the Inbox lists and previews the derived title.
- `processing`: name entry matches titles and IDs and stores IDs.

## Impact

- `src/afanes/core/frontmatter.py`: derive the first H1 and expose a title on `NoteDocument`.
- `src/afanes/core/vault.py`: carry the title on `VaultNote` and template the capture body.
- `src/afanes/ui/views/inbox.py`, `src/afanes/ui/state.py`: display titles.
- `src/afanes/ui/views/processing.py`: autocomplete inputs for people and projects.
- `AGENTS.md`, `README.md`: identity and capture conventions.
- No new dependencies, no index or schema changes, and no automatic migration.
