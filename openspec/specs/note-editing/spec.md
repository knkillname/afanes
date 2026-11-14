# note-editing Specification

## Purpose

Defines how a note is opened, read, created from a link, edited, saved, and removed as a page, and how internal links move between pages without changing the vault's file model.

## Requirements

### Requirement: A note opens as a page beside the Inbox

Selecting an Inbox note SHALL open it in a page pane beside the Inbox list. The page SHALL show its display title, its vault-relative path, and its Markdown body rendered read-only by default. Opening a page SHALL NOT write to the vault.

#### Scenario: Inbox selection opens the page

- **WHEN** the user selects an Inbox note
- **THEN** the page pane shows that note's display title, path, and rendered body

#### Scenario: Read mode performs no write

- **WHEN** a page is open in read mode
- **THEN** the file's content and modification time are unchanged

#### Scenario: Frontmatter is not body text

- **WHEN** a page with frontmatter is shown in read mode
- **THEN** the rendered body excludes the raw frontmatter block

#### Scenario: A note outside the Inbox opens the same way

- **WHEN** a link opens a note that is not under `inbox/`
- **THEN** the page shows that note even though the Inbox list continues to show only inbox notes

### Requirement: Internal links navigate from read mode

A tap on an internal reference in read mode SHALL resolve the destination against the current name catalog. A resolved reference SHALL open its target page. An unresolved reference SHALL open a new page draft for that reference. An ambiguous reference SHALL show every candidate and SHALL NOT choose one. External links, attachment destinations, and unsafe schemes SHALL remain inert.

#### Scenario: Resolved link opens its target

- **WHEN** the user taps `[Ada](note:Ada)` in read mode and exactly one note named `Ada` exists
- **THEN** the page pane opens that note

#### Scenario: Unresolved link starts a draft

- **WHEN** the user taps a `note:` reference that matches no page
- **THEN** a new page draft opens in edit mode for that reference name

#### Scenario: Ambiguous link asks

- **WHEN** two pages in the same scheme share the referenced name
- **THEN** the page pane lists both candidates and opens neither until one is chosen

#### Scenario: External link is inert

- **WHEN** the user taps an `https:`, `mailto:`, or attachment destination
- **THEN** no page opens, no note changes, and no external program is launched

#### Scenario: Unsafe scheme is inert

- **WHEN** the user taps a `javascript:` destination
- **THEN** no page opens and no note changes

### Requirement: New page type follows the project or note scheme

Creating a page from an unresolved reference SHALL derive its type and default folder from the
reference scheme: `note:` creates an uncategorized reference, `project:` creates a project, and
`log:` creates a log entry dated by the reference name. The draft SHALL open in edit mode with a
level-1 heading containing the reference name and an otherwise empty body.

#### Scenario: Note scheme creates an uncategorized reference

- **WHEN** the user creates a page from `note:Quarterly budget`
- **THEN** the draft has type `reference`, no category, and defaults to
  `reference/Quarterly budget.md`

#### Scenario: Project scheme creates a project

- **WHEN** the user creates a page from `project:Release 1.0`
- **THEN** the draft has type `project` and defaults to `projects/Release 1.0.md`

#### Scenario: Log scheme creates a log entry

- **WHEN** the user creates a page from `log:2025-10-12`
- **THEN** the draft has type `log`, date `2025-10-12`, and defaults to
  `log/2025/10/2025-10-12.md`

#### Scenario: Heading preserves the reference wording

- **WHEN** the user creates a page from `note:Q1: Planning?`
- **THEN** the draft heading reads `# Q1: Planning?` while the identity is `Q1 Planning`

### Requirement: A new page is written on first content

A new page draft SHALL NOT be written to the vault until it has body or label content. A draft
opened from a reference SHALL use the sanitized reference name as its identity; a log draft SHALL use
its ISO date. The first write SHALL use that exact identity or fail with an explanation, and an
untouched draft SHALL leave the vault unchanged.

#### Scenario: Untouched draft is discarded

- **WHEN** the user leaves a new draft without changing its body or labels
- **THEN** no file is created and no reference is rewritten

#### Scenario: First content writes the page

- **WHEN** the user types body text or changes a label in a new draft
- **THEN** the page is created on the next autosave or commit using the exact identity

#### Scenario: Exact identity is available

- **WHEN** the sanitized identity would collide with an existing file
- **THEN** the first write stops with an explanation and creates no suffixed name

#### Scenario: An untouched log draft writes nothing

- **WHEN** the user opens a log draft and leaves without changing its body or labels
- **THEN** no log file is created

#### Scenario: A log draft writes at its date

- **WHEN** the user types body text in a log draft dated `2025-10-12`
- **THEN** the file is written at `log/2025/10/2025-10-12.md`

#### Scenario: A starter selection is content

- **WHEN** the user chooses a starter card in a new log draft and changes nothing else
- **THEN** the next autosave or commit writes the entry with the starter body

