# inbox-capture Specification

## Purpose

Defines how a raw thought becomes a note in the vault's inbox folder, how that folder is listed and ordered, and how a note is previewed and reported without editing it.

## Requirements

### Requirement: Capture writes a note into the inbox

Capturing text SHALL create a Markdown note under the vault's `inbox/` directory, creating the directory when missing. The note SHALL declare `type: note` and MUST NOT declare `status`. A successful capture SHALL clear the composer for the next thought.

#### Scenario: Capture creates a note

- **WHEN** the user captures `Buy milk`
- **THEN** `inbox/Buy milk.md` exists with `type: note`

#### Scenario: No status is written

- **WHEN** a captured note is created
- **THEN** its frontmatter has no `status` key

#### Scenario: Inbox directory is created on demand

- **WHEN** the vault has no `inbox/` directory and the user captures
- **THEN** the directory is created and the note is written

#### Scenario: Empty capture is rejected

- **WHEN** the captured text is empty or whitespace-only
- **THEN** no file is created and the composer reports that a thought is required

#### Scenario: Successful capture clears the composer

- **WHEN** the capture is written
- **THEN** the composer is empty and ready for another thought

### Requirement: The filename comes from the first non-blank line

The filename stem SHALL be the first non-blank line of the captured text, processed by the vault's cross-platform name policy. That line SHALL become a level-1 heading at the start of the note body. The body SHALL be the captured text with `# ` inserted at the start of that line, unless the line already begins with `#`. All other captured text SHALL remain unchanged.

#### Scenario: First line becomes the name

- **WHEN** the user captures `Call Ada` followed by `about the invoice`
- **THEN** the note is named `Call Ada.md`

#### Scenario: Leading blank lines are skipped

- **WHEN** the captured text begins with blank lines
- **THEN** the first non-blank line becomes the name and receives the heading marker

#### Scenario: First line becomes the heading

- **WHEN** the user captures `Call Ada` followed by `about the invoice`
- **THEN** the body is `# Call Ada` followed by `about the invoice` on the next line

#### Scenario: Original wording is preserved in the heading

- **WHEN** the user captures `Q1: Planning?`
- **THEN** the identity is `Q1 Planning` and the body heading reads `# Q1: Planning?`

#### Scenario: An existing heading is not doubled

- **WHEN** the first non-blank line already begins with `#`
- **THEN** the body keeps that line as typed and adds no second heading marker

#### Scenario: The whole text is preserved

- **WHEN** the note is created
- **THEN** the body contains the complete captured text with `# ` inserted before the first non-blank line

#### Scenario: Unsafe characters are sanitized

- **WHEN** the first line contains characters forbidden in filenames
- **THEN** the derived filename applies the vault's cross-platform policy

#### Scenario: Repeated captures get distinct names

- **WHEN** the same text is captured twice
- **THEN** both notes exist with distinct names

### Requirement: The inbox is the folder under the vault root

The Inbox SHALL contain every note under the vault's `inbox/` directory, including nested subdirectories, and SHALL exclude every note outside it. The directory name SHALL be matched case-insensitively.

#### Scenario: Notes in the inbox are listed

- **WHEN** `inbox/A.md` and `inbox/B.md` exist
- **THEN** both appear in the Inbox

#### Scenario: Nested notes are listed

- **WHEN** `inbox/2026/C.md` exists
- **THEN** it appears in the Inbox

#### Scenario: Notes outside the inbox are excluded

- **WHEN** `work/D.md` exists
- **THEN** it does not appear in the Inbox

#### Scenario: Case variant is recognized

- **WHEN** the vault contains `Inbox/E.md`
- **THEN** it appears in the Inbox

#### Scenario: Moving a note out removes it

- **WHEN** a note is moved from `inbox/` to `work/` outside the application
- **THEN** it no longer appears in the Inbox and its name and references are unchanged

#### Scenario: Empty inbox shows an empty state

- **WHEN** no notes exist under `inbox/`
- **THEN** the Inbox shows an empty state that points to the composer

### Requirement: The inbox is ordered newest first

The Inbox SHALL order notes by file modification time, newest first, and SHALL use a deterministic tie-breaker when timestamps are equal.

#### Scenario: Newest note is first

- **WHEN** notes have different modification times
- **THEN** the most recently modified note appears first

#### Scenario: A new capture appears first

- **WHEN** the user captures a note
- **THEN** it appears before older notes

#### Scenario: Equal timestamps are deterministic

- **WHEN** two notes have the same modification time
- **THEN** their order is stable across scans

