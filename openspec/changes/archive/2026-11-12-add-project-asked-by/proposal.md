# Proposal

## Why

A project is often requested by someone else: a colleague, a family member, or a group. The project
page has no fixed place to record who asked, so the context lives in prose, in a link, or nowhere. The
Projects workspace shows status, due date, open-step count, and next step, but not why the project
exists or who is waiting for it. A consistent header field keeps that context visible without turning
the vault into a task database.

## What Changes

- Add one optional frontmatter key, `asked_by`, valid only on `project` notes. Its value is a single
  non-empty string naming the person or group that requested the project.
- Show `Asked by <name>` in the project page meta row, beside status and due date, when the key is
  present. The row omits the label when the key is absent.
- Offer an `Asked by` field in the page editor, visible only for projects. Clearing the field removes
  the key. Changing a note away from `project` also removes it.
- Keep the value as plain text. It is not an internal reference, does not resolve or navigate, is not
  searched, and does not appear in project rows, grouping, ordering, or review.
- Preserve unknown frontmatter keys, the body, and the newline style on every write.
- Update the frontmatter contract and the user documentation to describe the fifth recognized key and
  its scope.

## Capabilities

### New Capabilities

None. This change extends the existing note model and page editing behavior.

### Modified Capabilities

- `note-model`: the recognized frontmatter keys gain `asked_by`, scoped to projects, with a single
  non-empty string value.
- `note-editing`: the project page meta row shows the requester, the edit form sets and clears it, and
  a type change away from `project` clears it.

## Impact

- **Data format**: additive. Existing notes without `asked_by` are unchanged. A project that already
  carries an unknown `asked_by` value now has it validated; a non-string or blank value becomes a
  parse failure and opens in raw rescue mode, consistent with the other scoped keys.
- **Code**: `core/frontmatter.py` (parse, validate, preserve), `core/editing.py` (page labels and
  serialization), `ui/state/dialogs.py` (edit-form command), `ui/views/page.py` (meta row and edit
  field), `ui/strings.py` (labels), plus parser, editing, and view tests.
- **Documentation**: `docs/reference/frontmatter.md`, `docs/reference/vault-format.md`,
  `docs/guide/projects-and-steps.md`, and `CHANGELOG.md`.
- **Dependencies**: none.
- **Platforms**: no platform-specific behavior; the key travels in the Markdown file.
- **Non-goals**: multiple requesters, project-level people or roles, a read-mode person picker,
  clickable or searchable names, filtering by requester, a Processing field, and project-row display.
