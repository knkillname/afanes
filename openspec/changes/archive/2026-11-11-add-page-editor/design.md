# Design

## Context

The application shell currently routes between the welcome state, the Inbox, and the Processing Wizard. The Inbox owns a list and a read-only `ft.Markdown` preview whose link handler deliberately swallows taps. `core/vault.py` already owns scanning, containment, atomic writes, capture, processing, rename, and trash. `core/frontmatter.py` parses and serializes notes, and `core/links.py` resolves references against a `NameCatalog`.

`VaultNote` carries a content hash but not the raw text, and `Vault` exposes no edit read or save operation. `NoteDocument` keeps the raw frontmatter mapping so unknown keys can be preserved, but it does not validate `due_date`; YAML loads an ISO date as a `datetime.date`, not a string.

See `proposal.md` for motivation and `specs/note-editing/spec.md` for the behavior contract. The constraints are the project-wide ones: offline only, files are the source of truth, `core/` has no Flet imports, `ui/` does no parsing or file I/O, atomic writes, path containment, cross-platform filenames, and neutral vocabulary.

## Goals / Non-Goals

**Goals:**

- Add a page session that reads, edits, creates, and saves notes without weakening the vault safety rules.
- Route internal links from the rendered page while keeping external and unsafe destinations inert.
- Keep all page state in the existing single `AppState` controller and all domain rules in `core/`.
- Preserve unknown frontmatter keys, newline style, and existing file bytes when a field is untouched.
- Make the save loop testable without Flet, including conflict detection and exact-identity creation.

**Non-Goals:**

- No search view, index, file watcher, or background network activity.
- No WYSIWYG editing; the body editor is raw Markdown.
- No separate title property; the first level-1 heading remains the display title.
- No new note type, category, or reference scheme.
- No automatic merge of concurrent external edits.
- No global "New page" action; page creation starts from an unresolved link.

## Decisions

### A page draft is a pure core value object

Add `core/editing.py` with a frozen, slotted `PageDraft` value object. It owns one editing session's data and the local invariants that keep it coherent:

- optional path (absent until a new draft is first written)
- identity and originating reference, when the draft came from a link
- mode: normal or raw
- body or raw text
- label values: type, category, status, due date text, person identities, project identity
- the original raw frontmatter mapping
- newline style and baseline text/hash
- dirty and conflict flags

It exposes pure transformations such as loading from a `PageContent`, changing a label, setting the body, marking saved, and upgrading from raw to normal after a successful parse. It performs no I/O. `Vault` remains the service that reads and writes; `AppState` orchestrates the two.

This keeps the editor rules out of `ui/` while avoiding a second service object that would duplicate `Vault`'s resource ownership. A stateless transformation stays a module function; the draft is cohesive state, so it is a value object.

### The vault gains a page read and a guarded write

Add to `core/vault.py`:

- `PageContent`: path, relative path, raw text, content hash, parsed document, and a parse failure message. `Vault.read_page` returns it and never writes.
- `Vault.write_page(note_path, text, expected_hash)`: reads the current file, compares its SHA-256 digest with `expected_hash`, raises a new `ContentChangedError` when they differ, and otherwise writes the text atomically. It returns the new hash. This one primitive serves normal saves and raw rescue saves.
- `Vault.create_page(reference_name, note_type, category, body)`: builds the same canonical document as `create`, but writes the exact sanitized filename and raises `NameCollisionError` instead of adding a numeric suffix. It checks the scheme catalog and the target directory, including case-insensitive filename collisions.
- `Vault.plan_reference_repair` and `Vault.apply_reference_repair`: find every note whose references equal a given `NoteReference` and rewrite those destinations. This is equality matching, not resolution matching, so it works while the unsafe reference is still unresolved. The plan captures content hashes; the apply step skips changed files and reports failures, mirroring rename.
- `VaultSnapshot.link_target(reference)`: a pure router over the catalog and the failure list, returning resolved, ambiguous, broken (with matching failure paths), or missing. Broken matching compares normalized stems and never reads a file.
- `VaultSnapshot.referrers(note_path)`: exposes the inbound reference sites already computed privately for rename and trash, so a scheme-change preview can reuse them.

Add `ContentChangedError` to `core/errors.py` under `VaultError`.

### Link routing is a core decision

