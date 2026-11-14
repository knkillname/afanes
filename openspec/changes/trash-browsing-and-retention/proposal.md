# Proposal

## Why

Trash is currently only an in-session undo: the original path lives in memory, collisions
produce ambiguous numbered filenames, and discarded notes cannot be browsed, restored, or
purged after a restart. Notes that are no longer wanted also accumulate forever, because no
retention rule exists. The vault needs a durable Trash that is recognizable, recoverable, and
self-cleaning without becoming a second note catalog.

## What Changes

- Add a **Trash** destination to the workspace navigation, with a managed-note count, rows that
  show the note title and birthplace, a read-only page, and a dedicated group in global search.
- Store newly trashed notes as pure UUID files under `trash/`, so generated names cannot collide
  with real note names such as `Ada 2.md`.
- Record `trashed_from` (vault-relative birthplace) and `trashed_on` (local calendar day) in the
  note's YAML frontmatter. Remove both keys when the note is restored.
- Restore a trashed note to its birthplace, creating missing parent folders. A free birthplace
  restores immediately. An occupied birthplace shows a confirmation that the existing file will
  be permanently overwritten, with Cancel first. There is no Restore As.
- Silently delete managed notes when `trashed_on` is 30 or more days old. Cleanup runs when the
  vault opens and every time Trash is selected.
- Offer **Delete Permanently…** for one managed note and **Empty Trash…** for all managed notes,
  both with confirmation. Hidden unmanaged files are never shown and never deleted by the app.
- Keep the immediate **Undo** toast after moving a page to Trash. Undo restores only while the
  birthplace is free; on collision it reports the condition and leaves the note in Trash.
- **BREAKING**: moving a note to Trash now edits its frontmatter, so the note's bytes are no longer
  unchanged by trashing. Disk files in `trash/` that carry no birthplace metadata become hidden and
  unmanaged, and permanent deletion becomes a real behavior after confirmation or retention.

## Capabilities

### New Capabilities

- `trash-management`: durable trash storage, metadata, hidden unmanaged entries, read-only trashed
  pages, restore and overwrite behavior, retention, and permanent deletion.

### Modified Capabilities

- `vault-layout`: replace the old trash naming and recovery requirement with the new storage
  contract, while keeping trash outside the active catalog.
- `vault-browsing`: add the Trash destination, its rows and count, its search group, clarify that
  active-note groups exclude trashed notes, and record that selecting Trash may run retention.
- `note-editing`: scope the Rename and Move to Trash actions to active notes and name the read-only
  trashed page that offers Restore and Delete Permanently instead.
- `vault-selection`: record scheduled trash retention as the deliberate exception to the
  opening-is-read-only rule, while validation and scanning stay read-only.
- `vault-schema`: scope the opening-no-write guarantee to schema validation so retention can run
  after the workspace opens.
- `interface-theme`: scope the irreversible-confirmation rule to user-invoked actions and record
  scheduled retention as the deliberate exception.

## Impact

Affected code: `core/vault/trash.py`, `core/vault/naming.py`, `core/vault/service.py` scanning,
`core/frontmatter.py`, the new trash catalog and metadata value objects, `ui/state/browser.py`,
`ui/state/pages.py`, `ui/state/session.py`, `ui/state/workspace.py`, `ui/views/workspace.py`,
`ui/views/page.py`, `ui/strings.py`, `ui/theme.py`, and their tests.

Affected behavior: trashing writes frontmatter; snapshot scanning stays read-only and still
excludes `trash/`; a separate read-only trash catalog exposes managed entries; global search adds a
Trash group; `trash/` remains outside note identity, references, Review, and active counts.

No runtime dependency, network, telemetry, or cloud change. No vault schema version bump is
required: `afanes.yaml` is unchanged and the metadata keys are optional frontmatter data. Existing
trash files are not migrated. `AGENTS.md` section 4.5 and the interface standard must record the two
new exceptions: automatic retention may delete after open, and a confirmed restore may overwrite.
