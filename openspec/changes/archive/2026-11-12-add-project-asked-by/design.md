# Design

## Context

See `proposal.md` for motivation. The current note model recognizes four frontmatter keys:
`type`, `category`, `status`, and `due_date`. `core/frontmatter.NoteDocument` parses and validates
them; `core/editing.PageLabels` carries the editable values for the page draft; `NormalDraft.to_text`
writes the labels back into the raw frontmatter; and `ui/views/page.py` renders a project meta row
with status and due date. `ui/state/dialogs.PageDialogState` owns the label commands.

The vault is offline and file-first. The page editor is the only path that writes these labels, and
every write already preserves unknown keys, the body, and the newline style. The project snapshot and
search are derived from the body and the existing four keys.

## Goals / Non-Goals

**Goals:**

- Store one optional requester name on a project in plain frontmatter.
- Show the requester in the fixed project meta row.
- Set and clear it from the existing page editor.
- Keep the change inside the note model and page editing; leave the snapshot, search, rows, review,
  and processing untouched.
- Preserve strict parsing: an invalid or misplaced key is a validation error, not silent data.

**Non-Goals:**

- Resolving the name to a page, making it clickable, or searching it.
- Multiple requesters, project-level roles, or a general people map.
- A read-mode person picker or a project-row display.
- Automatic updates when the named person is renamed or trashed.
- Capture-time entry in the Processing Wizard.

## Decisions

### 1. `asked_by` is a single plain string, not a reference

The value is one name, written as a YAML string. It is not a `NoteReference`, does not use a scheme,
and does not enter the name catalog. This fits the job: the user needs to recall who asked, not
navigate to them. It also avoids a second reference storage path outside the Markdown body. Step
owners are the precedent for names kept in metadata; they resolve only when the UI offers
suggestions, and they can become stale after a rename.

Alternatives considered:

- A body link (`Asked by [Priya](<note:Priya>)`) reuses the reference engine but is prose, not a fixed
  header.
- A `note:Priya Nair` destination in frontmatter preserves the scheme but adds resolution, display,
  and unresolved-handling work for no recall benefit.
- A list of names or a roles map turns the project into a task record and is explicitly deferred.

### 2. Validate in `NoteDocument`, carry the text in `PageLabels`

`NoteDocument.from_text` and `with_metadata` validate `asked_by`: a single non-empty string, valid
only when the declared type is `project`. `PageLabels` adds an `asked_by_text` field populated from
the parsed document. `NormalDraft.to_text` trims a non-blank value and writes it; a blank value or a
non-project type pops the key. This mirrors how `due_date` and `category` travel through the same
objects and keeps the parser authoritative for hand-edited files.

Alternatives considered:

- Validate only in the editor: rejected because a hand-edited file must parse consistently with the
  application's other keys.
- Store the value only on `VaultNote`: rejected because the header reads the open draft, and adding it
  to the snapshot would invite row and search behavior that is out of scope.

### 3. Show the requester in the existing project meta row

The meta row currently holds status and due date. `Asked by <name>` follows them when the key is
present. When it is absent, the row omits the label. The value is plain text, so no link handling or
navigation state is added.

Alternative considered: always show `Asked by —` with a person action that opens a picker. That is
consistent with the due-date action but requires a new read-mode command, picker state, and
suggestion list. It is deferred until the plain display proves insufficient.

### 4. Edit through the existing page form

A single-line `Asked by` field appears in the edit form only for projects. It follows the existing
label pattern: the field calls one `PageDialogState` command, the draft becomes dirty, and the normal
autosave or Done path writes it. Clearing the field removes the key. The command count stays within
the architecture gate's limit for a domain controller.

Alternative considered: a read-mode inline picker. Deferred for the same reason as the meta-row
action.

### 5. A type change clears the key

`PageLabels.with_type` clears `asked_by_text` when the new type is not `project`, and
`NormalDraft.to_text` removes the key for any non-project. This matches the existing treatment of
`category` and `due_date` and prevents a type change from producing a note that the parser would
reject.

### 6. Keep the snapshot and search unchanged

`VaultNote` does not gain an `asked_by` field. Project rows, browser search, review, and the
Processing Wizard therefore behave exactly as before. The page header reads `PageLabels`, which is
built from the open document. The trade-off is explicit: the requester is visible only on the project
page, not in lists or search.

### 7. Accept stale names as a known limitation

Because the value is plain text, renaming the named note does not update the project and the rename
preview does not list it. This is consistent with step owners. The editor accepts free text, so the
user can correct a stale value. A future change can add suggestions or resolution if the need appears.

## Risks / Trade-offs

- **The frontmatter contract grows from four to five keys** -> update the note-model spec, the
  frontmatter reference, the vault format page, and the tests that assert the key set.
- **A stale requester after a rename** -> documented; the field remains editable and the value is
  never silently rewritten.
- **A blank or misplaced key makes the note unreadable** -> consistent with `category` and
  `due_date`; the existing raw rescue mode allows the user to repair it.
- **An existing unknown `asked_by` value becomes validated** -> additive for valid strings; an
  invalid list or blank value becomes a parse failure. The release notes should mention the new key.
- **The edit form gains a field** -> keep the form layout wrap-friendly and verify on the three
  supported platforms through the existing UI test patterns.

## Migration Plan

No data migration is required. Notes without the key are unchanged. Notes that already carry a valid
string `asked_by` become recognized and display the requester; a note with an invalid value opens in
raw rescue mode. Rolling back removes the parser and UI support; the key remains an unknown,
preserved value, so no user data is lost.

## Open Questions

None that change the specs, the approach, or the task breakdown.
