# Design

## Context

See `proposal.md` for motivation and the spec deltas for the behavior contract. The current code
already has a `TrashService` that plans, moves, and restores one note with an in-memory
`TrashPreview`, and `Vault.scan()` deliberately excludes `trash/` and `templates/` from the active
catalog. The active scan, its fingerprint, and every reference rule depend on that exclusion, so the
trash feature must not add trashed notes to `VaultSnapshot`.

The application also has two hard architectural constraints: `AppState` may declare at most 10
annotated fields, and UI views must not own parsing or file I/O. Any trash state must fit inside
existing controllers.

Two existing read-only guarantees need an explicit boundary. `Vault.open()` and `Vault.scan()` stay
read-only, and schema validation stays read-only. The workspace-level cleanup is a separate
maintenance step after validation; `vault-selection`, `vault-schema`, and `AGENTS.md` must name that
exception so the old absolute wording does not contradict the new behavior. The page-action
requirement in `note-editing` must also distinguish an active page from the read-only trashed page.

## Goals / Non-Goals

**Goals:**

- Give trash a durable, restart-safe identity and origin without joining the active catalog.
- Keep every active scan, reference, review, and count rule unchanged for active notes.
- Make retention deterministic and testable with an explicit local day, not a hidden clock.
- Keep the write path recoverable: a failed trash, restore, delete, or cleanup must leave a clear
  on-disk state and a visible report.

**Non-Goals:**

- No SQLite, persistent index, background daemon, or timer thread.
- No migration or rewriting of legacy `trash/` files.
- No automatic restore at startup, and no restore-by-rename UI.
- No trash for template cards under `templates/`.
- No change to `afanes.yaml` or the vault schema version.

## Decisions

### 1. Use a separate read-only trash catalog, not `VaultSnapshot`

A new `TrashCatalog` reads `trash/` on demand and returns a `TrashSnapshot` of managed `TrashEntry`
values. `Vault.scan()` and `Vault.scan_fingerprint()` keep their current contract. A separate
`TrashCatalog.fingerprint()` stat walk lets the five-second refresh notice external trash changes
without parsing notes.

**Why:** it preserves the active catalog boundary and avoids parsing every trashed note on every
active scan. **Alternative rejected:** adding a `trashed` tuple to `VaultSnapshot` would make the
active scan own two different populations and would complicate the existing exclusion tests.

`TrashEntry` carries the absolute trash path, the UUID entry id, the validated birthplace, the
trashed day when usable, the display title, the search text, and the content hash. Managed entries
only; unmanaged files are not represented in the UI.

### 2. Read and write the two keys through an independent metadata editor

`TrashMetadata` is a value object with `birthplace: Path` and `trashed_on: datetime.date | None`.
A small frontmatter editor adds or removes only `trashed_from` and `trashed_on` in the raw YAML
mapping, preserving the body, newline style, key order, and every unknown key. It uses the same
fence split as `NoteDocument` but does not validate note type, status, or other note fields.

**Why:** a note with a valid YAML header but an invalid note field can still have a known birthplace
and must remain restorable. Reusing `NoteDocument.from_text()` would reject it and turn a recoverable
entry into an unmanaged one. The metadata editor also avoids adding the keys to the closed note model
and keeps malformed trash metadata from making an active note unreadable.

`trashed_from` is stored as a POSIX-style vault-relative path. `trashed_on` is stored as a YAML
calendar date. Reading accepts a date or an ISO `YYYY-MM-DD` string; anything else is unusable.
Unusable metadata on an otherwise valid birthplace triggers the “stamp today” rule. A future date is
kept and does not expire until the local date catches up.

### 3. Flat UUID storage under the existing trash folder

New entries are written as `trash/<uuid>.md`. The trash folder is resolved case-insensitively with
`Vault.existing_directory`, matching the existing layout rule. UUIDs are canonical lowercase UUIDs
with dashes; a taken path selects another UUID. Unmanaged files keep whatever names they already
have.

**Why:** a UUID cannot be mistaken for a real note name, which is exactly the failure of `Ada 2.md`
when a real note is named `Ada 2`. **Alternative rejected:** numbered names still collide with real
names, and name-plus-UUID still looks like a note identity.

The UUID is storage identity only. Every user-facing surface — rows, page chrome, search results,
processing previews, success toasts, and failure notices — identifies the entry by its title and
birthplace, never by the UUID.

### 4. Trash writes metadata in place, then renames into the UUID path

The write order is:

1. Validate the source against the snapshot content hash.
2. Build the note text with the two metadata keys added.
3. Atomically replace the source text.
4. Rename the source to `trash/<uuid>.md`.
5. On a rename failure, atomically restore the original text and report the failure.

**Why:** this keeps a single authoritative copy until the final rename. A crash between steps 3 and
4 leaves the note active with two inert, unknown keys; no data is lost and the next trash can replace
them. **Alternative rejected:** writing a new trash copy and then deleting the source creates a
duplicate if the process stops between the two writes.

### 5. Restore rebuilds the text, then publishes exclusively or replaces after confirmation

