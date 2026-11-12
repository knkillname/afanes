# Proposal

## Why

The documentation screenshots exposed raw Markdown in read-only summaries. The review card shows
`Copy the timeline into [Incident notes](<note:Incident notes>)` literally, and the Projects workspace
row shows `Next: **Bold** step`. The project page already renders the same step text with
`ft.Markdown`, so the inconsistency is in the summary surfaces, not in the vault or the parser.

A user who is reading a review or scanning projects should see the rendered label and emphasis. Raw
Markdown should appear only in edit mode or raw rescue mode.

## What Changes

- Add one shared read-only step-text renderer based on `ft.Markdown`, with compact paragraph spacing,
  a configurable text style, and optional link handling.
- Use it for every step text in the guided review: the due or waiting step card, the project card's
  next step, and the project card's other open steps.
- Use it for the next-step line in the Projects workspace row, so `Next: **Bold** step` renders as a
  labelled Markdown line instead of raw syntax.
- Refactor the project page step rows to use the same component. The page already renders Markdown and
  keeps its internal-link navigation; this is a behavior-preserving refactor.
- Keep raw Markdown in edit mode and raw rescue mode. Rendering is display-only and never rewrites a
  note.
- Keep link taps inert in the review and project-row summaries, where the existing card action or row
  selection is the navigation path. The project page keeps its read-mode link navigation.
- Update the review tests, add a component test, regenerate the affected documentation screenshot, and
  add a short note to the review guide.
- Out of scope: replacing the Markdown renderer, making summary-surface links navigate, changing the
  edit-mode editor, changing step parsing, or adding a runtime dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `guided-review`: review cards render step text as Markdown, including the due/waiting step card,
  the project card's next step, and its other open steps.
- `project-overview`: a project row renders its next step as Markdown while its status, due date,
  open-step count, and no-next-step label remain plain text.

## Impact

- `src/afanes/ui/components/step_text.py` is added: the shared read-only step-text control.
- `src/afanes/ui/views/review.py` replaces raw `ft.Text` step lines with the shared control.
- `src/afanes/ui/views/projects.py` replaces the raw next-step line with the shared control.
- `src/afanes/ui/views/project_body.py` uses the shared control instead of duplicating Markdown
  configuration. Its behavior, link navigation, and step actions are unchanged.
- `src/afanes/ui/theme.py` may gain one typography token for the review step headline so the component
  does not introduce a magic size.
- Tests cover the shared control, the review cards, the project rows, and the unchanged project page.
- `docs/guide/review.md` gains a sentence about rendered step text, and
  `docs/_static/screenshots/review.png` is regenerated.
- No core, model, storage, or runtime dependency change; no vault write behavior changes.
