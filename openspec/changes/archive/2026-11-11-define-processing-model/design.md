# Design

## Context

See `proposal.md` - Why for motivation. The application currently ships only the capture loop: a capture is a `type: note` file under `inbox/`, the Inbox lists those files, and the preview is read-only. There is no processing operation, no status model, no category model, and no trash.

The current type model is also still flat: `NoteType` includes `person`, `project`, `note`, `action`, and `reference` as peers. `scheme_for_note_type` maps a single type to one scheme, and `Vault.scan` walks every Markdown file except dot directories. Deletion unlinks the file.

Constraints that shape the approach:

- Vault files are authoritative; scanning is read-only.
- `core/` and `models/` stay synchronous and free of Flet; the UI forwards intent.
- Writes are atomic, path-contained, and preserve unknown frontmatter.
- The vault must remain readable and editable without Afanes on macOS, Linux, and Windows.
- The product uses neutral, original vocabulary. The source workflow's name, proprietary wording, and diagrams stay out of the repository.

## Goals / Non-Goals

**Goals:**

- Define one explicit processing decision tree with observable outcomes.
- Separate storage folders from workflow state so status changes do not cause file moves.
- Make people and future categories reference notes rather than peer types.
- Add recoverable deletion through a vault-local trash folder.
- Keep the processing apply path atomic, retryable, and free of partial destinations.
- Record the phased master plan so later changes extend this model instead of redefining it.

**Non-Goals:**

- Link-driven page creation and the general note editor.
- A processed-note library, Timeline, People, Projects, or Next Actions views.
- The SQLite indexer and search layer.
- User-defined or dynamic categories.
- Project subfolders or automatic creation of project steps.
- Trash restore UI, trash purge, or automatic migration of legacy notes.
- Packaging and installer work.

## Decisions

### 1. Folders are storage; statuses and views are workflow

```
STORAGE (folders)          WORKFLOW (metadata / views)
-----------------          --------------------------
inbox/      captures       no status
trash/      discarded      excluded from catalog
reference/  non-actionable category: person / place / ...
projects/   outcomes       active / waiting / done / cancelled / archived / later
actions/    single steps   active / waiting / done / cancelled / archived / later
                           due_date  -> scheduled view
                           active    -> next actions view
                           later     -> later view
```

A folder answers "where does this file live?" A status or view answers "what is its workflow state?" Encoding states such as waiting, done, or later as folders would duplicate frontmatter, force file moves on every status change, and create drift when a user edits the frontmatter directly. Statuses stay in frontmatter; views are queries.

**Alternative considered:** one folder per workflow state (`waiting/`, `done/`, `later/`). Rejected because the folder and the status become two sources of truth, and status changes would touch file paths unnecessarily.

### 2. Default layout

```
vault/
  inbox/          capture queue
  trash/          recoverable discard
  reference/      non-actionable notes
    people/       category: person
    places/       future category
  projects/       outcome notes
  actions/        single action notes
```

- The layout is a **default destination policy** for notes the application creates. It is not a marker, a validation rule, or a required structure. Notes anywhere in the vault still resolve.
- Folders are created lazily on the first write that needs them. Opening or scanning a vault never creates a folder.
- Folder matching is case-insensitive. An existing `Inbox/`, `People/`, or `Trash/` is reused instead of creating a sibling with different case.
- `projects/` and `actions/` are flat. Project membership is the `project:` frontmatter reference, not directory nesting. This avoids project-folder renames and keeps identity independent of the path.
- `reference/people/` is the default for category `person`; uncategorized references live directly under `reference/`.
- `notes/` disappears. `type: note` is the capture type; processing resolves a capture into action, project, or reference. A generic non-actionable page is an uncategorized reference.

**Alternatives considered:**

- Five top-level type folders (`people/`, `references/`, `notes/`, `projects/`, `actions/`). Rejected because people and places are categories of reference, not peer content classes, and it enlarges the root.
- Project subfolders containing the project and its steps. Rejected because renaming a project would require a directory rename, standalone actions would still need a home, and the `project:` reference already carries membership.
- A single flat `notes/` folder for every processed note. Rejected because a person, project, and generic note can legitimately share a name in different schemes, which one directory cannot represent.

