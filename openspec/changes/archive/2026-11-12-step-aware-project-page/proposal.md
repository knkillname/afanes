# Proposal

## Why

A project page currently shows its steps twice: an interactive Steps panel and the same task lines inside the rendered Markdown body. The duplicate surfaces disagree about interaction, the body shows literal task markers, and changing a step's plan or owners requires entering raw edit mode. Reading a project should be the same surface where its steps are acted on.

## What Changes

- Render a project's read mode as one step-aware body. Ordinary prose blocks stay Markdown; each contiguous task list becomes an accent-tinted card of interactive step rows.
- Remove the separate Steps panel and the duplicate checklist from the project page.
- Show each step's checked state, text, owners, plan date, actual date, and tags as structured content rather than raw metadata syntax.
- Add always-visible, muted person and calendar actions to every step row, emphasized on hover and keyboard focus so mouse, touch, and keyboard users can reach them.
- Let the calendar action set or clear the step's `plan` date. `actual` remains automatic when the step is ticked.
- Let the person action manage the full owner list with removable chips and suggestions drawn from note names in the vault.
- Add a project meta row under the page title showing status and the optional due date. Its calendar action sets or clears the project due date from read mode.
- Keep owners step-level. Projects do not gain an owners frontmatter field.
- Fall back to ordinary rendered Markdown for a body shape that cannot be split into clean step blocks, so content is never dropped or rewritten.
- Keep non-project notes on ordinary GitHub-flavored Markdown rendering, including static task-list checkboxes.
- Preserve existing atomic-write, metadata-preservation, conflict, and external-edit rules for every new action.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `note-editing`: read mode renders a project body as step-aware blocks and exposes inline step and project-date actions.
- `project-steps`: a step's plan date and owner list are editable from the page while preserving completion, metadata, and atomic rewrite semantics.

## Impact

- `src/afanes/core/` gains a project-body block model that identifies prose blocks and step-list blocks, including step depth and detail ranges.
- `src/afanes/core/vault/steps.py` already provides plan and owner rewrites; the page commands reuse them.
- `src/afanes/ui/state/pages.py` gains a body-block view and one step-metadata command within the existing controller budget.
- `src/afanes/ui/views/page.py` and shared UI components render the step-aware body, hover/focus actions, owner manager, and project meta row.
- `src/afanes/ui/theme.py` and `src/afanes/ui/strings.py` gain the accent, muted-action, and copy tokens.
- The application shell wires the date picker used by step and project actions.
- Tests cover rendering, block fallbacks, step metadata writes, owner suggestions, due-date writes, accessibility states, and external-edit behavior.
- No runtime dependency, network, account, telemetry, or persistent index is added.
