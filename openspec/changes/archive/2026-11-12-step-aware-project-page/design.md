# Design

## Context

See `proposal.md` for motivation. The current page pane renders a project twice: `PageView._refresh_steps` builds interactive rows from `PageEditorState.page_steps`, while `PageView.read_body` renders `PageEditorState.page_read_text` as one `ft.Markdown` control. The two surfaces share a page card background and the body still contains the task-list lines.

Relevant constraints:

- `StepDocument` already finds task list items through the CommonMark parser and rewrites one line at a time.
- `VaultSteps` already provides `plan_step` and `set_step_owners` with atomic writes and confirmation.
- `ui/` is presentational: it must not implement Markdown parsing or write a vault file.
- `PageEditorState` has 23 public names against a budget of 25; `PageDialogState` has 22 against the same budget; `AppState` is at 10 of 10.
- `ft.Markdown` renders a whole document. Flet exposes link taps and selection changes, but not a line or block under the pointer, so per-step hover cannot be added to the existing single Markdown control.
- The page pane currently avoids rendered dialogs; `ft.DatePicker` needs `Page.show_dialog`, which only the application shell owns.

## Goals / Non-Goals

**Goals:**

- One project reading surface that preserves prose and step order.
- Interactive step rows inside the body with plan and owner actions.
- The same actions reachable with mouse, keyboard, and touch.
- Project status and due date visible in read mode with a due-date action.
- All new writes atomic, conflict-aware, and limited to the affected line or frontmatter key.

**Non-Goals:**

- No project-level owner field or frontmatter schema change.
- No general-purpose Markdown renderer or block editor.
- No tags editor in this change; tags stay visible and preserved.
- No change to step identity, completion, review, or project grouping rules.
- No new runtime dependency, network access, or persistent index.

## Decisions

### Project body block model lives in core

Add a core value object, `afanes.core.project_body.ProjectBody`, that owns one project body and exposes ordered blocks:

- a prose block carries the exact Markdown source for that block;
- a step-list block carries `ProjectStep` values plus the nesting depth and any detail Markdown belonging to each step.

The block model uses the CommonMark token map to find top-level blocks. A top-level list becomes a step-list block only when every list item in it, including nested items, is a task list item. A mixed list, a task list inside a blockquote, or any shape that cannot be separated without changing surrounding Markdown becomes a prose block. This fallback preserves content and formatting at the cost of hover actions for that block.

Alternatives considered:

- Line-by-line splitting outside a parser. Rejected because fenced code, blockquotes, nested lists, and multi-line items break it.
- Rendering each source line as its own control. Rejected because it destroys paragraph wrapping, list semantics, and table rendering.
- Keeping the single `ft.Markdown` body. Rejected because it cannot provide per-step actions.

### Page state exposes blocks, not rendered controls

`PageEditorState` gains a `page_body_blocks` property that returns the parsed blocks for a project, or an empty tuple for other notes. This keeps Markdown parsing out of the view and follows the existing `page_steps` and `page_read_text` pattern.

`PageEditorState` gains one command, `edit_page_step_metadata`, rather than separate plan and owner commands. It accepts a frozen `StepEdit` value object that distinguishes “change plan” from “change owners”. This keeps the controller at 25 public names and lets both actions share the same reload and snapshot-refresh path.

The command calls `VaultSteps.plan_step` or `VaultSteps.set_step_owners` with `confirm=True`, reloads the page, and refreshes the snapshot. It never writes through the UI.

### Read-mode due date reuses the existing label draft

`PageDialogState` already owns `set_page_due_date`, which updates `PageLabels` without writing. Add one command there, `save_page_due_date`, which updates the label text and forces a page write. `PageEditorState.autosave` gains a `force` flag so a read-mode metadata change can write without entering edit mode. The existing conflict guard, baseline hash, and atomic writer stay in charge.

This keeps the due-date command with the other label mutations and avoids a new `AppState` field. `PageDialogState` reaches 23 public names.

### Step rows are composed controls, not checkbox labels

Each step row is a checkbox plus a separate Markdown control for the step text. The checkbox carries the step text as its `semantics_label`. The Markdown control uses GitHub-flavored parsing so inline formatting and references render, with zero paragraph padding and link styling that contrasts on the accent surface.