### 3. Note model: actionable versus reference

```
ACTIONABLE
  action    one step
  project   an outcome made of steps

NON-ACTIONABLE
  reference
    category: person   -> person pages
    category: place    -> future
    category: (none)   -> uncategorized knowledge

note        the unprocessed capture type
```

- `NoteType` becomes `note`, `action`, `project`, `reference`. `PERSON` is removed.
- `ReferenceCategory` starts with `person`. Future categories are added by explicit specification changes.
- `Status` becomes `active`, `waiting`, `done`, `cancelled`, `archived`, and `later`. `inbox` is removed because the folder is the queue.
- The initial status matrix is:

| Type | Allowed statuses |
| --- | --- |
| `note` | none |
| `action` | `active`, `waiting`, `done`, `cancelled`, `archived`, `later` |
| `project` | `active`, `waiting`, `done`, `cancelled`, `archived`, `later` |
| `reference` | none, `later`, `archived` |

The matrix is validated centrally when parsing a note. An absent status means an available reference or an unprocessed capture; an invalid status is a validation error, not a silent coercion.

**Alternatives considered:**

- Keep `type: person` and describe people as reference-like in the UI only. Rejected because the maintained model treats people as reference notes and future categories would otherwise multiply the type enum.
- Allow one note in both its category scheme and the `note` scheme. Rejected because it complicates uniqueness, resolution, and the mental model. One note belongs to one scheme.
- Dynamic user-defined categories now. Rejected as speculative; the category vocabulary is closed until a real second category exists.

### 4. Scheme mapping and catalog

| Note shape | Scheme | Default folder |
| --- | --- | --- |
| `type: note` | `note` | `inbox/` while captured |
| `type: action` | `note` | `actions/` |
| `type: reference`, no category | `note` | `reference/` |
| `type: reference`, `category: person` | `person` | `reference/people/` |
| `type: project` | `project` | `projects/` |

`scheme_for_note_type` becomes a function of the type and optional category. `NameCatalog` indexes each note under exactly one scheme. A note never appears in two namespaces.

**Alternative considered:** keep a type-only mapping and special-case `person` inside the catalog. Rejected because the category is part of identity semantics, and the special case would spread across parsing, creation, and resolution.

### 5. Processing decision tree

```
Capture in inbox/
        |
        v
  Actionable?
    |                         |
    no                        yes
    |                         |
    v                         v
Trash / Later / Reference   Single step?
                              |            |
                              yes          no
                              |            |
                              v            v
                            Action       Project
                              |
                              +-- active   (next action)
                              +-- waiting  (delegated)
                              +-- due_date (scheduled)
                              +-- done     (completed immediately)
```

Outcomes:

| Outcome | Type | Status | Destination |
| --- | --- | --- | --- |
| Trash | unchanged, moved to trash | none | `trash/` |
| Later | `reference` | `later` | `reference/` |
| Reference | `reference` | none | `reference/` |
| Action | `action` | `active` by default; `waiting` when delegated; `done` when completed immediately | `actions/` |
| Project | `project` | `active` by default | `projects/` |

- The user chooses the outcome. Processing never infers a project, person, due date, or category from the capture text.
- Actions may carry an optional due date, people, and one project reference. Unresolved `person:` and `project:` references are allowed and reported; they resolve later if the page appears.
- Projects carry status, optional due date, and people. Steps are separate action notes linked by `project:`. Processing does not create steps.
- References created by processing are uncategorized. Person and place categories are assigned by later page creation or editing, not by processing a capture.
- Later is represented by `status: later`, not by a `later/` folder. The future Later view filters on that status.

**Alternatives considered:**

- Binary action/reference only. Rejected because an actionable capture can be a multi-step outcome, which is a project.
- Turning a capture into a person or place page. Rejected because it changes the reference scheme and would break inbound `note:` references; those pages are created deliberately by link-driven creation or editing.
- Inferring classification from the text. Rejected by the product's capture-before-structure principle.

### 6. Processing plan and apply

Processing is a plan/apply operation on the vault service:

1. **Plan.** Read the capture, compute the target type, category, status, metadata, and destination. Validate the outcome, the status matrix, path containment, destination collisions, existing scheme duplicates, and inbound references that a scheme change would break. Capture the source content hash.
2. **Preview.** The UI shows the outcome, destination, metadata, and any unresolved or breaking references. Nothing is written.
3. **Apply.** Re-read the source, verify the hash, write the classified frontmatter atomically to the source, then rename the source to the destination. If the rename fails, the note remains in `inbox/` with the new metadata and the same plan can be retried.

Writing before moving is deliberate: a crash after the write leaves a processed-looking note in the inbox, which is recoverable; moving before writing would hide an unprocessed note from the queue.

**Failure handling:**

- Source changed after planning: abort and ask the user to re-plan.
- Destination exists or the target name already exists in the scheme: abort. Never overwrite and never add a numeric suffix, because the name is identity and references may depend on it.
- Write failure: no destination file, note remains in the inbox.
- Move failure: retryable, no duplicate note.
- Scheme change with inbound references: report the affected count and require confirmation; do not retarget references.
- Trash: report inbound references, move the file without rewriting it, and never modify referring notes.

### 7. Trash

`trash/` is a visible, vault-local folder. It is excluded from scans, name uniqueness, and reference resolution by matching the first path component case-insensitively. Trashed notes remain ordinary Markdown files on disk, so a user can restore one by moving it back. The application does not purge trash automatically and does not implement a restore UI in this change.

Trash naming uses the existing unique-name policy inside `trash/`; the trashed filename is not identity because the folder is outside the catalog. Moving a note to trash preserves its bytes.

**Alternatives considered:**

- Platform trash. Rejected because it is not portable and not part of the vault.
- A hidden `.trash/` folder. Rejected because recoverability should be visible to the user.
- Permanent unlink. Rejected because it is not recoverable and conflicts with the file-safety policy.

### 8. UI boundaries

- The Processing Wizard is presentational. It collects the decision, metadata, and confirmation, then forwards plan/apply commands to the shared application state.
- Blocking scan, plan, write, and move work runs off the UI thread.
- The wizard is opened from a capture in the Inbox. On success the note leaves the Inbox and the view shows the destination. A processed-note library is a later phase; the first slice can verify the result in the vault and through the success banner.
- User-facing copy is centralized and uses the neutral vocabulary: Inbox, Action, Project, Reference, Later, Trash, People.
- No branded terminology, proprietary text, or copied diagram appears in code, tests, or UI copy.

### 9. Master plan phases

This change is the first phase of the recorded plan:

1. **Processing model and layout (this change).** Types, categories, statuses, default folders, processing plan/apply, trash, and the Processing Wizard.
2. **Pages and editing.** Clicking an unresolved internal link opens a blank page; an empty page is discarded, a page with content is kept. Add the generic note editor and person/place page creation.
3. **Views and index.** A processed-note library, Next Actions, Projects, People, Timeline, and the SQLite/FTS5 index that backs them.
4. **Packaging and verification.** Bundle the Flet client, build desktop packages, and run the manual macOS/Linux/Windows pass.

The phases are sequencing guidance. Each later phase still needs its own OpenSpec change and its own specs.

## Risks / Trade-offs

- **Breaking type change.** Removing `type: person` makes legacy notes unreadable until converted. The application is source-run only, so no automatic migration is included. Mitigation: report the legacy notes in the scan, document the conversion, and back up the vault before applying.
- **Two schemes for related content.** A person page is `person:` and is not also `note:`. Users may expect both. Mitigation: the UI always uses the category scheme, and the specs state the one-scheme rule.
- **Flat actions and projects at scale.** A large vault produces many files in `actions/` and `projects/`. Mitigation: the future indexer and views provide navigation; the folder stays a human affordance, not the query engine.
- **Trash exclusion changes resolution.** A trashed note becomes unresolved immediately. Mitigation: the preview reports inbound references; restoring the file resolves them again.
- **Write-then-move window.** A failed move leaves processed metadata in an inbox note. Mitigation: the plan is retryable and the note is still visible; no destination duplicate exists.
- **Closed category vocabulary.** Users may want custom categories. Mitigation: categories are extended by a deliberate change, keeping the scheme and folder mapping coherent.
- **Status matrix drift.** The matrix is enforced in one parser path. Mitigation: model tests cover every type/status pair, including invalid combinations.

