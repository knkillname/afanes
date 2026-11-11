# Proposal

## Why

Afanes can capture, preview, and process notes, but it cannot open a page, edit one, or follow a link. The Inbox preview is deliberately inert, unresolved references are dead ends, and every edit requires leaving the application. A personal wiki needs the opposite: reading a page leads to the pages it references, and editing a page is a first-class, local, file-faithful action.

## What Changes

- Open any note in a right-pane page with a read mode and an edit mode; the Inbox list remains visible beside it.
- Navigate internal links from read mode: a resolved link opens its page, an unresolved link starts a new page, an ambiguous link opens a candidate picker, and external or attachment links stay inert.
- Create a page from an unresolved link using the scheme's type and default folder. The draft opens with the link name as its heading, is written only on first real content, and uses the exact identity or stops with an explanation.
- Offer a previewed, vault-wide link repair when a link name must be sanitized into a safe identity.
- Edit the raw Markdown body and the frontmatter labels: type, category, status, due date, people, and project. People and project inputs reuse the existing title-or-identity suggestions.
- Autosave a dirty draft roughly every 30 seconds and commit on Done, Back, or navigation. Detect an external file change before every write and stop with a Reload or Overwrite choice.
- Preview the inbound references that a type or category change would leave unresolved; confirm or revert the change.
- Provide a raw rescue mode for notes with unparseable frontmatter, and make the link router open the existing file instead of creating a duplicate.
- Expose the existing previewed rename and trash operations from the page.
- Keep one browser-like page history for list clicks and link taps, with Back returning through it.

## Capabilities

### New Capabilities

- `note-editing`: reading a note as a page, editing its body and labels, autosaving and conflict detection, creating pages from unresolved links, link navigation, raw rescue, and the page-level rename and trash actions.

### Modified Capabilities

- `inbox-capture`: selecting a note opens the page read mode, and link taps navigate instead of being inert.
- `note-identity`: a rename keeps a heading that still matches the old identity in step with the new identity.

## Impact

- `src/afanes/core/`: reading a full note with a content hash, exact-identity creation, a page save operation with conflict checks, link-target resolution over the scan snapshot, and reference-repair reuse.
- `src/afanes/ui/`: the application shell, `AppState`, a page view and components, strings, and theme.
- `tests/`: core save/creation/link-routing tests, state tests, and view tests.
- No new dependencies, no network access, no cache schema change, and no change to the Markdown file format.
- `README.md` and `CHANGELOG.md` update at release time.
