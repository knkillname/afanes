# Tasks

## 1. Date formatter

- [ ] 1.1 Add `date_with_week(value: datetime.date) -> str` to `src/afanes/ui/strings.py` using `isoformat()` and `isocalendar()`, with a strict NumPy-style docstring; verify `hatch test tests/ui/test_strings.py` passes for a mid-year date.
- [ ] 1.2 Add formatter tests for `2025-12-29` reading `2026-W01`, `2026-01-01` reading `2026-W01`, `2021-01-01` reading `2020-W53`, `2020-12-31` reading `2020-W53`, and `2026-11-12` reading `2026-W46`; verify `hatch test tests/ui/test_strings.py` passes.
- [ ] 1.3 Add a loop test that compares the label's week-year and week with `value.isocalendar()` across a range of dates, including both year boundaries; verify the same test file passes.

## 2. Surfaces and documentation

- [ ] 2.1 Format the project due date on the page and the step plan and actual details with `date_with_week`; verify `hatch test tests/ui/test_page_view.py tests/ui/test_project_body_view.py` passes.
- [ ] 2.2 Format the projects list and review card dates; verify `hatch test tests/ui/test_projects_view.py tests/ui/test_review_view.py` passes.
- [ ] 2.3 Format the processing preview due date and move its inline due-date copy into `ui/strings.py`; verify `hatch test tests/ui/test_processing_view.py` passes.
- [ ] 2.4 Add one assertion per surface that the full `YYYY-MM-DD (YYYY-Www)` label is visible, plus a regression test that a saved due date is still `YYYY-MM-DD` and `2026-W47` is rejected; verify the affected view and frontmatter tests pass.
- [ ] 2.5 Document the display rule and the unchanged stored format in `docs/reference/frontmatter.md`, `docs/reference/step-metadata.md`, and `docs/guide/projects-and-steps.md`; verify `hatch run docs:build` passes.

## 3. Integration

- [ ] 3.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, and `openspec doctor`; verify all pass and coverage remains at or above 85 percent.
- [ ] 3.2 Open a vault in the desktop app and confirm the page, projects list, review, and processing preview each show the label, including a New Year date; record the platform and any surface that did not.

## Workflow follow-up

- Apply the change with `/opsx-apply` after approval.
- Archive the change after implementation, review, and the project gates pass.