```
tap a destination
  |
  +-- classify_destination
        +-- internal -> snapshot.link_target
        |     +-- resolved  -> open the target read mode
        |     +-- ambiguous -> candidate picker, no default
        |     +-- broken    -> raw rescue mode for the failed file
        |     +-- missing   -> new page draft for the reference
        +-- external / attachment / anchor / unsafe -> inert
```

The view passes the destination string to `AppState`, which classifies and routes. It never parses Markdown or touches the filesystem directly. The catalog and failures come from the retained scan snapshot, so routing is in-memory. The failure list is made clickable in the Inbox so broken notes are reachable without a link.

### New pages are drafts without a path

A draft from a missing reference starts with `# <reference name>` plus a blank line, and type/category derived from the scheme. The template is the dirty baseline: an untouched draft is discarded without a write. The first body or label change marks it dirty; the first successful save calls `create_page`, adopts the returned path, and becomes an ordinary page.

The identity is `safe_filename(reference.name)`. If the sanitized identity already belongs to a page in the same scheme, the router opens that page instead. If the exact filename is occupied by anything else, creation stops before writing and the draft remains open so the user can rename or cancel. No numeric suffix is added by the page flow.

On the first write, if `safe_filename(reference.name) != reference.name`, the state plans a reference repair against the snapshot and shows Rewrite / Keep / Cancel. Rewrite calls `apply_reference_repair`; Keep leaves the references untouched; Cancel removes the file just created for the draft and keeps the draft in memory. The repair preview lists note paths and reference counts, and custom labels are preserved because only destinations are rewritten.

### The save loop uses one guarded write

```
body or label change -> dirty
  |
  +-- 30 s autosave task, Done, Back, or navigation
        |
        +-- validate labels (date, status, category)
        +-- build the next document from the draft
        +-- new draft?  create_page
        +-- existing?   write_page(path, text, baseline_hash)
              |
              +-- hash differs -> conflict state, stop autosave, banner
              +-- success      -> baseline = written text and hash, dirty = false
```

The autosave runs only while edit mode is active and the draft is dirty. `AppState` owns one tracked autosave task, started with the application and cancelled on reset; it awaits `asyncio.sleep` and calls `autosave()`. Done, Back, and navigation commit synchronously before changing the page. No `time.sleep` is used, and no per-view task can leak when the pane is rebuilt.

Conflict resolution is explicit:

- Reload re-reads the file into the draft and returns to read mode.
- Overwrite writes the draft once without the hash guard after the user confirms, then resets the baseline.
- If the file was moved or deleted, Recreate writes the draft at the original contained path when it is free; Discard drops the draft.
- Leaving a conflicted draft asks for confirmation and writes nothing.

The hash check and the atomic replace are separate syscalls, so a narrow race remains. This is accepted for a local single-writer application and documented in the write method; the check still closes the ordinary external-edit window.

### Labels are owned keys in the preserved raw mapping

The draft loads the raw mapping from `NoteDocument.raw`. On save it changes only `type`, `category`, `status`, `due_date`, `people`, and `project`; every other key and the body are preserved. Cleared values remove their keys rather than writing null. The existing `NoteDocument.with_metadata` revalidates the result.

- Category is written only for `reference`; it is removed for every other type.
- Status is constrained by `allowed_statuses(type)`; a type change that invalidates the status clears it in the same confirmed change.
- Due date accepts an absent value, a `datetime.date` loaded by YAML, or an ISO `YYYY-MM-DD` string. It is normalized to a date and written as an ISO string. Any other value blocks the save with an inline error.
- People and project are stored as identities and rendered as `person:`/`project:` references on save. Suggestions come from `AppState.assignment_candidates`, the same snapshot-backed list used by processing.

A scheme change is computed with `scheme_for_note(old_type, old_category)` and `scheme_for_note(new_type, new_category)`. When they differ, `AppState` refreshes the snapshot, calls `referrers`, and shows the affected sites before mutating the draft. Cancel restores the previous dropdown values. Same-scheme changes apply immediately.

### Rename and trash reuse the existing plan/apply flow

The page action opens the existing rename or trash preview. The state retains the preview object and applies it only after confirmation.

Rename gains one rule: when the note's first level-1 heading text equals the old identity after trimming, the heading is updated to the new identity. `plan_rename` records whether that update is needed, and `apply_rename` applies it with the same content-hash guard used for reference rewrites. If the file changed after planning, the heading update is skipped and reported rather than forced. The state then updates the draft path, identity, and any history entries that pointed at the old path, and rescans.

