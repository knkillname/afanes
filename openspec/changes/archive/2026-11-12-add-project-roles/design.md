# Design

## Context

See `proposal.md` for motivation. The relevant current state:

- `refactor-single-owner` is archived, so `PageLabels.apply_to` is the single writer for editable
  frontmatter labels. Any new label belongs in `PageLabels`, not in a view or a second writer.
- `NoteDocument` parses `asked_by` as a project-only plain string. `VaultNote` stores `asked_by`
  and body references separately. Step owners live only in `ProjectStep.metadata`.
- `Connections` already resolves `asked_by` and step owners for the Requested projects and Owned
  steps sections, but rename and trash rewrite only body references. Search sees body text and step
  text, with step metadata comments removed.
- `StepDocument.with_owners` can replace one step's owner list while preserving every other metadata
  key, so a rename rewrite does not need to hand-build the YAML comment.
- `AppState` is at its 10-field budget and both `PageEditorState` and `PageDialogState` are at their
  25-public-name budgets. `PageEditorState.page_steps` is unused and can be removed to free one slot.
  `PageNavigator` has room for more commands. The UI must not add a new `AppState` field.
- There is no persistent index. Every derived view is rebuilt from the current `VaultSnapshot`.

## Goals / Non-Goals

**Goals:**

- Add one optional project owner and display it before the requester.
- Make `owner`, `asked_by`, and step `owners` metadata references for resolution, rename, trash,
  connections, and search.
- Add the Owned projects connection and the role-name navigation and creation flow.
- Add role fields to the Project and Done now processing outcomes.
- Keep status, grouping, next step, review, and project rows unchanged.
- Keep `PageLabels.apply_to` as the only frontmatter-label writer.

**Non-Goals:**

- Multiple project owners, a roles map, or a user identity ("me") setting.
- Auto-assigning appended steps from the project owner.
- Changing the body-link creation flow, which still opens a draft.
- Restricting role names to `category: person`; any `note:` note can be a hub.
- Read-mode inline editing of the role fields; edit mode owns the values.
- Searching any metadata other than the three role names.

## Decisions

### D1: `owner` is a project-only plain text name

Add `owner` to the recognized frontmatter keys. It is one optional non-empty string, trimmed on write
and valid only on a project. It uses the `note:` namespace, not a new scheme, and the file stores the
plain name (`owner: Sam Rivera`), not a link. `NoteDocument` validates it; `PageLabels` adds
`owner_text` and `with_owner_text`; `PageLabels.apply_to` writes or removes the key after `asked_by`
in the documented key order. `with_type` clears it whenever the new type is not `project`.

Alternatives considered:

- **A list of owners.** Deferred. One accountable name matches the product-owner/main-developer
  distinction; step owners already carry per-step multiplicity.
- **`note:Sam Rivera` in frontmatter.** Rejected. It makes hand-edited files noisier without adding
  resolution power.
- **A roles mapping.** Rejected. It turns the project into a task record and revives the retired
  people-map shape.

### D2: Metadata references are derived from the scanned note

`VaultNote` gains `owner: str | None` and a `metadata_references` property. That property yields a
`NoteReference` in the `note:` scheme for the owner, the requester, and every step owner. The
existing `body_references` and `references` stay body-only, so `Linked from` keeps its current
meaning and role names never become body links.

`Vault._read_note` populates `owner` from the parsed document and appends the three role-name groups
to `search_text`. `StepDocument.search_text` already removes metadata comments; role names are added
explicitly after that removal. Other metadata (`plan`, `actual`, `tags`, unknown keys) stays out of
search.

Alternatives considered:

- **Add role names to `body_references`.** Rejected. It would make role names appear under
  `Linked from` and inflate body-link counts.
- **Store a separate metadata-reference field.** Rejected as redundant; the names already live on
  the note and its steps.

### D3: Rename and trash count body and metadata references

`VaultSnapshot.affected_sites` sums body references and `metadata_references` per note. The rename
preview therefore counts a project once with every matching role occurrence. `VaultNaming._rewrite_note`
updates, in one atomic write:

1. body link destinations through `MarkdownBody.rewrite_references`;
2. `owner` and `asked_by` when their written name matches the old reference key;
3. each step's `owners` through `StepDocument.with_owners`, which preserves `plan`, `actual`, `tags`,
   and unknown keys.

`_verify_rewrite` checks body references and metadata references after serialization. The existing
content-hash guard still skips a file changed after the preview. `plan_reference_repair` includes
metadata references so unsafe-name repairs cover them too.

Alternatives considered:

- **A separate rename path per role key.** Rejected. It duplicates the preview, hash, and failure
  handling.
- **Rewrite only frontmatter and leave step owners stale.** Rejected by the decision that all three
  name locations update together.

### D4: Separate project ownership from step ownership in `Connections`

The existing `ConnectionSet.owned_projects` means "projects whose steps this page owns." Keep that
field and its `OwnedProject` value object unchanged. Add `project_owner_projects` and
`finished_project_owner_projects` for project-level ownership. The UI labels remain `Owned projects`
for the new fields and `Owned steps` for the existing field, so the internal and visible names do not
collide.

`Connections._index_project` indexes `owner` the same way it indexes `asked_by`: unique `note:`
resolution only, open projects in `project_owner_projects`, closed projects in
`finished_project_owner_projects`. `has_connections` includes both. The section order is Linked from,
Owned projects, Owned steps, Requested projects. The finished-project toggle reveals both finished
project-owner and finished requested projects; the completed-step toggle stays independent.

Alternatives considered:

- **Rename `owned_projects` and `OwnedProject` to step-specific names.** Rejected. It removes public
  Python API for a naming cleanup that is not required by the feature.
- **Reuse one `owned_projects` field for both relationships.** Rejected. The UI and tests would be
  unable to tell project ownership from step ownership.
- **Merge requested and owned projects into one list.** Rejected. The roles answer different
  questions and the user asked for distinct sections.

### D5: Role navigation without a new `AppState` field

`PageNavigator` gains `follow_role(name)` returning an outcome enum: opened, ambiguous, or missing.
It builds a `note:` reference from the written name and reuses `open_page`, the existing `ambiguous`
candidate state, and `choose_candidate`.
The page view renders role names as link-styled controls, including the project meta row and the step
owner chips and detail line.

For a missing name, the view opens a new shared component, `RoleReferenceDialog`. It offers an
editable category combobox seeded with `person`, every category used by a scanned reference, and every
category declared by a valid reference template card. The suggestions ignore the browser query and the
active section, so a search cannot hide a known category; a free-typed label and no category are still
accepted. Confirming calls `PageNavigator.create_role_reference(name, category)`, which reuses
`VaultPages.create_page` for the atomic write, refreshes the snapshot, and opens the new note in edit
mode. Cancelling writes nothing. The body-link draft flow is untouched.

`PageEditorState` gains `set_page_owner(text, *, save=False)`. The controller was already at its
25-public-name budget, so the unused `page_steps` property is removed in the same change; the count
stays at 25. The existing `set_page_asked_by(text, *, save=False)` command stays on
`PageDialogState`, which is also at its budget. Both commands mutate a `PageLabels` value through
`with_owner_text` or `with_asked_by_text`, and `PageLabels.apply_to` remains the only frontmatter
writer. The view calls the editor command for Owner and the dialog command for Asked by.

The read-mode owner and requester icons use a shared `RoleNameDialog` that offers every `note:` name
and accepts a typed name. Both commands accept `save=True`, which writes the draft through the normal
autosave, conflict, and atomic-write path and then refreshes the scan. Edit-mode typing keeps
`save=False` and leaves the draft unsaved until Done or autosave.

Alternatives considered:

- **One generic `set_page_role(field, text)` on `PageDialogState`.** Rejected. It would remove the
  existing `set_page_asked_by` command instead of an unused property.
- **A new `RoleState` controller on `AppState`.** Rejected. `AppState` has no field budget left.
- **Mutate labels in the view.** Rejected. It would create a second label writer after the refactor.

