# Proposal

## Why

The workspace now follows the reference palette, surfaces, typography, and adaptive layout, but its
controls still behave one wave behind. An action that cannot succeed from the current input stays
enabled and reports an error after the click; several views show more than one accent-filled action;
inline confirmations put the affirmative control before Cancel; and non-header buttons still combine
icons with labels. The interface standard already names these as wave 2, and the conformance baseline
records them as debt.

## What Changes

- **Unavailable actions are insensitive.** Capture, Processing Preview, Create Vault, New Reference,
  Rename, and Add Step disable their affirmative control until the current input can succeed. The
  command-level rejection stays as a guard for direct calls, but the interface no longer invites a
  click that must fail.
- **One suggested action per rendered view.** Welcome keeps one accent-filled action: Choose Vault on
  the desktop and Open in the browser presentation. New Vault becomes a regular button. The page
  conflict panel, rename panel, repair panel, and Processing plan keep one suggested or destructive
  control. New view-level tests count visible suggested and destructive controls instead of relying
  only on the class-scope baseline.
- **Cancel first.** Every inline confirmation panel orders Cancel before the affirmative action, as
  the existing dialogs already do.
- **Header buttons may combine icon and label.** The conformance gate stops flagging icon-plus-label
  inside a header bar and keeps requiring one or the other elsewhere. Header buttons are identified
  explicitly so the exception cannot spread by accident.
- **List rows use the standard height.** Remove `dense=True` from the remaining lists and delete
  those baseline entries.
- **The baseline only shrinks.** Every migration deletes its baseline entry in the same change; no
  new entry is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-theme`: adds the insensitive-action and cancel-first rules, makes the header-bar
  exception for icon-plus-label buttons explicit, and requires the standard list-row height.
- `inbox-capture`: an empty composer makes Capture insensitive; a direct blank submission is still
  rejected without writing.
- `guided-review`: a blank next-step form makes Add Step insensitive; a direct blank submission is
  still rejected without writing.
- `vault-browsing`: a blank name makes New Reference's Create action insensitive; the creation
  command still rejects a blank name.
- `processing`: Preview is insensitive until the selected outcome and its required fields are valid.

## Impact

- UI: `views/inbox.py`, `views/workspace.py`, `views/page.py`, `views/processing.py`,
  `views/review.py`, and `app.py` for the dialog submits. Shared panels and status components may
  change order or spacing. No Markdown parsing, vault I/O, or state ownership moves.
- Tests: `tests/ui/test_conformance.py` and the affected view tests, plus a new view-level control
  hierarchy test. The conformance baseline shrinks.
- Docs: `docs/develop/interface-standard.md` records wave 2 as landed and the corrected gate scope.
- No core, model, CLI, dependency, storage, or vault-format change. No new runtime network access.