#### Scenario: An occupied date refuses the first log write

- **WHEN** the log date becomes occupied before the draft's first write
- **THEN** no file is written, the draft remains, and the collision is reported

### Requirement: Unsafe reference names use the safe identity

When a page's sanitized identity differs from the reference name that opened it, the application SHALL create the page under the safe identity and, on the first write, preview every reference that still uses the unsafe name. The preview SHALL offer rewriting those references, keeping them unchanged, or cancelling the creation.

#### Scenario: Unsafe name is replaced

- **WHEN** `note:Q1: Planning?` is created as `Q1 Planning` and two references use the unsafe name
- **THEN** the preview reports both references and offers to rewrite them

#### Scenario: Keep leaves references unresolved

- **WHEN** the user chooses to keep the old references
- **THEN** the new page exists and the references remain unchanged and unresolved

#### Scenario: Cancel removes the new page

- **WHEN** the user cancels at the repair preview
- **THEN** the newly created page is removed and the draft is restored

#### Scenario: Rewrite preserves custom labels

- **WHEN** a reference uses a custom label and its destination is repaired
- **THEN** only the destination changes and the label is preserved

### Requirement: An existing safe page is reused

If the safe identity already belongs to a page in the same scheme, the application SHALL open that page and offer the repair instead of creating a second page.

#### Scenario: Existing safe page is reused

- **WHEN** a page named `Q1 Planning` already exists in the same scheme
- **THEN** the application opens that page and offers the repair instead of creating another page

### Requirement: The page edits the body and the label fields

Edit mode SHALL present the complete Markdown body, including its headings and steps, as raw text,
along with a label form for type, date, category, status, due date, requester, and owner. Date SHALL
be offered for every note. Category SHALL be offered only for references; due date, requester, and
owner only for projects; log SHALL offer none of those workflow labels. Status choices SHALL follow
the selected type. An invalid label value SHALL block the save and show an inline error.

#### Scenario: Body is raw Markdown

- **WHEN** the user edits a page
- **THEN** the body field contains the complete body, including its level-1 heading and steps

#### Scenario: Title is edited as the heading

- **WHEN** the user changes the first heading in the body
- **THEN** the display title changes after the body is saved

#### Scenario: Category is free form and limited to references

- **WHEN** the selected type is `reference`
- **THEN** the category field accepts any label
- **AND WHEN** the selected type is not `reference`
- **THEN** the category field is not offered

#### Scenario: Due date is limited to projects

- **WHEN** the selected type is `project`
- **THEN** the due date field is offered
- **AND WHEN** the selected type is not `project`
- **THEN** it is not offered

#### Scenario: Status follows the type

- **WHEN** the selected type changes so that the current status is invalid
- **THEN** the status is cleared before the change is saved

#### Scenario: Invalid due date is not written

- **WHEN** the due date field contains an invalid date
- **THEN** the save is blocked, an inline error is shown, and the note keeps its previous due date

#### Scenario: No people or project fields

- **WHEN** the edit form is shown
- **THEN** it offers no `people` or `project` label

#### Scenario: Steps are edited as body text

- **WHEN** the user edits a project
- **THEN** steps and their metadata are edited through the body field

#### Scenario: Date is offered on every note

- **WHEN** a note, reference, project, or log is edited
- **THEN** the Date field is offered

#### Scenario: Labels share the available width

- **WHEN** the page pane is wide enough for the visible label fields
- **THEN** Date is shown in the same row as the other visible labels

#### Scenario: Labels wrap on a narrow pane

- **WHEN** the page pane is too narrow for every visible label field
- **THEN** the fields wrap onto additional rows without horizontal scrolling

#### Scenario: The body fills the page pane

- **WHEN** the edit form is shown
- **THEN** the body field extends to the bottom of the available page pane
- **AND** its text starts at the top-left of the field

#### Scenario: Log offers no workflow labels

- **WHEN** a log entry is edited
- **THEN** category, status, due date, requester, and owner are not offered

#### Scenario: An invalid date shows a warning

- **WHEN** the Date field contains a malformed value
- **THEN** the warning from `note-model` is shown and the save is blocked until it is valid

### Requirement: The label form flows and fills the page pane

Edit mode SHALL lay out every visible label control, including the **Starter** control of a new log draft, in one adaptive flow. Visible controls SHALL share the available row width and grow to fill it. Controls SHALL wrap onto another row only when the pane cannot fit their minimum widths, without horizontal scrolling. The body field SHALL fill the remaining width and height below the label flow.

#### Scenario: Wide pane shares one row

- **WHEN** a new log draft is edited on a pane wide enough for three controls
- **THEN** Type, Date, and Starter share one row and grow to fill its width

#### Scenario: Starter keeps its guidance