### D6: Processing accepts the two role fields

`ProcessingPlan` gains `owner: str | None` and `asked_by: str | None`. `VaultProcessing.plan_processing`
accepts both only for `PROJECT` and `DONE_NOW`, trims them, and rejects them for every other outcome.
`processed_text` applies `with_owner_text` and `with_asked_by_text` before `PageLabels.apply_to`.
`AppendStepPlan` is unchanged.

`ProcessingView` adds two text fields with the same suggestion behavior as the page editor. They are
visible only for Project and Done now, optional, and shown in the plan preview. `ProcessingState`
passes the values to the planner. The wizard saves unresolved names as plain text and does not create
person notes.

Alternatives considered:

- **Create a person note inside the wizard.** Rejected. It adds a nested dialog and a second creation
  flow for a name that can be created later from the project page.
- **Auto-assign appended steps to the project owner.** Rejected. It would make a self-owned project's
  steps waiting on the user, and the app has no "me" identity to avoid that.

### D7: Search reads the snapshot, not the raw file

The browser and Log search keep using `VaultNote.search_text`. `Vault._read_note` appends the owner,
requester, and step owner names after the existing body/step-text reduction. No query path or index
changes. Searching a role name lists the project; searching `plan`, `actual`, `tags`, or an unknown
frontmatter key does not.

Alternatives considered:

- **Search the raw frontmatter.** Rejected. It would expose unknown keys and other metadata.
- **A second search index.** Rejected. The vault has no persistent index and the snapshot is already
  in memory.

### D8: Phased implementation and gates

The label refactor is already archived. Implement this change in phases:

1. `owner` parsing and `PageLabels`;
2. reference plumbing on the scanned note and rename/trash characterization;
3. page edit form and meta row;
4. connections, search, and section order;
5. role-name navigation, the category dialog, and step owner linking;
6. Processing Wizard fields;
7. documentation, specs, and integration gates.

Each phase keeps the existing gates green. The rename/trash phase starts with characterization tests
that pin current body-only behavior before metadata rewrites are added. The architecture gate needs no
new free function or duplicate view helper; the only budget-sensitive change is removing the unused
`PageEditorState.page_steps` property before adding `PageEditorState.set_page_owner`.

## Risks / Trade-offs

- **Metadata rewrites can corrupt step comments.** → Use `StepDocument.with_owners`, verify the
  serialized rewrite, keep the atomic write and content-hash guard, and test unknown keys, CRLF, and
  partial failures.
- **One project can name the same person in the owner, requester, and several steps.** → Count each
  occurrence in the rename preview; document that the number counts references, not unique people.
- **Missing names are silent in connections.** → Render them as broken links and offer the category
  dialog; do not add a global diagnostics view.
- **The existing `owned_projects` field still means step ownership.** → Keep the name for API
  compatibility and add the explicit `project_owner_projects` fields for the new section; document
  the distinction in the `ConnectionSet` docstring.
- **`PageDialogState` is at its public-name budget.** → Keep `set_page_asked_by` there and add
  `set_page_owner` to `PageEditorState` after removing the unused `page_steps` property; both route
  through `PageLabels.apply_to`.
- **The wizard gets busier.** → Show the role fields only for Project and Done now, keep them
  optional, and reuse the existing suggestion pattern.
- **Search results change.** → Update the browser and Log search specs and tests; include only role
  names, not other metadata.
- **Existing specs contradict the new behavior.** → The deltas are the normative change; update
  `note-model`, `step-metadata`, `frontmatter`, and `names-and-links` docs in the same change.

## Migration Plan

No data migration. Projects without `owner` are unchanged. A project that already carries an unknown
`owner` string becomes recognized; a blank, list, or numeric value becomes a parse failure and opens
in raw rescue mode, consistent with `asked_by`. Rolling back treats `owner` as an unknown key and
preserves it. `afanes.yaml` and its schema version are unchanged. No dependency, platform, or runtime
network behavior changes.

## Open Questions

None.
