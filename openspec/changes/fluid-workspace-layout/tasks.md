# Tasks

## 1. Fluid shell columns

- [x] 1.1 Replace `BROWSER_MAX_WIDTH` and `CONTENT_MAX_WIDTH` with a `BROWSER_SHARE` token and add `FIELD_MIN_WIDTH`; verify `tests/ui/test_theme.py` reflects the new token set and no dead maximum-width token remains
- [x] 1.2 Compute the browser width from the available workspace width with the browser share clamped by the browser and page minimums, leave the detail expanding, and remove every maximum-width assignment; verify `tests/ui/test_workspace_view.py` covers 1024, 1100, and very wide windows without clipping
- [x] 1.3 Update `docs/develop/interface-standard.md` and `docs/guide/workspace.md` for fluid columns and removed maximum widths; verify `hatch run docs:build`

## 2. Shared Log date-control row

- [x] 2.1 Replace the two Log control rows with one wrapping row containing Today's Entry, Entries, and Everything in that order; verify `tests/ui/test_workspace_view.py` finds all three controls in the same row and finds no second control row
- [x] 2.2 Add narrow-browser coverage for the wrapping Log row and keep the existing search-hides-controls test green; verify `hatch test tests/ui/test_workspace_view.py`
- [x] 2.3 Update `docs/guide/workspace.md` and `docs/guide/log.md` for the shared row; verify `hatch run docs:build`

## 3. Full-width page content

- [x] 3.1 Remove the fixed page-column width and the `fit_width` resize plumbing so the page column expands inside the detail card; verify `tests/ui/test_page_view.py` shows the column filling the card in read and edit modes
- [x] 3.2 Replace the `TestPageWidth` cap tests with full-width and minimum-width coverage; verify `hatch test tests/ui/test_page_view.py`
- [x] 3.3 Update `docs/develop/interface-standard.md` and `docs/guide/pages-and-editing.md` for uncapped page content; verify `hatch run docs:build`

## 4. Adaptive label flow and Starter

- [ ] 4.1 Add a `FieldFlow` component under `src/afanes/ui/components/` that assigns 12-column spans from the measured width and the field minimum, filters hidden controls, and reflows on width or visibility changes; verify new component tests cover wide, narrow, odd-count, and hidden-control layouts
- [ ] 4.2 Integrate `FieldFlow` into the page editor with visible controls in Type, Category, Status, Date, Starter, Due date, Owner, Asked by order, and place the Starter dropdown inside the flow while its description and warning stay in the panel below; verify `tests/ui/test_page_view.py` covers a wide log draft with Type, Date, and Starter on one row and a wrapped narrow pane
- [ ] 4.3 Update `tests/ui/test_page_view.py` expectations for the form control order, the expanding body field, the hidden Starter dropdown, and the reflow after a type or starter change; verify `hatch test tests/ui/test_page_view.py`
- [ ] 4.4 Update `docs/guide/pages-and-editing.md` for the adaptive label flow and the Starter position; verify `hatch run docs:build`

## 5. Integration checks

- [ ] 5.1 Run `hatch check` and fix lint, format, and type findings without changing behavior; verify the command exits 0
- [ ] 5.2 Run `hatch test --cover` and keep coverage at or above 85%, with parser, link, and vault modules unchanged; verify the command exits 0
- [ ] 5.3 Run `tests/ui/test_conformance.py` and shrink only baseline entries whose violations disappeared; verify no baseline entry is stale and no count grows
- [ ] 5.4 Run `openspec validate --all --strict`, `openspec doctor`, and the AGENTS.md vocabulary compliance grep; verify all three pass with the documented exclusions
- [ ] 5.5 Resize the running app at 1024, 1100, and a very wide window and confirm the Log controls share a row when they fit, the editor fields stretch, and no region clips; record the observation for the archive

## Workflow follow-up

- Archive the change after the owner accepts the visual result.
- Run the post-archive release workflow from AGENTS.md section 5.3.
