# Tasks

## 1. Trash metadata and read-only catalog

- [x] 1.1 Add the `TrashMetadata` value object and a frontmatter editor that adds and removes only
  `trashed_from` and `trashed_on`, preserving body, newline style, key order, and unknown keys.
  Verify with new tests in `tests/core/vault/test_trash.py` covering round-trip, unknown keys, CRLF,
  missing keys, malformed dates, and absolute or escaping birthplaces.
- [x] 1.2 Add `TrashEntry`, `TrashSnapshot`, and `TrashCatalog` with managed-entry discovery, title
  fallback to the birthplace stem, search text, sorting, managed-entry count, and the trash
  fingerprint. Verify with tests covering hidden/unmanaged files, unsafe birthplaces, symlinks, a
  missing trash folder, deterministic ordering, and a stable fingerprint.
- [x] 1.3 Update `docs/reference/vault-format.md` with the two metadata keys, the UUID storage
  convention, and the unmanaged-file rule. Verify with `hatch run docs:build`.

## 2. Trash write path

- [x] 2.1 Extend `TrashService.plan_trash` and `VaultNaming.plan_trash` to allocate a pure UUID
  destination and return it in the preview. Verify with tests that two plans never choose the same
  path and an existing UUID file is not overwritten.
- [x] 2.2 Extend `TrashService.trash` to validate the source content hash, write the metadata into
  the note, rename it to the UUID path, and restore the original text when the rename fails. Verify
  with tests for body and unknown-key preservation, a changed source, an unwritable note, a taken
  UUID, and a rename failure.
- [x] 2.3 Update `TrashPreview`, the undo record, and the page trash command to carry the new
  metadata-aware preview. Verify with existing trash and undo tests plus new assertions that Undo
  removes the metadata after a successful restore.

## 3. Restore, permanent deletion, and retention

- [x] 3.1 Implement restore to the recorded birthplace with exclusive publication, parent creation,
  metadata removal, and a free-path fast path. Verify with tests for a free birthplace, missing
  parents, body/newline preservation, metadata removal, and a restored note leaving Trash.
- [x] 3.2 Add the occupied-birthplace gate that refuses to overwrite unless explicitly allowed, uses
  an atomic replace when allowed, and refuses directories and symlinks. Verify with tests for refusal,
  confirmed replacement, cancel/no-write, directory refusal, and symlink refusal.
- [x] 3.3 Add per-note permanent deletion and Empty Trash in the trash service, deleting only managed
  regular files and leaving unmanaged files untouched. Verify with tests for one entry, all managed
  entries, unmanaged files, and a failed deletion report.
- [x] 3.4 Add the retention pass: stamp a missing or malformed trashed day with the supplied local
  day, delete entries at 30 or more days, keep entries at 29 days, and report failed writes or
  deletes. Verify with boundary, read-only, and partial-failure tests.
- [x] 3.5 Make the Undo path use the same restore rules without overwrite permission, leaving the
  note in Trash and reporting a collision. Verify with tests for a free birth and an occupied
  birthplace, including “writes nothing on collision.”

## 4. Trash search and session state

- [x] 4.1 Add managed-entry search over title, birthplace, and body text with the same normalization
  as active search, plus a separate Trash result collection. Verify with tests for title, birthplace,
  body, case/whitespace normalization, and unmanaged-file exclusion.
- [x] 4.2 Add the trash snapshot, trash banner, and trash refresh to `VaultSession`; add the Trash
  count and listing accessors to `BrowserState`. Verify with `tests/ui/test_state.py` for load,
  refresh, count, empty state, and banner ownership.
- [x] 4.3 Run cleanup on vault open and on selecting Trash, and refresh the trash catalog when the
  trash fingerprint changes in the background. Verify with state tests for open-time purge,
  selection-time purge, background external change, and a failed maintenance pass.
- [x] 4.4 Keep `AppState` at 10 annotated fields and keep the trash state inside the session and
  existing controllers. Verify with `hatch test tests/core/test_architecture.py`.

## 5. Trash browser

- [x] 5.1 Add `WorkspaceSection.TRASH`, its label, icon, navigation entry, and managed-entry count,
  mapping it to a custom browser area rather than a `BrowserSection`. Verify with
  `tests/ui/test_workspace_view.py` for the entry, count, selection, and empty state.
