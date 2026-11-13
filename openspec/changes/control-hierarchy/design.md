# Design

## Context

The workspace is built from presentational view classes. Each view constructs its controls once,
keeps references to the ones it mutates, and repaints through `refresh()` when the shared state
changes. Dialogs live in `app.py` and the role components. The conformance gate is an AST scan of
`src/afanes/ui` with a baseline that may only shrink; it counts controls per class, so it cannot tell
which of a class's dialogs and cards are visible together.

See `proposal.md` for motivation and `specs/` for the behavior contract.

## Goals / Non-Goals

**Goals:**

- Make every affirmative action insensitive until its current input can succeed, with live updates.
- Make the visible suggested or destructive action unique per rendered surface.
- Put Cancel before the affirmative action in every inline confirmation.
- Bring the gate in line with the header-bar exception already stated in `interface-theme`.
- Remove the remaining dense list rows and shrink the baseline.

**Non-Goals:**

- No keyboard shortcut map, toast system, undo, writing-style sweep, or window-title work; those are
  later waves.
- No new state fields, controllers, or dependencies.
- No change to vault writes, parsing, search, or the CLI.

## Decisions

### Availability is computed by the view

Each view derives availability from the controls it already owns: composer text, name fields,
selected outcome, form text, and date fields. A change handler updates the dependent control's
`disabled` flag and repaints it; `refresh()` re-applies the same rule so a state change cannot leave
a stale enabled action.

*Alternative considered:* a `can_*` flag on `AppState` or a domain controller. Rejected because it
duplicates input that already lives in the control, adds a public state field, and forces every
keystroke through the state singleton. The command-level validation stays unchanged as the guard
for direct calls.

Specific rules:

| Surface | Affirmative action | Enabled when |
| --- | --- | --- |
| Inbox composer | Capture | the composer has non-blank text |
| Processing form | Preview | an outcome is selected and its required project or date is valid |
| New Vault dialog | Create | the path field has non-blank text |
| New Reference dialog | Create | the name field has non-blank text |
| Page rename | Preview and Rename | the new-name field has non-blank text |
| Review form | Confirm | the typed value is non-blank and, for postpone, a valid date |

### One affirmative style per rendered surface

The suggested style marks the action that completes the current surface. When a surface has several
mutually exclusive states, each state may keep its own suggested control because only one is visible
at a time. Two changes make that true:

- Welcome keeps one suggested action: **Choose Vault** on the desktop presentation and **Open** in
  the browser presentation. **New Vault** becomes an outlined button.
- While an inline form or confirmation is open in a review card, the card hides its normal action
  rows so the form's **Confirm** is the only affirmative control. Cancelling restores the rows.
- The page conflict panel keeps **Reload from Disk** as the suggested action; **Overwrite with This
  Version**, **Recreate Page**, and **Discard Draft** become regular buttons. Reload is the safe
  recovery, and the overwrite path is already explained in the panel.
- The rename panel keeps **Rename** as the suggested action; **Preview** becomes a regular button.
  The repair panel keeps **Rewrite Links** suggested.

The class-scope AST baseline remains a conservative upper bound for classes that own several
dialogs. A new view-level test walks the built control tree, respects `visible`, and asserts that no
rendered surface shows more than one suggested or destructive control. That test, not the class
count, verifies the requirement.

*Alternative considered:* teaching the AST gate about visibility. Rejected; static analysis cannot
resolve which controls a card includes without reproducing the view logic.

### Cancel first is a list order, not a new component

`Panel` already renders its actions in the order it receives. Reorder each call site to put Cancel
first and the affirmative action last, matching the dialogs:

- trash: Cancel, Move to Trash
- type change: Cancel, Change Type
- category move: Cancel, Move Page
- rename: Cancel, Preview, Rename
- repair: Cancel Creation, Keep Old Links, Rewrite Links

A view test asserts the order for each panel. No shared helper is introduced; the order is a
two-line change per call site and is easier to read than a wrapper.

### The gate gets an explicit header-bar allowlist

`interface-theme` already permits icon-plus-label inside a header bar, sidebar, or view switcher. The
gate currently flags every such button. Add a small `HEADER_ACTION_KEYS` set to the conformance test
containing the page toolbar actions (`page-edit-action`, `page-done-action`, `process-note`), give
the two page buttons those keys, and skip exactly those keys in the icon-plus-label rule. A focused
test asserts the allowlist matches the controls placed in each view's header row, so it cannot grow
silently.

All other icon-plus-label buttons migrate to one or the other: dialog actions become label-only,
compact form actions become label-only, and the remaining card actions lose their icons.

*Alternatives considered:* inferring header membership from the AST (fragile and hard to review), and
a `HeaderAction` wrapper component (a new public class for three controls, and it would hide any
misuse from the gate). The explicit key set is smaller and auditable.

### Dense rows are removed, not retokenized

Remove every `dense=True` from the remaining lists: Log tree, page lists, processing pickers, project
body lists, and workspace tiles. Row height and padding already come from the list theme and spacing
tokens, so no new token is needed. The baseline entries for dense rows are deleted.

*Risk:* longer lists scroll more. That is the intended reference density; the alternative is to keep
a non-standard row height, which the standard forbids.

## Risks / Trade-offs

- **A disabled action can hide why it is unavailable** → keep the field label or hint adjacent, and
  never replace a clear field with a disabled button alone. The rules only disable actions whose
  missing input is visible on the same surface.
- **Hiding the action row while a review form is open changes the card layout** → Cancel restores
  the row, and the form remains the focused surface. This is progressive disclosure, not removal.
- **The class-scope baseline stays above one for multi-dialog classes** → the new view-level test
  verifies the actual rule; the baseline remains a shrinking upper bound rather than a claim about
  one screen.
- **Removing dense rows can expose clipping at 1024x600** → the existing minimum-window test and a
  manual resize check cover the long lists.
- **Dialog controls need an explicit repaint** → update the dialog or control after changing
  `disabled`; tests exercise both the enabled and disabled transitions.

## Migration Plan

No data or storage migration. Roll back by reverting the UI change and restoring the baseline
entries in the same commit. The conformance baseline changes land with the migrations that remove
each violation.