### Requirement: Inbox entries show the display title

Each Inbox entry SHALL show the note's display title as its primary text and its vault-relative path as the secondary text. Notes with the same display title SHALL remain distinguishable by that path.

#### Scenario: Entry uses the heading

- **WHEN** `inbox/Call Ada.md` has a body starting with `# Call Ada`
- **THEN** its Inbox entry shows `Call Ada`

#### Scenario: Entry falls back to the identity

- **WHEN** an Inbox note has no level-1 heading
- **THEN** its entry shows the note's identity

#### Scenario: Duplicate titles are distinguishable

- **WHEN** two Inbox notes both display the title `Buy milk`
- **THEN** each entry also shows its own vault-relative path

### Requirement: The preview is read-only

Selecting a note SHALL show its display title and its Markdown body rendered read-only. The preview MUST NOT display raw frontmatter as body text, write to the note, or launch or navigate any link.

#### Scenario: Body is rendered

- **WHEN** the user selects a note
- **THEN** the preview shows the rendered Markdown body

#### Scenario: Title comes from the heading

- **WHEN** the user selects a note whose body starts with `# Call Ada`
- **THEN** the preview header shows `Call Ada`

#### Scenario: Title falls back to the identity

- **WHEN** the user selects a note with no level-1 heading
- **THEN** the preview header shows the note's identity

#### Scenario: Preview performs no write

- **WHEN** a note is previewed
- **THEN** the file's content and modification time are unchanged

#### Scenario: Link taps are inert

- **WHEN** the user taps a link in the preview
- **THEN** no note is changed, no navigation occurs, and no external program is launched

#### Scenario: Frontmatter is not body text

- **WHEN** the user selects a note with frontmatter
- **THEN** the preview shows the body without the raw frontmatter block

### Requirement: Unreadable notes are reported, not hidden

When a scan cannot parse one or more notes, the Inbox SHALL show the readable notes and SHALL report the count and vault-relative paths of the unreadable notes. It MUST NOT silently omit them or modify them.

#### Scenario: Mixed vault shows a warning

- **WHEN** one note has malformed frontmatter and others are readable
- **THEN** the readable notes appear and a warning names the unreadable note

#### Scenario: Clean vault has no warning

- **WHEN** every note parses
- **THEN** no unreadable-note warning appears

#### Scenario: Capture still works

- **WHEN** an unreadable note exists and the user captures
- **THEN** the new note is created and appears in the Inbox

#### Scenario: Reporting makes no changes

- **WHEN** unreadable notes are reported
- **THEN** they are not rewritten, moved, or deleted

### Requirement: Refresh reflects external changes

The Inbox SHALL provide a refresh action that re-reads the vault, so notes added, edited, moved, or deleted outside the application are reflected without restarting.

#### Scenario: External addition appears

- **WHEN** a note is added to `inbox/` outside the application and the user refreshes
- **THEN** it appears in the Inbox

#### Scenario: External deletion disappears

- **WHEN** a note is deleted outside the application and the user refreshes
- **THEN** it no longer appears

#### Scenario: External edit is shown

- **WHEN** a note body is edited outside the application and the user refreshes
- **THEN** the preview shows the new body

### Requirement: Capture failures are reported safely

When a capture cannot be written, the application SHALL report an actionable error, SHALL leave no partial note, and SHALL preserve the composer text for retry. Capturing MUST NOT modify or delete any other note.

#### Scenario: Write failure leaves no partial note

- **WHEN** the vault cannot be written and the user captures
- **THEN** an error is shown and no partial note remains

#### Scenario: Composer text is preserved

- **WHEN** a capture fails
- **THEN** the captured text remains in the composer

#### Scenario: Other notes are untouched

- **WHEN** a capture is written
- **THEN** every other note's content is unchanged

#### Scenario: Path conflict is explained

- **WHEN** a regular file named `inbox` blocks the inbox directory
- **THEN** the error explains that the capture queue could not be created

### Requirement: Capture does not infer structure

Capture SHALL NOT infer a project, people, due date, or references from the text. The note SHALL remain unclassified until a later workflow changes it.

#### Scenario: Bare names are not links

- **WHEN** the captured text contains `Ada`
- **THEN** no `person:Ada` reference is created

#### Scenario: No due date is inferred

- **WHEN** the captured text contains a date
- **THEN** the note has no `due_date` key

#### Scenario: Only the type is declared

- **WHEN** the note is created
- **THEN** `type` is its only frontmatter key