- **WHEN** a new log draft shows the Starter control in the label flow
- **THEN** the selected card description and any invalid-card warning appear below the label flow

#### Scenario: Project labels share rows

- **WHEN** a project with every workflow label visible is edited on a wide pane
- **THEN** the visible label controls flow across the available rows and fill each row without fixed field widths

#### Scenario: Narrow pane wraps the flow

- **WHEN** the page pane cannot fit the visible label controls at their minimum widths
- **THEN** the remaining controls wrap onto another row without horizontal scrolling

#### Scenario: Body fills the detail width

- **WHEN** the edit form is shown in a detail card wider than the label minimums
- **THEN** the body field spans the full form width and extends to the bottom of the available pane

### Requirement: Category suggests existing labels while accepting new ones

Edit mode SHALL present the category as an editable combobox. Its suggestions SHALL be the distinct category labels already present on reference notes in the vault, sorted alphabetically and case-insensitively. Selecting a suggestion or typing a label that is not listed SHALL both be valid, and the existing category validation SHALL still apply.

#### Scenario: Existing labels are suggested

- **WHEN** the vault contains references under the `person` and `place` categories and a reference is edited
- **THEN** the category combobox offers `person` and `place`

#### Scenario: Typing filters the suggestions

- **WHEN** the user types part of a category name into the combobox
- **THEN** the suggestions are filtered to the labels that match, ignoring case

#### Scenario: A new label is accepted

- **WHEN** the user types a category that is not in the suggestions and confirms it
- **THEN** the reference receives that category and the note moves to the matching folder as before

#### Scenario: No existing labels yet

- **WHEN** the vault has no categorized reference notes and a reference is edited
- **THEN** the combobox offers no suggestions but still accepts a typed category

### Requirement: The page edits the project requester

Edit mode SHALL offer an `Asked by` field for projects. The field SHALL accept one line of text.
A non-blank value SHALL be trimmed and written as `asked_by`. A blank value SHALL remove the key.
Changing the note type away from `project` SHALL remove the key before saving. The write SHALL
preserve the body, unknown keys, and every other frontmatter value.

#### Scenario: The field is offered for projects

- **WHEN** the selected type is `project`
- **THEN** the `Asked by` field is offered

#### Scenario: The field is not offered for other types

- **WHEN** the selected type is `reference`, `note`, or `log`
- **THEN** the `Asked by` field is not offered

#### Scenario: A requester is written

- **WHEN** the user enters `Priya Nair` in the field and saves
- **THEN** the frontmatter contains `asked_by: Priya Nair`

#### Scenario: Clearing removes the key

- **WHEN** the user clears the field and saves
- **THEN** the `asked_by` key is removed and every other value is kept

#### Scenario: A type change clears the requester

- **WHEN** a project with `asked_by` is changed to a reference and saved
- **THEN** the `asked_by` key is removed

#### Scenario: The rest of the note is preserved

- **WHEN** the requester is set or cleared
- **THEN** the body, unknown frontmatter keys, and the newline style are unchanged

#### Scenario: The requester is not a link

- **WHEN** the user saves a requester
- **THEN** no body reference is created or rewritten

#### Scenario: A log never carries a requester

- **WHEN** a project with `asked_by` is changed to `log`
- **THEN** the `asked_by` key is removed before the save

### Requirement: The page edits the project owner

Edit mode SHALL offer an `Owner` field for projects. The field SHALL accept one line of text. A
non-blank value SHALL be trimmed and written as `owner`. A blank value SHALL remove the key.
Changing the note type away from `project` SHALL remove the key before saving. The write SHALL
preserve the body, unknown keys, and every other frontmatter value.

#### Scenario: The field is offered for projects

- **WHEN** the selected type is `project`
- **THEN** the `Owner` field is offered

#### Scenario: The field is not offered for other types

- **WHEN** the selected type is `reference`, `note`, or `log`
- **THEN** the `Owner` field is not offered

#### Scenario: An owner is written

- **WHEN** the user enters `Sam Rivera` in the field and saves
- **THEN** the frontmatter contains `owner: Sam Rivera`

#### Scenario: Clearing removes the key

- **WHEN** the user clears the field and saves
- **THEN** the `owner` key is removed and every other value is kept

#### Scenario: A type change clears the owner

- **WHEN** a project with `owner` is changed to a reference and saved
- **THEN** the `owner` key is removed

#### Scenario: The rest of the note is preserved

- **WHEN** the owner is set or cleared
- **THEN** the body, unknown frontmatter keys, and the newline style are unchanged

#### Scenario: A log never carries an owner

- **WHEN** a project with `owner` is changed to `log`
- **THEN** the `owner` key is removed before the save

### Requirement: Role name fields suggest vault names

The `Owner` and `Asked by` fields SHALL suggest matching `note:` names while the user types.
Selecting a suggestion SHALL fill the field with that name. Free text that matches no note SHALL
remain valid so a new person or team can be recorded before its note exists.

