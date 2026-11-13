# Proposal

## Why

A project can record who asked for it, but not who is accountable for delivering it. In software work
those are often different roles: a product owner requests the project, and a main developer owns it.
The only ownership concept today is per step, which describes what a step waits on, not who owns the
project. Role names are also plain text: they go stale when the named note is renamed, do not appear
in search, and cannot be followed or created like every other note name.

## What Changes

- Add an optional `owner` frontmatter key, valid only on projects, holding one non-empty person or
  team name. The project page shows `Owner` before `Asked by`, and each role has a read-mode action
  that sets or clears it with vault-name suggestions and writes immediately.
- Make `owner`, `asked_by`, and step `owners` metadata references in the `note:` namespace: they
  resolve through the same catalog, are rewritten by rename, are counted by rename and trash
  previews, feed the target page's connections, and are searchable. Values stay plain text in the
  file; no scheme syntax is added.
- Add an `Owned projects` section to a page's Connections: open projects whose `owner` resolves to
  the page, with finished owned projects behind the existing completed toggle. The section order is
  Linked from, Owned projects, Owned steps, Requested projects.
- Make project role names and step owner names clickable in read mode. A resolved name opens its
  page; an ambiguous name shows the existing candidate picker; a missing name renders as a broken
  link, asks for a category (always offering `person`, existing categories, and template card
  categories), then creates and opens a reference note.
- Add `Owner` and `Asked by` fields to the Processing Wizard for the Project and Done now outcomes,
  with vault-name suggestions. New names are written as-is and created later from the project page.
  Append step keeps its current behavior and does not assign step owners.
- Include role names in browser search. Role names do not change project status, grouping, next
  step, review, or workspace rows.
- Update the affected specs and user documentation. No vault schema version bump and no dependency
  change.

## Capabilities

### New Capabilities

None. This change extends existing note, reference, editing, connection, project, and processing
behavior.

### Modified Capabilities

- `note-model`: add `owner` as a project-only recognized key; change `asked_by` from a non-resolving
  plain label to a plain-text value with metadata reference behavior.
- `note-editing`: edit and display `Owner`; show both project role names as links; add the category
  dialog for a missing name; clear both keys on a type change; make step owner names clickable.
- `note-references`: define metadata role references (`owner`, `asked_by`, and step `owners`) that
  resolve through the `note:` catalog without becoming body references.
- `note-identity`: count and rewrite metadata role references during rename and trash previews; step
  owner rewrites preserve the rest of the metadata comment.
- `note-connections`: add `Owned projects`, its ordering, its completed toggle, and the connection
  presence rule.
- `project-steps`: step owner names are metadata references; clicking them follows the role-name
  rules; rename rewrites preserve unknown metadata.
- `project-overview`: the project owner is display-only and does not change status, grouping, next
  step, or rows.
- `processing`: Project and Done now accept optional owner and requester names; Append step remains
  unchanged.
- `note-log`: log entries reject and remove `owner` as well as the other project keys.
- `vault-browsing`: browser search matches `owner`, `asked_by`, and step owner names while other
  metadata stays excluded.

## Impact

- Core: `frontmatter`, `labels`, `editing`, `steps`, `connections`, `search`, `processing`, vault
  read/write, and the naming rename/trash/repair paths.
- UI: page header and edit form, step owner chips and details, Connections sections, category dialog
  and navigation, Processing Wizard fields, and shared strings.
- Tests: frontmatter parsing, page editing, rename and trash, connections, search, processing, page
  and processing views, and architecture gates.
- Specs: the ten capabilities above. Documentation: frontmatter, vault format, projects and steps,
  step metadata, pages and editing, names and links, workspace search, and processing.
- Public API: additive `owner` attributes and command; `ConnectionSet` gains owned-project data.
  The unused `PageEditorState.page_steps` property is removed to keep the controller within its
  public-name budget. No other removed public API, dependency, vault-format, or schema-version change.
  Offline and cross-platform behavior stay unchanged.
