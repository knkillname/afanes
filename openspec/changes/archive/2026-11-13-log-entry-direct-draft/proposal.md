# Proposal

## Why

Creating a log entry from the calendar still opens a modal that asks for a title and a starter card,
even though the date already supplies the identity and a sensible title. This adds friction to the
most frequent Log action and makes an empty day feel like a form rather than a place to write. The
modal is also the only place where log template cards appear.

## What Changes

- Clicking an empty calendar day opens an unsaved log draft in the editor with a long-date default
  title instead of a title-and-card dialog.
- **Today's Entry** and the plus on an empty month or year row follow the same direct-draft path.
- The draft is written only when it has content; an untouched draft is discarded.
- An occupied date opens its existing entry in read mode, whether it was reached from the calendar,
  **Today's Entry**, or a month/year control.
- A **Starter** control in the new log draft lists the valid log cards and Empty. Choosing a card
  fills the draft body; invalid cards are reported inline. The old creation dialog is removed.
- New log drafts use a generated long date title: `November 13, 2026`, `November 2026`, or `2026`.
- A date change rewrites the heading only while it still equals the old generated date title. A
  custom heading is preserved.
- **BREAKING**: The dialog-facing `VaultPages.create_log_entry(date, title, scaffold)` helper is
  replaced by a draft-aware creation path that writes the draft text at the date path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `note-log`: dated actions open a draft instead of a dialog; occupied dates open read mode; the
  default date title and Starter control become part of the Log workflow.
- `template-cards`: the log creation picker becomes the Starter control in a new log draft; card
  bodies and Empty keep their current semantics.
- `note-editing`: a log draft uses the existing new-page rule, so it is written on first content and
  an untouched draft creates no file.
- `note-identity`: a log date change follows the new date only for the generated default heading;
  custom headings stay untouched.

## Impact

- UI: `ui/views/workspace.py`, `ui/views/page.py`, `ui/app.py`, `ui/components/template_cards.py`,
  `ui/state/navigation.py`, `ui/state/pages.py`, `ui/strings.py`.
- Core: `core/editing.py`, `core/log.py`, `core/vault/pages.py`, `core/vault/log_conversions.py`,
  `core/vault/naming.py`, `core/vault/naming_reports.py`.
- Tests: calendar, workspace, app, page, state, editing, log, naming, template-card, and copy tests.
- Documentation: the Log, workspace, page editing, template-card, and bundled guide pages.
- No new dependency, schema key, persistent index, or network behavior. The vault remains the source
  of truth and the existing atomic-write and path-containment rules apply.