#### Scenario: Existing names are suggested

- **WHEN** the vault contains a note named `Sam Rivera` and the user types `Sam` in the Owner field
- **THEN** `Sam Rivera` is offered as a suggestion

#### Scenario: Typing filters the suggestions

- **WHEN** the user types part of a name
- **THEN** only the matching names are offered

#### Scenario: Free text is accepted

- **WHEN** the user types a name that matches no note and saves
- **THEN** the value is written unchanged as a broken role name

#### Scenario: No matches leaves no suggestions

- **WHEN** the user types a name that matches no note
- **THEN** no suggestion is shown and the field still accepts the text

### Requirement: Autosave and commit preserve the draft

A dirty edit draft SHALL be written to the vault roughly every 30 seconds and on Done, Back, or navigation. A new draft SHALL be created on its first write. Leaving edit mode SHALL commit the draft and SHALL NOT ask whether to save. A page in edit mode SHALL show whether a write is in progress and SHALL report a failed write without discarding the draft.

#### Scenario: Periodic autosave writes a dirty draft

- **WHEN** an edit draft has unsaved changes and the autosave interval elapses
- **THEN** the current body and labels are written to the vault

#### Scenario: Done commits

- **WHEN** the user finishes editing and returns to read mode
- **THEN** the draft is written before read mode is shown

#### Scenario: Back commits

- **WHEN** the user presses Back while a dirty draft is open
- **THEN** the draft is written before the previous page is shown

#### Scenario: Untouched new draft is discarded on Back

- **WHEN** the user presses Back on a new draft with no content
- **THEN** no file is created and the previous page is shown

#### Scenario: Failed write keeps the draft

- **WHEN** an autosave or commit fails
- **THEN** the draft remains in edit mode and a message reports the failure

### Requirement: External edits stop the write

Before every write, the application SHALL compare the file's current content with the content captured at the last read or write. If the content changed outside the application, the write SHALL be aborted, autosave SHALL stop, and the application SHALL offer to reload the file, overwrite it with the draft, recreate a moved or deleted file, or discard the draft. Leaving a conflicted draft SHALL require confirmation.

#### Scenario: External change stops autosave

- **WHEN** a file changes on disk after the page loaded and autosave is due
- **THEN** nothing is written, autosave stops, and the reload or overwrite choice is shown

#### Scenario: Reload replaces the draft

- **WHEN** the user chooses to reload
- **THEN** the draft is replaced by the current file content and the page returns to read mode

#### Scenario: Overwrite keeps the draft

- **WHEN** the user chooses to overwrite
- **THEN** the draft is written and the new content becomes the comparison baseline

#### Scenario: Moved or deleted file is reported

- **WHEN** the file no longer exists at its path
- **THEN** the application offers to recreate it from the draft or discard the draft

#### Scenario: Leaving a conflict asks first

- **WHEN** the user navigates away from an unresolved conflict
- **THEN** the application asks for confirmation and writes nothing without consent

### Requirement: Type changes preview stranded references

Changing a note's type can move it between the `note`, `project`, and `log` schemes. For a change
between `note` and `project`, the application SHALL list inbound references that will become
unresolved and SHALL require confirmation. A change to or from `log` SHALL rewrite inbound
references automatically as defined by `note-identity` and SHALL NOT use the stranded-reference
preview. A category change MUST NOT change resolution; it only moves the file.

#### Scenario: Scheme change is previewed

- **WHEN** a note referenced as `note:Prepare report` is changed to a project
- **THEN** the confirmation lists the notes whose `note:Prepare report` references will become
  unresolved

#### Scenario: Cancel restores the type

- **WHEN** the user cancels the type change confirmation
- **THEN** the original type is kept and nothing is written

#### Scenario: Same-scheme change needs no confirmation

- **WHEN** a note changes between `note` and `reference`
- **THEN** no inbound reference is stranded and no confirmation is required

#### Scenario: References are not retargeted

- **WHEN** the scheme change is confirmed
- **THEN** inbound references keep their original destinations and are reported as unresolved

#### Scenario: A category change keeps references

- **WHEN** a reference's category changes
- **THEN** its `note:` references still resolve and only its file location may change

#### Scenario: A log conversion rewrites without a preview

- **WHEN** a reference is changed to `log`
- **THEN** inbound references are rewritten and no stranded-reference preview is shown

#### Scenario: Leaving the log rewrites without a preview

- **WHEN** a log entry is changed to `reference` or `project`
- **THEN** inbound references are rewritten and no stranded-reference preview is shown

### Requirement: Broken notes open in raw rescue mode

A note whose frontmatter cannot be parsed SHALL be reachable from the failure report and from a link whose name matches the existing file. It SHALL open as raw text with the label form and derived title unavailable and a visible warning. Saving SHALL write exactly the edited text and SHALL NOT repair or reinterpret it. When the text parses, the page SHALL become a normal page on the next load or scan.