## Migration Plan

1. Back up the vault.
2. Convert any existing `type: person` note to `type: reference` with `category: person`. The filename stem remains the name and identity.
3. Remove any `status: inbox` value. Captures have no status; the folder is the queue.
4. Existing files may remain in `people/` or any other directory. The directory is not identity; only the category controls the scheme. New pages use `reference/people/`.
5. Rollback: revert the application and specs. Files written by this change use `type: reference` and a `category` key, which older code preserves as an unknown key while still treating the note as a reference. The removal of `type: person` is one-way for notes already converted.

No automatic migration command is included in this change. A future doctor or CLI command can automate the conversion.

## Open Questions

These do not change this change's specs or task breakdown:

- Whether the future Later view should include deferred actions and projects as well as references.
- Whether trash gets a restore UI, a purge action, or both.
- Whether categories eventually become user-defined.
- How the future processed-note library should group actions and projects by default.

## Implementation Review

Reviewed on 2026-11-11:

- The diff is scoped to the processing model, vault layout, trash, category migration, and the Processing Wizard. `pyproject.toml` is unchanged; no dependency or network client was added.
- `type: person` and `status: inbox` remain only as rejection tests and migration notes. The scanner reports them as unreadable instead of coercing them.
- Processing writes the classified source note with `afanes.core.atomic.write_text_atomic`, then renames it. A failed move leaves the note in `inbox/` for retry. Trash moves bytes without rewriting the note.
- Unknown frontmatter keys, the Markdown body, newline style, and referring notes are preserved. Tests cover body, unknown-key, and blank-line preservation.
- Default folder resolution and trash exclusion are case-insensitive; destinations are contained by `Vault.contained`. Existing notes anywhere in the vault still resolve.
- The UI forwards intent through `AppState`; views do no parsing, SQL, or direct file I/O. Blocking work runs through `asyncio.to_thread`.
- The source-run smoke test started the Flet app without a traceback; interactive click-through was not automated.

## Verification

- Source-run smoke test on Linux with `DISPLAY=:0`: `timeout 8s hatch run python -m afanes` started the Flet app and loaded the cached desktop client with no traceback. The timeout stopped the process after startup.
- Interactive click-through is not automated in this environment. The Inbox-to-wizard and cancel-to-Inbox routing is covered by `tests/ui/test_app.py`; the wizard form, preview, and success state are covered by `tests/ui/test_processing_view.py`.

## Test Strategy

- **Models:** category and status parsing, per-type status validity, `NoteType` membership, enum serialization.
- **References:** scheme mapping with and without categories, one-scheme membership, ambiguous duplicates, category changes, legacy `type: person` rejection.
- **Layout:** case-insensitive folder reuse, lazy creation, default destinations, containment, trash exclusion, no writes on scan.
- **Processing:** plan validation, collisions, scheme-change warnings, trash inbound counts, source hash guard, atomic write, retry after move failure, body and unknown-key preservation.
- **Integration:** capture -> process each outcome -> scan -> destination and resolution checks; trash -> unresolved reference -> restore -> resolved.
- **UI:** `AppState` plan/apply commands, wizard construction and handler behavior, error and success banners, no blocking I/O on the UI thread.
- **Architecture:** `models` imports only the standard library, `core` has no Flet, `ui` has no parsing or SQL, new modules stay in the acyclic graph.
- **Cross-platform:** case variants, reserved names, path separators, symlink escapes, CRLF preservation.

## Platform Impact

- Folder matching is case-insensitive on every platform, so a vault created on Linux and opened on macOS does not gain duplicate default folders.
- The vault-local trash is ordinary filesystem content and works on all three platforms.
- The atomic rename assumes the source and destination are on the same filesystem, which is true inside one vault. A vault that contains a mount point across filesystems would surface an explicit move failure rather than a partial write.
- No platform-specific APIs, no network access, and no new dependencies.

## Privacy and Vocabulary

- All processing is local. No note content leaves the device.
- User-facing copy and specs use the project's neutral vocabulary.
- The source workflow's name, proprietary text, and diagrams are not copied into the repository. The decision tree above is an original description of behavior.
