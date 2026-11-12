# Tasks

## 1. Shared step renderer

- [x] 1.1 Add `StepText` in `src/afanes/ui/components/step_text.py` and a `STEP_HEADLINE_TEXT_STYLE`
  token in `src/afanes/ui/theme.py`. The component builds an `ft.Markdown` with GitHub-flavored
  Markdown, `auto_follow_links=False`, zero paragraph padding and block spacing, a supplied text
  style, an underlined link style derived from it, and optional selectable, expand, link-handler, and
  key values. Verify `hatch check` passes.
- [x] 1.2 Add `tests/ui/test_step_text.py` covering the extension set, compact style sheet, selection,
  expansion, and link-handler wiring. Verify `hatch test tests/ui/test_step_text.py`.

## 2. Project page uses the shared renderer

- [x] 2.1 Replace the two direct `ft.Markdown` step-text calls in `src/afanes/ui/views/project_body.py`
  with `StepText`, passing the existing link handler, step surface style, `expand=True`, and
  `selectable=False`; remove the private `_step_style_sheet` helper. Verify
  `hatch test tests/ui/test_project_body_view.py tests/ui/test_page_view.py` still passes.
- [x] 2.2 Add a project-page regression test asserting the step text is an `ft.Markdown` with the
  link/emphasis value and that an internal link still reaches the existing navigation handler. Verify
  the focused test passes.

## 3. Review cards render step Markdown

- [x] 3.1 Replace the raw step text in `ReviewView._step_card` and the next/other step lines in
  `ReviewView._next_step_controls` with `StepText`. Use the headline style for the due/waiting step
  and the default body style for project-card steps; pass no link handler. Verify
  `hatch test tests/ui/test_review_view.py`.
- [x] 3.2 Update `tests/ui/test_review_view.py` so its text collector includes `ft.Markdown.value`, and
  add tests with a linked and emphasized step. Assert the step text is an `ft.Markdown`, its value
  contains the source, and no sibling `ft.Text` contains raw `[...](...)` or `**...**` syntax. Verify
  the review test module passes.

## 4. Project rows render the next step as Markdown

- [x] 4.1 Replace the `PROJECT_NEXT_STEP.format(...)` `ft.Text` line in
  `ProjectsView._project_tile` with `StepText` using the existing small muted detail style and no link
  handler; keep the status, due date, open-step count, and no-next-step label as plain text. Verify
  `hatch test tests/ui/test_projects_view.py`.
- [x] 4.2 Update `tests/ui/test_projects_view.py` so its detail collector includes `ft.Markdown.value`,
  and add tests with a linked and emphasized next step. Assert the row contains an `ft.Markdown` and no
  `ft.Text` detail contains raw Markdown syntax. Verify the projects test module passes.

## 5. Documentation and screenshot

- [x] 5.1 Add a sentence to `docs/guide/review.md` that review-card step text is rendered Markdown and
  raw source is limited to edit mode, and add the matching next-step note to
  `docs/guide/projects-and-steps.md`. Verify `hatch run docs:build` passes.
- [x] 5.2 Regenerate `docs/_static/screenshots/review.png` from a demo vault whose due step contains an
  internal link, capturing the card at the existing 1280x720 size. Verify the image shows the link
  label rather than `[...](...)`, and `hatch run docs:build` still passes.

## 6. Integration verification

- [x] 6.1 Run the full local gates: `hatch run docs:build`, `hatch check`, `hatch test --cover`,
  `openspec validate --all --strict`, `openspec doctor`, and the section 6.1 vocabulary grep. Verify
  all pass before reporting the change ready for review.

## Workflow follow-up

- Archive the change after review and after every task is checked.
- Run the post-archive release workflow in `AGENTS.md` section 5.3.