#### Scenario: Failure opens raw

- **WHEN** the user opens a note with malformed frontmatter
- **THEN** the page shows the complete raw file text and no label form

#### Scenario: Raw save writes as typed

- **WHEN** the user saves text that still does not parse
- **THEN** the file contains exactly the edited text and the page remains in rescue mode

#### Scenario: Parsing restores the normal page

- **WHEN** the edited text parses successfully
- **THEN** the next load shows the normal read mode with labels available

#### Scenario: Link does not duplicate a broken page

- **WHEN** a link's name matches an existing unparseable file
- **THEN** the application opens that file in rescue mode instead of creating a new page

### Requirement: Trash is immediate and undoable

Moving a page to trash SHALL take effect immediately and SHALL offer an Undo toast. Undo SHALL
restore the just-trashed note to its original path while that path is free. Undo MUST NOT overwrite
an occupied path; it SHALL report the collision and leave the note in trash. The undo opportunity
SHALL belong to the current session and SHALL end when the toast is dismissed or replaced.

#### Scenario: Trash moves immediately

- **WHEN** the user selects Trash for an open page
- **THEN** the page moves to trash without a confirmation surface

#### Scenario: Undo restores the note

- **WHEN** the user selects Undo on the trash toast while the original path is free
- **THEN** the note returns to its original path and the page history no longer points at the trash destination

#### Scenario: An occupied path is not overwritten

- **WHEN** the user selects Undo and the original path now belongs to another note
- **THEN** the application reports the collision, leaves the trashed note in trash, and writes nothing

#### Scenario: The undo opportunity is transient

- **WHEN** the trash toast is dismissed, replaced, or the application restarts
- **THEN** the page no longer offers undo for that trash action

### Requirement: The page offers rename and trash actions

The page SHALL offer Rename for active notes, references, and projects, and hide it for log entries.
An active note SHALL offer Trash for every type; a trashed note is read-only and offers Restore and
Delete Permanently instead. Rename SHALL use the preview, confirmation, atomic-write, and
inbound-reference rules, and SHALL update a level-1 heading only when its text matches the old
identity. After a rename or trash, the page history SHALL not return to a path that no longer exists.

#### Scenario: Rename previews affected references

- **WHEN** the user requests a rename from the page
- **THEN** the application reports the affected note and reference counts before asking for
  confirmation

#### Scenario: Matching heading follows the identity

- **WHEN** a note's first heading text equals its old identity and the note is renamed
- **THEN** the heading is updated to the new identity

#### Scenario: Custom heading is preserved

- **WHEN** a note's first heading differs from its old identity and the note is renamed
- **THEN** the heading is unchanged

#### Scenario: Trash does not preview inbound references

- **WHEN** the user requests trash from the page
- **THEN** the application moves the note immediately and does not report the destination or inbound references first

#### Scenario: History skips the removed path

- **WHEN** the current page is renamed or trashed
- **THEN** Back opens the previous page and never the old path

#### Scenario: A log entry has no Rename action

- **WHEN** a log entry is open
- **THEN** the page offers no Rename action

#### Scenario: A log entry can be trashed

- **WHEN** a log entry is open
- **THEN** the page offers the Trash action

#### Scenario: A trashed note is not an active page

- **WHEN** a trashed note is open
- **THEN** the page offers Restore and Delete Permanently instead of Rename and Move to Trash

### Requirement: One history covers list clicks and link taps

The application SHALL keep one bounded page history for every page opened from the Inbox list or from a link. Back SHALL return to the previous page in that history. At the beginning of the history, Back SHALL show the empty page pane. The history SHALL NOT grow without bound.

#### Scenario: List clicks share the history

- **WHEN** the user opens notes A, then B, then C from the Inbox list and presses Back
- **THEN** the page pane shows B

#### Scenario: Link taps join the same history

- **WHEN** the user follows a link from C to D and presses Back
- **THEN** the page pane shows C

#### Scenario: Oldest entry returns to empty

- **WHEN** the user presses Back on the oldest history entry
- **THEN** the page pane shows no page

#### Scenario: History is bounded

- **WHEN** the user opens more pages than the history limit
- **THEN** the oldest entries are dropped and the history remains bounded

### Requirement: Steps render as structured rows

Read mode SHALL render a project body as ordered prose blocks and task-list blocks. A task-list block SHALL render as an accent-tinted card of step rows showing checked state, text, owners, plan and actual dates, and tags. The metadata comment SHALL be hidden from rendered text. Ticking or unticking a step SHALL rewrite only that line atomically.

#### Scenario: A step shows its metadata

- **WHEN** a step declares owners, dates, and tags
- **THEN** the row shows them as labels rather than raw syntax

#### Scenario: Prose and steps keep document order

