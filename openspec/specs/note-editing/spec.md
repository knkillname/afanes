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

Creating a page from an unresolved reference SHALL derive its type and default folder from the reference scheme: `note:` creates an uncategorized reference and `project:` creates a project. The draft SHALL open in edit mode with a level-1 heading containing the reference name and an otherwise empty body.

#### Scenario: Note scheme creates an uncategorized reference

- **WHEN** the user creates a page from `note:Quarterly budget`
- **THEN** the draft has type `reference`, no category, and defaults to `reference/Quarterly budget.md`

#### Scenario: Project scheme creates a project

- **WHEN** the user creates a page from `project:Release 1.0`
- **THEN** the draft has type `project` and defaults to `projects/Release 1.0.md`

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

Edit mode SHALL present the complete Markdown body, including its headings and steps, as raw text, along with a label form for type, category, status, and due date. Category SHALL be offered only for references and due date only for projects. Status choices SHALL follow the selected type. An invalid label value SHALL block the save and show an inline error.

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

Changing a note's type can move it between the `note` and `project` schemes. Before applying such a change, the application SHALL list the inbound references that will become unresolved and SHALL require confirmation. A category change MUST NOT change resolution; it only moves the file.

#### Scenario: Scheme change is previewed

- **WHEN** a note referenced as `note:Prepare report` is changed to a project
- **THEN** the confirmation lists the notes whose `note:Prepare report` references will become unresolved

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

The page SHALL offer rename and trash actions that use the existing preview, confirmation, atomic-write, and inbound-reference rules. Rename SHALL update a level-1 heading only when its text matches the old identity. After a rename or trash, the page history SHALL be updated so Back never returns to a path that no longer exists.

#### Scenario: Rename previews affected references

- **WHEN** the user requests a rename from the page
- **THEN** the application reports the affected note and reference counts before asking for confirmation

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

Read mode SHALL render a project's steps as rows showing the step text, checked state, owners, plan and actual dates, and tags. The metadata comment SHALL be hidden from the rendered text. Ticking or unticking a step SHALL rewrite only that line atomically.

#### Scenario: A step shows its metadata

- **WHEN** a step declares owners, dates, and tags
- **THEN** the row shows them as labels rather than raw syntax

#### Scenario: The comment is hidden

- **WHEN** a project body is rendered
- **THEN** the metadata comment does not appear as body text

#### Scenario: Ticking a step updates the line

- **WHEN** the user ticks a step in read mode
- **THEN** the checkbox and its `actual` date are written and the rest of the file is unchanged

#### Scenario: Unticking removes the actual date

- **WHEN** the user unticks a step
- **THEN** `actual` is removed and `plan` is kept

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
