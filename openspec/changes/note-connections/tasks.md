# Tasks

## 1. Snapshot and derivation

- [ ] 1.1 Add `asked_by: str | None` to `VaultNote`, populate it from `NoteDocument.asked_by` in `Vault._read_note`, and update the test helper; verify `hatch test tests/core/vault/test_snapshot.py` passes.
- [ ] 1.2 Add `src/afanes/core/connections.py` with `ConnectionSet`, `OwnedProject`, and a `Connections` service that builds the three indexes from one snapshot; verify import and service tests pass with `hatch test tests/core/test_connections.py`.
- [ ] 1.3 Add core tests for unique resolution, repeated links listed once, self exclusion, missing and ambiguous exclusion, trashed exclusion, open/completed step split, open/finished project split, `asked_by` matching, and deterministic ordering; verify `hatch test tests/core/test_connections.py` passes.
- [ ] 1.4 Add the `VaultSession.connections` property and its private snapshot-identity cache, clear it in `reset`, and verify a state test shows one build per snapshot and a rebuild after a new snapshot with `hatch test tests/ui/test_state.py`.

## 2. Page section

- [ ] 2.1 Add the section, subsection, toggle, and empty-state copy to `src/afanes/ui/strings.py`, and the section spacing to `src/afanes/ui/theme.py`; verify the strings and theme tests pass.
- [ ] 2.2 Render the Connections section after the rendered body with `Linked from`, `Owned steps`, and `Requested projects`, using title rows and project headings; verify the page-view tests cover all three subsections with `hatch test tests/ui/test_page_view.py`.
- [ ] 2.3 Wire row clicks through the existing navigation command, open owned steps at the project top, add the independent "Show completed" toggles, and reset both when the page path changes; verify the interaction tests pass with `hatch test tests/ui/test_page_view.py`.
- [ ] 2.4 Add page-view tests for the hidden empty state, hidden edit and raw rescue modes, grouped step order, each toggle in isolation, and the reset on page change; verify `hatch test tests/ui/test_page_view.py` passes.
- [ ] 2.5 Document the section in `docs/guide/pages-and-editing.md` and its relationship to references and ownership in `docs/reference/names-and-links.md`; verify `hatch run docs:build` passes.

## 3. Integration

- [ ] 3.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, and `openspec doctor`; verify all pass and coverage remains at or above 85 percent.
- [ ] 3.2 Run `hatch run python scripts/scan_benchmark.py --notes 1000 5000 10000 --repeat 5`; verify the scan and first-page index build stay within the existing benchmark envelope, or record the measured cost in the change.

## Workflow follow-up

- Apply the change with `/opsx-apply` after approval.
- Archive the change after implementation, review, and the project gates pass.
