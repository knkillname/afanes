# Design

## Context

See `proposal.md` for motivation. The current Log path is:

```
empty day / Today / month-year plus
    -> AppShell.show_log_entry_dialog
    -> title + starter card dialog
    -> Navigation.open_or_create_log_entry
    -> VaultPages.create_log_entry writes the file
    -> page loads in edit mode

day with one entry -> WorkspaceView._select -> page loads in read mode
```

The page editor already has a new-draft lifecycle: `PageEditorState.commit` discards a clean new
draft, and `_create_new_page` writes a dirty draft on its first save. Reference and project drafts
use `NormalDraft.new`; log drafts do not exist yet. `TemplateCardPicker` already provides the card
ordering, Empty option, duplicate-title handling, descriptions, and invalid-card warning used by the
reference, processing, and log dialogs.

`NoteDate` carries ISO identity only. `core/log.py` owns the Log timeline and calendar and is the
natural home for a shared default-title formatter. Log date changes are planned by
`LogConversions.plan_log_date_change`, shaped as a `RenamePreview`, and applied by
`VaultNaming.apply_rename`; `_write_conversion` writes the new date/type before the move, and
`heading_update` is currently always false for a date change.

## Goals / Non-Goals

**Goals:**

- Make every empty dated action open an unsaved log draft in the editor.
- Keep an occupied date in read mode.
- Give new entries a generated long-date title and let the user edit it.
- Preserve log card choice without a creation dialog.
- Make a generated heading follow a date change while a custom heading stays put.
- Keep browsing and untouched drafts write-free.

**Non-Goals:**

- No change to the reference or processing template pickers.
- No new frontmatter key, schema version, or title-provenance marker.
- No change to log card files, their format, or the eight seeded cards.
- No localization of month names; the internationalization change owns that.
- No fix for the existing gap where a missing `log:` link opens a reference draft. That behavior can
  reuse the new constructor in a separate change.
- No persistent index and no new dependency.

## Decisions

### Log drafts use the existing new-page lifecycle

`NormalDraft` gains a log constructor that builds an unwritten draft with:

- identity `date.text`;
- body `# <default title>\n\n`;
- `type: log` and `date` labels;
- a `NoteDocument` source carrying the same type and date.

`PageEditorState` gains a `start_log_draft` command that installs that draft in edit mode.
`PageNavigator` wraps it with the existing commit, history, and command-lock behavior. When the
draft first becomes dirty, `_create_new_page` detects `NoteType.LOG` and writes the draft text at the
date path instead of calling the reference/project `create_page` path.

`VaultPages.create_log_entry(date, title, scaffold)` is replaced by a draft-text creation method
that validates the exact text, checks the log namespace and target path, and writes atomically. The
draft remains the source of the body; the core method does not rebuild it from a title and scaffold.

**Alternatives considered:** writing the file on the click (rejected: accidental calendar clicks
would leave empty entries and it conflicts with the existing new-page rule); keeping the dialog with
a prefilled title (rejected: the request removes the dialog).

### One AppShell handler routes every dated action

`WorkspaceView` keeps the existing `on_log_entry(date)` callback for an empty day, **Today's
Entry**, and the month/year plus controls. `AppShell` replaces `show_log_entry_dialog` with a
handler that:

1. asks the snapshot for a log entry at the date;
2. opens it with `open_page` when one exists, which is read mode;
3. otherwise loads the template-card listing and calls the new `start_log_draft` command.

A day with one entry already opens through `_select`; a day with several entries keeps the tree
expansion. **Today's Entry** and the month/year plus controls use the same handler, so an occupied
date opens read mode there too.

**Alternatives considered:** separate callbacks for the calendar and the buttons (rejected: it
reintroduces the current read/edit inconsistency); keeping `open_or_create_log_entry` and adding a
draft mode flag (rejected: two creation paths with different write timing).

### The Starter control reuses TemplateCardPicker in the editor

`PageEditorState` holds a small `LogDraftStarter` value object with the valid cards, issues, selected
card, and the generated body for the current selection. `PageView` adds the existing
`TemplateCardPicker` for `TemplateCardContext.LOG` above the body field in the edit form.

