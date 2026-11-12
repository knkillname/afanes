# Design

## Context

See `proposal.md` for motivation. The current rendering paths differ:

- `ProjectBodyView` already renders step text with `ft.Markdown`, `GITHUB_FLAVORED`, a compact
  `MarkdownStyleSheet`, and `on_tap_link` for read-mode navigation. The project page screenshot shows
  links and emphasis correctly.
- `ReviewView` renders due/waiting step text, the project card's next step, and other open steps with
  `ft.Text`. The review screenshot shows raw `[Incident notes](<note:Incident notes>)`.
- `ProjectsView` builds the row's next-step line as `PROJECT_NEXT_STEP.format(title=step.text)` and
  renders it with `ft.Text`. The Projects screenshot shows raw `Next: **Bold** step`.

The Markdown parser is not the problem. The missing piece is using the working renderer in the summary
surfaces. The UI layer already depends on Flet and `afanes.ui.theme`; no core or model behavior is
involved.

## Goals / Non-Goals

**Goals:**

- Render inline Markdown for every read-only step text in review cards and project rows.
- Keep one shared rendering path so the project page, review cards, and project rows cannot drift.
- Preserve the existing headline emphasis on review step cards and the small muted style on project
  row details.
- Keep the project page's internal-link navigation unchanged.
- Keep rendering display-only: no vault write, no new dependency, no file-format change.

**Non-Goals:**

- Replacing `ft.Markdown` with a custom parser or a new Markdown library.
- Making links in review cards or project rows navigate to pages.
- Changing edit mode, raw rescue mode, or the existing page read-mode link rules.
- Changing step parsing, metadata handling, or search behavior.
- Changing the project page screenshot, which already renders correctly.

## Decisions

### Use `ft.Markdown` through one shared component

Add `StepText` in `src/afanes/ui/components/step_text.py`. It builds an `ft.Markdown` with:

- `extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED`;
- `auto_follow_links=False`;
- a compact `MarkdownStyleSheet` with `p_padding=0` and `block_spacing=0`;
- a `p_text_style` supplied by the surface, with an `a_text_style` that reuses the same text color and
  adds an underline;
- optional `selectable`, `expand`, `on_tap_link`, and `key` values.

The component is a class with a `build()` method, matching the existing `Banner`, `Panel`, `Card`, and
`StatusLabel` components. It does not parse Markdown; Flet does.

Alternatives considered:

- A custom inline parser that emits `ft.TextSpan` values. Rejected because `ft.Markdown` already
  renders the app's link and emphasis syntax on the project page, and a second renderer would diverge.
- Keeping `ft.Text` and stripping Markdown syntax with a regex. Rejected because it would drop link
  labels, emphasis, and inline code, and would need a parser anyway.
- Duplicating the `ft.Markdown` setup in each view. Rejected because the style and extension choices
  would drift, which is how this bug appeared.

### Text styles are surface-specific tokens

The review due/waiting step card keeps its prominent headline size. Add a
`STEP_HEADLINE_TEXT_STYLE` token to `ui/theme.py` so the component does not hide a magic size in the
view. The project page continues to use `STEP_TEXT_COLOR`; the project row uses the existing small
muted detail style.

Link styling derives from the supplied text style rather than a separate color. That keeps links
readable on the accent step card, the plain review card, and the muted project row without adding a
second set of color tokens.

### Summary-surface links are display-only

The project page passes its existing `follow` callback, so read-mode links keep navigating. Review
cards and project rows pass no link handler. Their navigation path remains the existing explicit
action: **Open project** on a review card, and selecting the project row. This avoids a link tap
changing the page behind a review session or surprising the user while scanning projects.

The rendered link text is still a label, not raw syntax. The interaction difference is documented in
the review guide and covered by a scenario.

### The project page is the first consumer of the shared component

`ProjectBodyView` replaces its two direct `ft.Markdown` calls with `StepText`, passing the existing
link handler, `expand=True`, `selectable=False`, and the step surface style. The private
`_step_style_sheet` helper moves into the component. Existing project-page tests should pass without
behavior changes; the shared component keeps the same extension set, compact spacing, and link
callback.

### Tests assert control type and visible text, not just strings

The existing review helper collects `ft.Text.value`; the project-row helper does the same for detail
text. Both must also collect `ft.Markdown.value` so the current assertions still see the step text.
Add assertions that the step text is an `ft.Markdown`, that its value contains the Markdown source,
and that no sibling `ft.Text` contains the raw `[label](...)` or `**...**` syntax. Add a dedicated
`tests/ui/test_step_text.py` for the component's extension set, compact style sheet, selection, and
link-handler wiring.

### Documentation follows the behavior

Add one sentence to `docs/guide/review.md` stating that card step text is rendered Markdown and raw
source is limited to edit mode. Regenerate `docs/_static/screenshots/review.png` from a demo vault whose
step contains a link. The project page screenshot already proves the working renderer and does not
need a new capture.

## Risks / Trade-offs

- **Markdown block spacing makes summary lines taller** -> The compact style sheet zeroes paragraph
  padding and block spacing; the regenerated screenshot is the visual check.
- **Links in summaries look clickable but are inert** -> Keep them styled as labels, document the
  explicit Open project action, and preserve full link navigation on the project page.
- **Headline styling drifts from the existing card** -> Use one theme token and compare the regenerated
  review screenshot before closing the change.
- **Test helpers over-collect Markdown source** -> Keep assertions on control type and rendered-label
  intent; do not treat `ft.Markdown.value` as proof of visual rendering.
- **A future surface repeats the bug** -> The shared component is the only supported read-only step
  renderer; the review and project-row tests fail if a surface regresses to raw `ft.Text`.
- **Flet Markdown behaves differently across platforms** -> The project page already uses the same
  control and renderer; this change adds no new client or parser.

## Migration Plan

1. Add the shared component and its test.
2. Move the project page to the component and confirm its tests and screenshot behavior are unchanged.
3. Update review cards and project rows, then update their tests.
4. Update the review guide and regenerate the review screenshot.
5. Run `hatch check`, the focused UI tests, `hatch test --cover`, and `hatch run docs:build`.

There is no data migration or rollback beyond reverting the UI changes. No note is rewritten by
rendering.

## Scope Note

Full-gate verification surfaced a pre-existing failure in the frontmatter round-trip property test:
its Hypothesis strategy generated `.` and `..` category labels, which `CategoryLabel` correctly
rejects as traversal segments. The fix is test-only. The strategy now excludes those two labels, and
the existing deterministic `TestCategoryLabel::test_traversal_segment_is_rejected` continues to cover
the product rule. No product code or behavior changes.

## Open Questions

None blocking. Whether review-card links should become navigable instead of display-only can be
revisited in a later change without changing the rendering contract.