Using `ft.Markdown` as the checkbox label was rejected because Flet wraps a checkbox label in a tap handler that toggles the checkbox. A link tap inside the label could both navigate and complete the step.

### Actions are always present but muted

The person and calendar actions are always rendered on the row. At rest they use a muted `ON_SECONDARY_CONTAINER` color. Hover and keyboard focus raise them to full emphasis. This satisfies mouse discovery without making touch users depend on hover.

The calendar action opens the date picker for `plan`; when a plan exists, an adjacent clear action removes it. The person action opens an inline owner panel under the row. The panel shows removable chips and a text field with suggestions from `VaultSession.assignment_candidates(ReferenceScheme.NOTE, query)`. Each add or remove writes immediately, so the panel never becomes a second unsaved draft.

### Date picking is injected from the shell

`PageView` and the new project-body view receive a `pick_date` callback from `WorkspaceView`, which receives it from the application shell. The shell owns the `ft.DatePicker` and calls `Page.show_dialog`. Tests pass a fake picker callback. This keeps `PageView` free of page-level dialog plumbing and preserves desktop, web, and touch parity.

Alternative considered: an inline `YYYY-MM-DD` text field. It avoids the callback but is a worse fit for a calendar icon and adds another validation surface.

### Step-aware body rendering is a separate view component

A new `ui/views/project_body.py` component renders the blocks returned by `page_body_blocks`. It owns only presentation and transient UI state: the open owner panel, the owner query, and a local error message. It reads `app_state` and calls the page commands. `PageView` delegates the project read body to it and keeps the existing non-project `ft.Markdown` path, now using `GITHUB_FLAVORED`.

The `ProcessingView.capture_body` Markdown control uses the same extension set so a note does not render task markers differently in two places.

### Styling uses theme tokens

Add steps-specific tokens to `ui/theme.py`: accent surface, on-accent text, muted action color, and link decoration. The step card uses `SECONDARY_CONTAINER`; prose remains on the page surface. No hex colors or ad-hoc pixel values in views. All new copy, including action tooltips, owner labels, due-date labels, and fallback messages, goes in `ui/strings.py`.

## Risks / Trade-offs

- **Body splitting loses fidelity in unusual Markdown** → Use a conservative fallback to ordinary Markdown for mixed lists, blockquotes, tables, and any shape that cannot be separated safely. Add fixtures for each shape.
- **The state budget is reached exactly** → Keep one combined step command, put the due-date command on `PageDialogState`, and let the architecture gate prove the counts. No further public names in these controllers.
- **Icon-only actions reduce discoverability** → Always-visible icons, tooltips, semantics labels, keyboard focus, and full emphasis on hover/focus.
- **Date picker plumbing crosses the shell boundary** → Inject a small callback instead of exposing `Page` to views; test with a fake picker.
- **Immediate owner writes can cause several writes** → Each write is one line, atomic, and leaves no hidden draft. The panel refreshes from the written file after each action.
- **Project due-date write bypasses edit mode** → Reuse the existing draft, baseline hash, conflict guard, and atomic writer through `autosave(force=True)`; never write directly from the view.
- **Accent contrast** → Pair `SECONDARY_CONTAINER` with `ON_SECONDARY_CONTAINER` for text, icons, and links, and underline links so navigation is not color-only.

## Migration Plan

No vault migration is required. Existing notes keep their current Markdown, frontmatter, and step metadata. The new renderer reads the same files, and any unsupported shape simply renders as Markdown. Rollback is a code revert; no data was rewritten by the change itself.

## Platform Notes

The date picker is a Flet `DatePicker` opened by the shell for desktop and web through the same callback. Hover and focus emphasis uses `ButtonStyle` state colors, so it does not depend on a pointer-only event; every action also has a tooltip and a semantics label and stays visible for touch. Colors come from Material role tokens (`SECONDARY_CONTAINER` and `ON_SECONDARY_CONTAINER`), and links are underlined so navigation does not rely on color alone in light or dark themes. Linux was exercised by the automated tests; macOS and Windows use the same Flet controls and remain manual evidence in `RELEASE.md`.

## Open Questions

None blocking. The exact date-picker visual treatment and the owner-panel spacing can be adjusted during implementation without changing the specs or the approach.