- **WHEN** a project body contains prose before and after a task list
- **THEN** the page shows the prose, the step card, and the following prose in body order

#### Scenario: A contiguous task list is one card

- **WHEN** a project body contains several task list items separated only by blank lines
- **THEN** the page groups them into one step card

#### Scenario: Unsupported body shape falls back to Markdown

- **WHEN** a task list cannot be separated into step rows without changing the surrounding Markdown
- **THEN** that block renders as ordinary Markdown and no content is dropped or rewritten

#### Scenario: The comment is hidden

- **WHEN** a project body is rendered
- **THEN** the metadata comment does not appear as body text

#### Scenario: Ticking a step updates the line

- **WHEN** the user ticks a step in read mode
- **THEN** the checkbox and its `actual` date are written and the rest of the file is unchanged

#### Scenario: Unticking removes the actual date

- **WHEN** the user unticks a step
- **THEN** `actual` is removed and `plan` is kept

### Requirement: Step row text is rendered Markdown

Step row text SHALL render inline Markdown, including internal references. A tap on an internal reference in a step row SHALL follow the existing read-mode navigation rules. External, attachment, and unsafe destinations SHALL remain inert.

#### Scenario: A link in a step row opens its target

- **WHEN** a step row contains `[Sam Rivera](<note:Sam Rivera>)` and exactly one note named `Sam Rivera` exists
- **THEN** tapping the label opens that note

#### Scenario: An ambiguous step link asks

- **WHEN** two notes share the referenced name
- **THEN** the page lists both candidates and opens neither until one is chosen

#### Scenario: An external step link is inert

- **WHEN** a step row contains an `https:` or attachment link
- **THEN** no page opens and no external program is launched

### Requirement: Step rows expose plan and owner actions

Every step row SHALL expose a calendar action and a person action. The calendar action SHALL set or clear the step's plan date. The person action SHALL manage the complete owner list. Both actions SHALL be present but muted at rest, SHALL become emphasized on hover or keyboard focus, and SHALL remain reachable on touch devices.

#### Scenario: The plan date is set

- **WHEN** the user chooses a date from a step's calendar action
- **THEN** that step's `plan` is written as the chosen calendar date

#### Scenario: The plan date is cleared

- **WHEN** the user clears a step's plan date
- **THEN** the `plan` key is removed and the rest of the metadata is kept

#### Scenario: An owner is added

- **WHEN** the user adds `Sam Rivera` through a step's person action
- **THEN** `Sam Rivera` joins the step's owners and the step leaves the user's own list

#### Scenario: An owner is removed

- **WHEN** the user removes the last owner through a step's person action
- **THEN** the `owners` key is removed and the step becomes the user's own work again

#### Scenario: Multiple owners are managed

- **WHEN** the user adds, removes, and re-adds names through the person action
- **THEN** the written owner list contains exactly the names shown in the panel, in their shown order

#### Scenario: Actions are reachable without hover

- **WHEN** the pointer is not over a step row
- **THEN** both actions remain visible at reduced emphasis and remain reachable by keyboard focus and touch

#### Scenario: A failed write keeps the old metadata

- **WHEN** a plan or owner write fails
- **THEN** the page reports the failure and the step keeps its previous metadata

### Requirement: Project page shows status and due date

Read mode SHALL show a project meta row under the page title with its status and optional due date. The due date SHALL expose a calendar action that sets or clears it. The action SHALL be present but muted at rest and emphasized on hover or keyboard focus. The due-date field SHALL remain available in edit mode.

#### Scenario: The due date is shown

- **WHEN** a project declares `due_date: 2026-12-01`
- **THEN** the meta row shows that date

#### Scenario: A project without a due date offers the action

- **WHEN** a project has no due date
- **THEN** the meta row shows the add-date action and no date

#### Scenario: The due date is set from read mode

- **WHEN** the user chooses a date from the project meta row
- **THEN** the project frontmatter is written with that due date and the body is unchanged

#### Scenario: The due date is cleared

- **WHEN** the user clears the project due date
- **THEN** the `due_date` key is removed and the body is unchanged

#### Scenario: An invalid due date is rejected

- **WHEN** a due-date write would contain an invalid calendar date
- **THEN** nothing is written and the meta row reports the problem

#### Scenario: Non-project pages have no project meta row

- **WHEN** a note or reference is open in read mode
- **THEN** no project status or due-date control is shown

### Requirement: The project meta row shows the requester

Read mode SHALL show `Owner <name>` and `Asked by <name>` in the project meta row when the project
declares `owner` or `asked_by`, in that order. The row SHALL omit each label when its key is absent.
Each name SHALL be a navigation control that follows the role-name navigation rules. The file values
SHALL remain plain text.

#### Scenario: A project with a requester shows it

- **WHEN** a project declares `asked_by: Priya Nair`
- **THEN** the meta row shows `Asked by Priya Nair`