Trash uses `plan_trash` and `trash`. On success the current page is removed from history, the state shows the previous page or the empty pane, and the snapshot is refreshed.

### One bounded history

`AppState` keeps a tuple of page paths behind the current page and the current draft. Opening a page or following a link pushes the current page path. A new draft contributes its path only after a commit; an untouched draft contributes nothing. Back commits or discards the current draft, pops the stack, and shows the previous page in read mode. An empty stack clears the pane. The stack is capped at 50 entries. Renaming rewrites matching entries; trashing removes them; a path that no longer exists is skipped with a message.

### The UI is a page view beside the existing list

Add `ui/views/page.py` for the right pane. `ui/views/inbox.py` keeps the list, composer, and banners and delegates the pane to the page view. The page view has:

- a header with Back, title in read mode, path, Edit/Done, and a menu with Rename and Trash
- `ft.Markdown` in read mode with `on_tap_link`
- a raw body `ft.TextField`, the label form, and save status in edit mode
- a raw rescue text field with a warning and no labels
- banners for conflict, validation, write failure, and ambiguity

`AppState` gains the page draft, history, and commands (`open_page`, `edit_page`, `done_editing`, `autosave`, `back`, `follow_link`, `reload_page`, `overwrite_page`, `discard_draft`, `begin_rename`, `apply_rename`, `begin_trash`, `apply_trash`, `plan_type_change`, `apply_type_change`). Views only call these commands and render the exposed fields. New copy goes to `ui/strings.py`; sizes and colors go to `ui/theme.py`. Suggestions reuse the processing view's list pattern rather than introducing a second interaction model.

### Failure reporting stays visible and becomes actionable

The Inbox banner keeps the count and paths of unreadable notes, and each path becomes tappable. Tapping one opens the raw rescue mode. A link whose normalized name matches exactly one failure opens the same mode; several matches show a picker. This closes the duplicate-page hole: the router never treats an existing unreadable file as a missing page.

## Test Strategy

- `tests/core/test_editing.py`: draft loading, dirty baseline, label transformations, due-date normalization, raw upgrade, and new-page identity rules.
- `tests/core/test_vault.py`: `read_page`, exact `create_page` collisions, `write_page` conflict detection, and atomic-write behavior using `tmp_path`.
- `tests/core/test_links.py` or `tests/core/test_vault.py`: `link_target` outcomes and failure matching.
- `tests/core/test_vault.py`: reference-repair planning and apply, including skipped files.
- `tests/ui/test_state.py`: open/back history, autosave command, conflict states, type-change preview, rename/trash history updates. Patch module collaborators; no rendered window.
- `tests/ui/test_page_view.py`: read/edit/raw control states, link routing calls, and validation errors, with the `AppState` singleton reset.
- Architecture tests continue to reject Flet imports in `core/` and file I/O in `ui/`.
- Every new public type and function gets strict NumPy-style docstrings; the full gates are `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, and the vocabulary check.

## Risks / Trade-offs

- **Hash check race** → accepted for a local single-writer app; the check immediately precedes the atomic write and catches ordinary external edits.
- **Autosave creates a page the user did not finish** → the first-content rule prevents empty pages, and trash remains recoverable; no silent discard of typed content.
- **A stale snapshot can miss references that would be stranded by a type change** → the state refreshes the snapshot before computing the scheme-change preview.
- **Full vault scans on navigation and rename/trash** → acceptable before the index exists; routing and previews use the retained snapshot, and scans run off the UI thread.
- **Raw rescue can persist invalid files** → intentional; the warning is explicit and the editor never auto-repairs.
- **One invalid label blocks all autosave** → the draft is retained, the field shows the reason, and the user can clear or fix it; nothing invalid is written.
- **Async autosave task lifecycle** → the view starts, tracks, and cancels the task on Done, Back, navigation, and dispose; tests call the state command directly with controlled timing.
- **Case-insensitive filesystems** → exact creation checks case-folded siblings, and all paths remain contained and NFC-normalized by the existing name policy.

## Migration Plan

No vault migration is required. The editor writes the same frontmatter contract and Markdown format, creates files only under the existing default folders, and leaves notes it does not edit untouched. Rolling back to the previous release leaves every page readable; the only new durable behavior is the rename heading update, which follows the existing display-title model. There is no cache schema to invalidate.