Restore reads the trashed file, removes the two metadata keys, and builds the restored text. A free
birthplace uses an exclusive write, so a race cannot overwrite anything. An occupied birthplace is
only written after the explicit overwrite confirmation and uses an atomic replace. A directory,
symlink, or other non-regular occupant is refused, not replaced. The trash source is removed only
after the destination write succeeds.

**Why:** the restored note has different bytes from the trashed one, so the old hard-link publish
path no longer applies. Exclusive publication preserves the no-overwrite rule for the safe case;
atomic replacement makes the confirmed overwrite a single filesystem operation.

If the destination write succeeds but removing the trash source fails, the restored note and the
trash copy both remain. The failure is reported and the copy can be deleted from Trash; rolling back
the destination would delete the restored note and would not bring the overwritten occupant back.

Undo reuses the same restore path without a confirmation. It therefore naturally refuses an occupied
birthplace, leaves the note in Trash, and reports the collision.

### 6. Retention is a catalog operation driven by an explicit local day

`TrashCatalog.expired(today)` filters managed entries with
`today - trashed_on >= datetime.timedelta(days=30)`. A cleanup pass first stamps missing or malformed
days with today, then deletes expired entries. It takes `today` as a plain value from the UI and
passes it to workers; core code does not read a clock. Deletion uses `Path.unlink` on a verified
regular file under the trash root, never recursion and never a symlink.

Cleanup runs when the vault opens and when Trash is selected. A failed write or delete becomes a
persistent banner owned by the session; the entry stays visible and a later successful pass clears
the banner. Unmanaged files are never candidates.

**Why:** a date-only rule is stable across time zones and file copies; mtime would be reset by backup
tools and could delete a note too early.

### 7. Put trash state in existing controllers, not a new `AppState` field

`VaultSession` gains a `TrashSnapshot | None` and a `trash_banner`. `BrowserState` derives the Trash
count and the Trash listing/search results from it. `PageDialogState` owns restore, delete, and empty
commands. `PageEditorState` gets a `trash_entry: TrashEntry | None` marker for the read-only page.
`WorkspaceController` runs the open-vault cleanup; `BrowserState.set_section(TRASH)` runs the cleanup
and reload before returning.

**Why:** `AppState` already has 10 annotated fields and is gated. A new `TrashState` field would fail
the architecture test. The session already owns scan-like data, and the dialog state already owns
page trash undo.

### 8. Search composes a separate Trash group

`BrowserState.listing()` continues to return active groups. Trash search is a separate
`TrashSnapshot.search(query)` result. The workspace view appends a **Trash** section after the active
groups; selecting a result opens the read-only trashed page. No `VaultNote` is created for a trashed
entry, and unmanaged files are not searchable.

### 9. Read-only trash page uses the existing draft machinery without editing

`PageNavigator.open_trash(entry)` commits the current active draft, loads the trashed file with
`Vault.read_page`, builds the normal or raw draft, and marks `PageEditorState.trash_entry`. The page
view hides Edit, Rename, and Move to Trash, shows Restore as the suggested action and Delete
Permanently in the secondary menu, and displays a trash metadata line instead of editable labels.
Autosave and save commands return without writing while `trash_entry` is set. The page path label
shows the birthplace, never the UUID.

A background trash refresh that discovers the open entry is gone closes the read-only page back to
the Trash browser with a notice.

### 10. Confirmation surfaces follow the existing feedback pattern

The overwrite warning and per-note delete are inline page panels, matching the existing rename and
type-change pattern. Empty Trash is a dialog because it acts on the browser, not on an open page.
Every destructive confirmation places Cancel first, makes the affirmative action non-default, and
uses the destructive token. Restore is the single suggested action on the trashed page.

## Risks / Trade-offs

- **Silent permanent deletion at 30 days** → The policy is fixed, documented, and only applies to
  managed entries. There is no undo by product decision; the Trash list and global search keep the
  remaining lifetime visible through daily use.
- **Permanent overwrite on restore** → The confirmation names the file, Cancel comes first, the
  affirmative action is not the default, and Undo never invokes the overwrite path.
- **Trashing rewrites YAML and can drop comments** → The metadata editor preserves unknown keys,
  key order, body, and newline style; YAML comments inside the frontmatter block follow the same
  existing limitation as every other frontmatter rewrite.
- **A crash between metadata write and rename** → The note remains active with inert keys; no copy is
  lost. The next trash replaces the keys.
- **Legacy trash files become invisible** → They remain on disk and are never deleted by the app.
  Documentation names the behavior; users can still move or delete them outside the application.
- **A read-only vault cannot clean up or stamp dates** → Browsing still works; the entry remains
  visible and a banner reports the failure.
- **Trash search reads trashed bodies** → The catalog is built once per refresh and cached in the
  session; search matching is in-memory and uses the same normalization as active search.
- **No new AppState field** → Trash state lives in the session and existing controllers, keeping the
  architecture gate satisfied.

## Migration Plan

No schema bump and no automatic migration. Existing `trash/` files without valid metadata become
unmanaged immediately: they are not listed, restored, expired, or deleted. New trash operations use
the UUID and metadata contract. Rollback is possible for files still present, but notes already
expired or overwritten cannot be recovered; the release notes must state that plainly. The change
does not add a dependency, a network call, or a persistent index.