- [x] 5.2 Add Trash rows that show the title and “From `<birthplace>`,” with selection opening the
  trashed page and a refresh preserving the selection rules. Verify with workspace view tests for
  row content, ordering, and selection.
- [x] 5.3 Add the Trash group to global search results and keep Trash matches out of active groups.
  Verify with workspace view and core search tests for mixed results, read-only opening, and
  unmanaged-file exclusion.
- [x] 5.4 Add the Empty Trash action to the Trash browser header with a confirmation dialog that
  names the managed count and places Cancel first. Verify with workspace view and feedback tests for
  cancel, confirm, and a hidden unmanaged file remaining.
- [x] 5.5 Update `docs/guide/workspace.md` for the Trash destination, its rows, search group, and
  Empty Trash action. Verify with `hatch run docs:build`.

## 6. Read-only trashed page and actions

- [x] 6.1 Add the trash-page marker to `PageEditorState`, load a trashed entry without adding it to
  the active catalog, block editing/rename/autosave, show the birthplace instead of the UUID in the
  path label, and close the page when a background refresh finds the entry gone. Verify with page
  state and page view tests.
- [x] 6.2 Render the trashed page read-only with the “Trashed from … on …” line, Restore as the
  suggested action, and Delete Permanently in the secondary menu; hide Edit, Rename, and Move to
  Trash. Verify with `tests/ui/test_page_view.py` and conformance tests.
- [x] 6.3 Add the inline overwrite warning for an occupied birthplace and the inline per-note delete
  confirmation. Verify with page view tests for Cancel-first order, no write on cancel, confirmed
  overwrite, and confirmed deletion.
- [x] 6.4 Make a trashed search result and a Trash row share the same read-only open path, including
  Back returning to the Trash browser. Verify with workspace and navigation tests.
- [x] 6.5 Update `docs/guide/pages-and-editing.md`, `docs/reference/names-and-links.md`, and
  `docs/reference/troubleshooting.md` for restoration, overwrite, retention, and unmanaged trash
  files. Verify with `hatch run docs:build`.

## 7. Copy, interface standard, and conformance

- [x] 7.1 Add every new copy constant to `ui/strings.py`, classify each in the header-case or
  sentence-case sets, and use typographic apostrophes and ellipses. Verify with
  `hatch test tests/ui/test_copy.py`.
- [x] 7.2 Update `docs/develop/interface-standard.md` for the Trash destination, the restore-overwrite
  confirmation, and scheduled retention as the non-user-invoked exception. Verify with
  `hatch run docs:build`.
- [x] 7.3 Update the conformance baseline only if the new views require it, and keep at most one
  suggested or destructive control per rendered surface. Verify with
  `hatch test tests/ui/test_conformance.py`.
- [x] 7.4 Update the README feature or workflow copy if the Trash destination changes the user-facing
  feature list. Verify with `hatch run docs:build` and a README review.
- [x] 7.5 Update `AGENTS.md` section 4.5 and any affected interface rules to name the two new
  exceptions: scheduled trash retention may delete after opening, and a confirmed restore may
  overwrite. Verify by re-reading the changed sections and running the `AGENTS.md` section 6.1
  vocabulary grep commands.
- [x] 7.6 Audit every user-facing surface that can name a trash entry — navigation, rows, page
  chrome, search results, processing preview, toasts, and failure notices — and replace the UUID
  with the title or birthplace. Verify with view and processing tests plus a search of the UI copy
  for the UUID path pattern.

## 8. Integration and gates

- [x] 8.1 Run `hatch check` and fix lint, formatting, and strict type failures.
- [x] 8.2 Run `hatch test --cover` and keep coverage at or above the project threshold.
- [x] 8.3 Run `openspec validate --all --strict` and `openspec doctor`, then run the
  `AGENTS.md` section 6.1 vocabulary grep commands and confirm they produce no output.
- [x] 8.4 Smoke-test the desktop application with a temporary vault: trash, browse, search, restore,
  overwrite, delete one entry, empty Trash, and reopen the vault after retention. Verify the Trash
  count and page state after each step.
- [x] 8.5 Smoke-test a read-only vault and confirm browsing and Trash listing still work while the
  maintenance failure banner is shown.

## Workflow follow-up

- Archive the change after review and all gates pass.
- Run the post-archive release workflow from `AGENTS.md` section 5.3, including the changelog,
  README/docs status, and version decision.