#### Scenario: A project without a requester omits the label

- **WHEN** a project has no `asked_by` key
- **THEN** the meta row shows no requester label

#### Scenario: Non-project pages show no requester

- **WHEN** a reference or capture is open in read mode
- **THEN** no requester label is shown

#### Scenario: Viewing the requester writes nothing

- **WHEN** the project meta row is shown
- **THEN** no note file is created, changed, or removed

#### Scenario: A project with an owner shows it

- **WHEN** a project declares `owner: Sam Rivera`
- **THEN** the meta row shows `Owner Sam Rivera`

#### Scenario: Owner is shown before requester

- **WHEN** a project declares both `owner` and `asked_by`
- **THEN** the meta row shows the owner before the requester

#### Scenario: A project without an owner omits the label

- **WHEN** a project has no `owner` key
- **THEN** the meta row shows no owner label

#### Scenario: A resolved role name opens its page

- **WHEN** the user selects a role name that resolves to exactly one note
- **THEN** that note opens

#### Scenario: A missing role name starts creation

- **WHEN** the user selects a role name that matches no note
- **THEN** the missing-role-name creation flow starts

### Requirement: Read mode sets the project roles

Read mode SHALL offer an owner action and a requester action for projects. Each action SHALL ask for a
name with vault-name suggestions, accept a new name, and write it immediately without entering edit
mode. Each action SHALL also offer clearing the role. Cancelling SHALL write nothing, and a successful
change SHALL refresh the page, its role links, and its Connections.

#### Scenario: The owner action writes a name

- **WHEN** the reader selects the owner action, types `Sam Rivera`, and confirms
- **THEN** the project frontmatter contains `owner: Sam Rivera` without entering edit mode

#### Scenario: The requester action writes a name

- **WHEN** the reader selects the requester action, types `Priya Nair`, and confirms
- **THEN** the project frontmatter contains `asked_by: Priya Nair` without entering edit mode

#### Scenario: A typed name that matches no note is still written

- **WHEN** the reader types `Min` in the requester action without choosing a suggested note, and confirms
- **THEN** `asked_by: Min` is written and the page shows `Min` as a broken role link

#### Scenario: A role is cleared

- **WHEN** the reader selects the clear action in the owner or requester dialog
- **THEN** the corresponding key is removed and the page refreshes

#### Scenario: Cancelling writes nothing

- **WHEN** the reader cancels the owner or requester dialog
- **THEN** no file is created, changed, or removed

#### Scenario: The actions are project-only

- **WHEN** a reference, capture, or log entry is open in read mode
- **THEN** neither role action is shown

### Requirement: Role names navigate from read mode

A project role name shown in read mode SHALL act as a navigation control. A resolved name SHALL open
its page. An ambiguous name SHALL show every candidate and SHALL NOT choose one. A missing name SHALL
start the missing-role-name creation flow. A role name is not a body link and SHALL NOT change the
body navigation rules.

#### Scenario: A resolved role name opens its page

- **WHEN** the user selects `Sam Rivera` in the project meta row and exactly one note is named
  `Sam Rivera`
- **THEN** that note opens

#### Scenario: An ambiguous role name asks

- **WHEN** two notes are named `Sam Rivera`
- **THEN** the page lists both candidates and opens neither until one is chosen

#### Scenario: A missing role name starts creation

- **WHEN** the user selects `Sam Rivera` and no note has that name
- **THEN** the missing-role-name creation flow starts

#### Scenario: Viewing role names writes nothing

- **WHEN** a role name is shown or selected in read mode
- **THEN** no note file is created, changed, or removed until the user confirms creation

### Requirement: A missing role name creates a categorized reference

The missing-role-name flow SHALL ask for a category in an editable combobox. Suggestions SHALL always
include `person`, every category used by a reference note, and every category offered by a valid
reference template card. A free-typed label and no category SHALL remain available, and suggestions
SHALL ignore the browser query and active section. Confirming SHALL create the reference atomically
under the chosen category and open it in edit mode; cancelling SHALL write nothing.

#### Scenario: Person is always suggested

- **WHEN** the vault has no reference with `category: person`
- **THEN** `person` is offered in the category suggestions

#### Scenario: Template categories are suggested

- **WHEN** the vault contains a valid reference template card with `category: team`
- **THEN** `team` is offered even when no reference uses it yet

#### Scenario: Search does not hide categories

- **WHEN** the browser search query matches no note in an existing category
- **THEN** that category is still offered

#### Scenario: A category is chosen

- **WHEN** the user chooses the `person` category for `Sam Rivera`
- **THEN** a reference named `Sam Rivera` is created under `reference/person/` and opens

#### Scenario: No category is chosen

- **WHEN** the user chooses no category for `Sam Rivera`
- **THEN** an uncategorized reference named `Sam Rivera` is created under `reference/` and opens

#### Scenario: A new category is typed

