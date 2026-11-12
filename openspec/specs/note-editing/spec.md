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

A new page draft SHALL NOT be written to the vault until it has body or label content. Its identity SHALL be the sanitized reference name, and the first write SHALL use that exact identity or fail with an explanation.

#### Scenario: Untouched draft is discarded

- **WHEN** the user leaves a new draft without changing its body or labels
- **THEN** no file is created and no reference is rewritten

#### Scenario: First content writes the page

- **WHEN** the user types body text or changes a label in a new draft
- **THEN** the page is created on the next autosave or commit using the exact identity

#### Scenario: Exact identity is available

- **WHEN** the sanitized identity would collide with an existing file
- **THEN** the first write stops with an explanation and creates no suffixed name

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

### Requirement: The page edits the body and the four labels

Edit mode SHALL present the complete Markdown body, including its headings and steps, as raw text,
along with a label form for type, date, category, status, due date, and requester. Date SHALL be
offered for every note. Category SHALL be offered only for references; due date and requester only
for projects; log SHALL offer none of them. Status choices SHALL follow the selected type. An invalid
label value SHALL block the save and show an inline error.

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

#### Scenario: Log offers no workflow labels

- **WHEN** a log entry is edited
- **THEN** category, status, due date, and requester are not offered

#### Scenario: An invalid date shows a warning

- **WHEN** the Date field contains a malformed value
- **THEN** the warning from `note-model` is shown and the save is blocked until it is valid

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

### Requirement: Rename and trash are available from the page

The page SHALL offer Rename for notes, references, and projects, and SHALL hide it for log entries.
The page SHALL offer Trash for every type. Rename SHALL use the existing preview, confirmation,
atomic-write, and inbound-reference rules. Rename SHALL update a level-1 heading only when its text
matches the old identity. After a rename or trash, the page history SHALL be updated so Back never
returns to a path that no longer exists.

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

#### Scenario: Trash previews inbound references

- **WHEN** the user requests trash from the page
- **THEN** the application reports the destination and inbound references before confirmation

#### Scenario: History skips the removed path

- **WHEN** the current page is renamed or trashed
- **THEN** Back opens the previous page and never the old path

#### Scenario: A log entry has no Rename action

- **WHEN** a log entry is open
- **THEN** the page offers no Rename action

#### Scenario: A log entry can be trashed

- **WHEN** a log entry is open
- **THEN** the page offers the Trash action

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

Read mode SHALL show `Asked by <name>` in the project meta row when the project declares
`asked_by`. The row SHALL omit the label when the key is absent. The value SHALL be displayed as
plain text and SHALL NOT add a navigation control.

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