The control is visible only when all of these are true:

- the page is an unwritten log draft;
- a starter listing is present;
- the body equals the generated heading plus the selected starter.

The last check means the control disappears as soon as the user types content beyond the generated
body. Selecting a card replaces the generated body with the heading plus that card's body; selecting
Empty restores the heading only. The selection makes the draft dirty, so the next autosave or commit
writes it. The existing picker supplies the Empty option, title ordering, duplicate-title suffixes,
descriptions, and the invalid-card warning.

**Alternatives considered:** an inline page menu or a separate dialog (rejected: a dialog returns
the surface the change removes, and a menu hides the card descriptions); applying a card after the
user has typed (rejected: it would overwrite content or require a destructive confirmation).

### A shared `LogTitle` value object owns the default title

`core/log.py` gains a frozen `LogTitle` value object with a `for_date` factory and a `text` property.
It formats `November 13, 2026`, `November 2026`, or `2026` using the standard library month names.
The AppShell uses it for a new draft, and `LogConversions` uses it to compare and replace a generated
heading.

**Alternatives considered:** a UI-only formatter (rejected: core date changes must compare the same
text); ISO titles (rejected by the product choice); weekday titles (rejected: more formatting surface
without a product need).

### Date changes rewrite only the generated heading

`RenamePreview` gains `new_heading: str | None`. `plan_log_date_change` compares the note's current
title with `LogTitle.for_date(note.date).text`:

- equal: set `new_heading` to the new date's title;
- different: leave `new_heading` as `None`.

`_write_conversion` applies the new date/type and, when present, `new_heading` in the same atomic
write before the move. The existing `heading_update` path remains false for conversions. This avoids
the post-conversion hash mismatch that would occur if the ordinary heading-update pass ran after the
date was written. Ordinary renames keep using `new_name` as their heading text.

A dirty log draft is committed before its date change is planned, so the preview sees the current
body and the change does not discard unsaved edits.

**Alternatives considered:** always preserving the heading (rejected by the product choice); always
rewriting it (rejected: it destroys custom headings); adding a frontmatter provenance key (rejected:
new schema surface for a behavior the matching heuristic already covers).

### Dialog copy is removed and the first-write error remains

The log dialog strings for its title, body, submit action, and blank-title error are removed, and the
copy gate's classification is updated. The first-write failure notice remains, with wording about
writing rather than creating, and is shown as a transient toast. The editor opening is the success
signal, so no success toast is added.

## Risks / Trade-offs

- **A draft is invisible in the calendar until its first write.** → The editor is visibly open; an
  untouched draft is intentionally discarded and creates no file. The docs state the rule.
- **Choosing a starter writes on the next autosave even if the user only wanted to preview it.** →
  Choosing a card is explicit content; Empty restores the heading before any write, and the control
  hides once the user types beyond the generated body.
- **The Starter control can make the edit form taller.** → It appears only for a new log draft and
  disappears after user content; the existing picker description and warning are compact captions.
- **A date-shaped custom heading is indistinguishable from a generated one.** → The matching
  heuristic updates it; a heading in any other form is preserved. This is the same rule ordinary
  renames use.
- **Month names are English until localization lands.** → `LogTitle` is one shared source, so the
  internationalization change can replace its formatting without touching the creation or date-change
  call sites.
- **Removing `create_log_entry` is a breaking internal API change.** → Update every caller and test
  in this change; record the replacement in the changelog.

## Migration Plan

No vault migration or schema change is required. Existing log entries keep their headings and
content. New drafts use the new title only after they are written. Rolling back leaves every written
entry as an ordinary log note because no new frontmatter key or file format is introduced.

Implementation lands with the delta specs, updated tests, the Log guide, workspace and page-editing
docs, the template-card reference, and the bundled guide. The change is released under `Unreleased`
unless the archive completes a larger milestone.

## Open Questions

None. The Starter placement, invalid-card reporting, and date-change behavior are settled above.