- **WHEN** the user types a category that is not in the suggestions
- **THEN** the new reference uses that category and its folder

#### Scenario: Creating and opening are one action

- **WHEN** the user confirms the category choice
- **THEN** the note is written immediately and opens in edit mode; no draft save step is required

#### Scenario: The new reference stays responsive

- **WHEN** the created role reference is open in edit mode
- **THEN** choosing **Done** returns to read mode
- **AND** the Back action remains available and returns to the previous page

#### Scenario: Cancelling writes nothing

- **WHEN** the user cancels the category choice
- **THEN** no note is created, changed, or removed

#### Scenario: A collision is reported

- **WHEN** the role name already belongs to a note in the `note:` scheme
- **THEN** no second note is created without an explicit resolution

### Requirement: A role reference uses the matching template

When a valid reference template card exists for the chosen category, the created role reference SHALL
include that card's starter body below the role-name heading. When no card matches, the note SHALL
contain only the heading.

#### Scenario: The matching card supplies the body

- **WHEN** the vault has a valid `person` card and the user chooses `person`
- **THEN** the new reference contains the card's `## Contact` body below `# Sam Rivera`

#### Scenario: No card leaves only the heading

- **WHEN** the chosen category has no matching template card
- **THEN** the new reference contains the role-name heading and no starter body

### Requirement: Step owner names navigate as role names

Every step owner name shown in read mode SHALL follow the role-name navigation rules, including the
owner panel chips and the step detail line. Selecting a name SHALL NOT remove it from the step; the
chip's delete action SHALL remain a separate control.

#### Scenario: A step owner name opens its page

- **WHEN** a step declares `owners: [Sam Rivera]` and exactly one note is named `Sam Rivera`
- **THEN** selecting the name opens that note

#### Scenario: A missing step owner name starts creation

- **WHEN** a step declares `owners: [Sam Rivera]` and no note has that name
- **THEN** selecting the name starts the missing-role-name creation flow

#### Scenario: Deleting a chip still removes the owner

- **WHEN** the user activates the chip's delete action
- **THEN** the owner is removed from the step and no page is opened

### Requirement: An open page follows an external edit

While a page is open, a change made to its file outside the application SHALL be detected without a manual refresh. A page with no unsaved changes SHALL reload the new content; a page with unsaved edits SHALL raise the existing conflict state instead of replacing the draft.

#### Scenario: A clean page reloads

- **WHEN** the open page's file changes on disk and the draft has no unsaved changes
- **THEN** the page shows the current file content without the user asking for a reload

#### Scenario: A dirty draft is kept

- **WHEN** the open page's file changes on disk while the draft has unsaved edits
- **THEN** the draft is kept and the reload, overwrite, or discard choice is offered

#### Scenario: A deleted page is reported

- **WHEN** the open page's file is removed outside the application
- **THEN** the page reports that the file is missing and offers to recreate it or discard the draft

#### Scenario: The application's own write does not conflict

- **WHEN** the application writes the open page itself
- **THEN** no conflict is raised and the page shows the written content

#### Scenario: Resolution keeps its meaning

- **WHEN** the user resolves a conflict raised by an external edit
- **THEN** the reload, overwrite, recreate, and discard actions behave as before

### Requirement: Read mode shows the note date

Read mode SHALL show the note's `date` in the page meta row for every note. A project SHALL also show
its `due_date` as a separate value. A missing date SHALL show an add-date action, and a malformed
date SHALL show the warning defined by `note-model`.

#### Scenario: A dated note shows its date

- **WHEN** a note declares `date: 2025-10`
- **THEN** the meta row shows `2025-10`

#### Scenario: A project shows both dates

- **WHEN** a project declares `date: 2025-10` and `due_date: 2026-01-15`
- **THEN** the meta row shows both values with distinct labels

#### Scenario: A missing date offers an action

- **WHEN** a note has no `date`
- **THEN** the meta row shows the add-date action and no date

#### Scenario: A malformed date shows a warning

- **WHEN** a note declares `date: last Tuesday`
- **THEN** the meta row reports the invalid value

### Requirement: Read mode ends with the Connections section

Read mode SHALL place the Connections section after the rendered body of a parsed note. The section SHALL NOT appear
in edit mode or in raw rescue mode, and rendering it MUST NOT write to the vault or change the body text.

#### Scenario: Connections follow the body

- **WHEN** a parsed note with connections opens in read mode
- **THEN** the Connections section appears after the rendered body

#### Scenario: Edit mode hides connections

- **WHEN** the reader starts editing the open page
- **THEN** the Connections section is not shown

#### Scenario: Raw rescue hides connections

- **WHEN** a note opens in raw rescue mode
- **THEN** the Connections section is not shown

#### Scenario: Showing connections writes nothing

- **WHEN** read mode renders the section
- **THEN** no note file is created, changed, moved, or removed
