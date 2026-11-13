# Proposal

## Why

The archived `add-project-roles` change passed every machine gate but its test suite is not
yet a reliable executable record of the specification. A scenario-to-test audit found two
code/spec divergences introduced by that change, one pre-existing processing gap, four
under-specified or under-tested behaviors, and fifteen scenarios with no asserting test.

This change closes those findings in one approved change. The archived artifacts stay frozen;
all behavior, specification, test, and documentation work happens here.

## What Changes

- **Connections:** Omit a connection group when it has no visible item. Move the two reveal
  controls to the Connections panel footer so a page with only hidden completed steps or
  finished projects can still reveal them. This removes the empty placeholder groups and the
  shared-toggle trap.
- **Page navigation:** Reset the page pane scroll position whenever the open page changes:
  browser selection, links, connection entries, owned steps, and Back. A page always opens at
  the top.
- **Processing:** Add **Log entry** to the Processing Wizard's outcome list. The core outcome
  already exists and the form already hides project fields for non-project outcomes; only the
  wizard option and its label are missing.
- **Rewrite reports:** For rename, type change, date change, and link repair, report which
  notes were updated and which were not, using vault-relative paths and the reason for each
  skipped or failed note. Replace the current count-only partial-failure messages.
- **Search specification:** Keep the browser's behavior of listing a project when a step
  matches, but remove the requirement that the matching step be displayed with the project.
- **Null frontmatter:** Treat a null `status` or `due_date` as absent on every note type. The
  specification will state the null rule explicitly; the named-reference keys remain strict.
  Tests cover the null cases. No parser behavior changes.
- **Tests:** Add regression tests for every behavior fix, the fifteen missing-scenario tests,
  the prioritized weak tests from the audit, and `owner` in the label-write architecture gate.
- **Prose:** Fix the stale frontmatter module docstring and rename the stale `vault-browsing`
  and `note-editing` requirement titles. The `vault-browsing` Purpose stays for a later prose
  edit because OpenSpec deltas carry requirements, not Purpose.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `note-connections`: A connection group is omitted when it has no visible item; the reveal
  controls remain available when only completed items exist.
- `vault-browsing`: A page change opens at the top. The step-text search scenario lists the
  project without requiring the matching step to be displayed. The stale requirement title is
  renamed.
- `processing`: Every fixed outcome, including Log entry, is offered by the Processing Wizard.
- `note-identity`: Every reference rewrite reports the notes updated and the notes not updated,
  with reasons.
- `note-model`: Null `status` and `due_date` are absent; the other forbidden keys remain errors.
- `note-editing`: The stale requirement title is renamed to match the fields it describes.

## Impact

- UI: `src/afanes/ui/views/page.py`, `workspace.py`, `processing.py`; `src/afanes/ui/state/dialogs.py`;
  `src/afanes/ui/strings.py`; possibly `src/afanes/ui/theme.py`.
- Core: `src/afanes/core/frontmatter.py` docstring only. Rewrite reports, processing outcomes,
  and search matching already carry the required data.
- Tests: `tests/ui/test_page_view.py`, `test_workspace_view.py`, `test_projects_view.py`,
  `test_processing_view.py`, `test_state.py`; `tests/core/test_frontmatter.py`,
  `test_connections.py`, `test_search.py`, `test_integration.py`, `vault/test_naming.py`,
  `vault/test_processing.py`; `tests/core/test_architecture.py`.
- Documentation: `docs/guide/pages-and-editing.md`, `docs/guide/workspace.md`,
  `docs/reference/frontmatter.md`; check `docs/guide/processing.md` and `README.md` for stale
  statements.
- No new dependency, network access, telemetry, persistent index, or storage change.
- Cross-platform behavior is unchanged; the work is UI presentation, specification, and tests.
