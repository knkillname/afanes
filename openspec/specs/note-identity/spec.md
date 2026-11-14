# note-identity Specification

## Purpose

Defines how a note's filename becomes its name, title, and identity, and how Afanes keeps names unique and references stable across directory moves and renames.

## Requirements

### Requirement: Filename determines name and title

A note's filename stem SHALL be its name and identity. The directory and the `.md` extension SHALL
NOT be part of the name. No stored `id` or `title` key SHALL participate in identity. For a log note,
the stem SHALL be its ISO date. The display title SHALL be derived from the body as defined by
"Display title comes from the first level-1 heading".

#### Scenario: Title is the stem

- **WHEN** `people/Ada Lovelace.md` has no level-1 heading
- **THEN** its display title and reference name are `Ada Lovelace`

#### Scenario: Directory is not part of the name

- **WHEN** a note moves from `work/` to `people/`
- **THEN** its name and identity are unchanged

#### Scenario: Stored id is ignored

- **WHEN** a note's frontmatter contains an `id` key
- **THEN** the key is preserved as unknown data and is not used for identity

#### Scenario: Stored title is ignored

- **WHEN** a note's frontmatter contains a `title` key
- **THEN** the key is preserved as unknown data and does not override the heading-derived display
  title

#### Scenario: Display preserves case

- **WHEN** a note is named `Turing Machine.md` and has no level-1 heading
- **THEN** its title is displayed as `Turing Machine` and not lowercased

#### Scenario: A log name is its date

- **WHEN** a log entry is stored as `log/2025/10/2025-10-12.md`
- **THEN** its name and identity are `2025-10-12`

#### Scenario: A log title comes from its heading

- **WHEN** `log/2025/10/2025-10-12.md` has the body heading `# A quiet Tuesday`
- **THEN** its display title is `A quiet Tuesday`

### Requirement: Names are unique per scheme

Within a scheme, one name SHALL identify exactly one note across the vault, using the same
normalization as reference matching. Two notes with the same name in different directories SHALL be
duplicates. The `note`, `project`, and `log` schemes MAY reuse a name. Every reference shares the
`note` scheme, regardless of its category.

#### Scenario: Duplicate in different directories

- **WHEN** two reference notes are named `Ada` in different directories
- **THEN** the vault is reported as having duplicate note names

#### Scenario: Cross-scheme reuse is allowed

- **WHEN** a reference note and a project note are both named `Ada`
- **THEN** `note:Ada` and `project:Ada` resolve to their respective notes

#### Scenario: Categorized reference shares the note scheme

- **WHEN** a reference with `category: person` and an uncategorized note are both named `Ada`
- **THEN** the vault is reported as having duplicate note names

#### Scenario: External duplicate is ambiguous

- **WHEN** a duplicate name is introduced outside the application
- **THEN** references to that name are reported as ambiguous and are not resolved to either note

#### Scenario: A log name is separate from note and project names

- **WHEN** a reference named `2025-10-12` and a log entry dated `2025-10-12` both exist
- **THEN** `note:2025-10-12` and `log:2025-10-12` resolve to their respective notes

### Requirement: Uniqueness is enforced on write

The application SHALL guarantee per-scheme name uniqueness when it creates or renames a note. At
creation, a derived name already used in its scheme, or already present as a file in the target
directory, SHALL receive the smallest available integer suffix, except that a log creation SHALL be
refused when its date is occupied. An explicit rename to a name already used in the same scheme
SHALL be rejected with an actionable message.

#### Scenario: Creation collision is suffixed

- **WHEN** a second person note is created with the derived name `Ada`
- **THEN** it is created as `Ada 2`

#### Scenario: Rename collision is rejected

- **WHEN** a rename targets a name already used in the same scheme
- **THEN** the rename is rejected and the note keeps its current name

#### Scenario: An occupied log date is refused

- **WHEN** a log entry is created for a date that already has a log entry
- **THEN** creation is refused, no suffix is added, and the existing entry is unchanged

### Requirement: Cross-platform name sanitization

When creating or renaming a note, the application SHALL derive a filename safe on macOS, Linux, and Windows: replace forbidden characters, avoid reserved device names, remove trailing dots and spaces, remove leading dots, enforce a 200-byte UTF-8 limit, and write NFC. The sanitized stem SHALL become the note's identity and reference name. It SHALL NOT replace the display title.

#### Scenario: Forbidden characters are replaced

- **WHEN** a title source is `Q1: Planning?`
- **THEN** the derived identity is `Q1 Planning`

#### Scenario: Sanitization preserves the display title

- **WHEN** a page is created from `Q1: Planning?`
- **THEN** its identity is `Q1 Planning` and its body heading still reads `# Q1: Planning?`

#### Scenario: Reserved device name is avoided

- **WHEN** a title source is `CON`
- **THEN** the derived identity is `CON-note`

#### Scenario: Trailing dot or space is removed

- **WHEN** a title source ends with a dot or a space
- **THEN** the derived identity does not

#### Scenario: Leading dot is removed

- **WHEN** a title source begins with a dot
- **THEN** the derived identity does not begin with a dot

#### Scenario: Length is bounded

- **WHEN** a title source exceeds the byte limit
- **THEN** the derived identity is truncated to fit and remains unique

#### Scenario: Empty result has a fallback

- **WHEN** a title source sanitizes to an empty identity
- **THEN** the derived identity is `Untitled`

### Requirement: Display title comes from the first level-1 heading

The display title of a note SHALL be the text of the first level-1 Markdown heading in its body. When the body has no level-1 heading, or its first level-1 heading has blank text, the display title SHALL be the note's identity. The display title SHALL NOT participate in identity, uniqueness, or reference resolution.

#### Scenario: Heading becomes the title

- **WHEN** a note with identity `Ada` has a body starting with `# Ada, Countess of Lovelace`
- **THEN** the application displays `Ada, Countess of Lovelace` as its title

#### Scenario: Missing heading falls back

- **WHEN** a note has no level-1 heading
- **THEN** the application displays its identity as the title

#### Scenario: First heading wins

- **WHEN** a body has two level-1 headings
- **THEN** the first one is the display title

#### Scenario: Heading after introductory text

- **WHEN** a body begins with a paragraph and later has a level-1 heading
- **THEN** that heading is still the display title

#### Scenario: Heading in a code block is ignored

- **WHEN** the only line beginning with `#` is inside a fenced code block
- **THEN** the note falls back to its identity as the title

#### Scenario: Title edit changes no reference

- **WHEN** a note's level-1 heading is edited from `Ada` to `Ada, Countess of Lovelace`
- **THEN** `person:Ada` still resolves to the note and no reference is rewritten

#### Scenario: Duplicate titles are allowed

- **WHEN** two notes have the same level-1 heading
- **THEN** both keep that title and remain distinct by identity

### Requirement: Directory moves preserve identity

Moving a note between directories SHALL NOT change its name or any reference to it. The application SHALL confirm the move and perform it without rewriting references.

#### Scenario: Move is confirmed

- **WHEN** the user requests a directory move
- **THEN** the application asks for confirmation before moving the file

#### Scenario: Move changes no reference

- **WHEN** `people/Ada Lovelace.md` moves to `work/Ada Lovelace.md`
- **THEN** every `person:Ada Lovelace` reference still resolves

#### Scenario: Backlinks survive a move

- **WHEN** a referenced note moves between directories
- **THEN** its inbound and outbound backlinks are unchanged

### Requirement: Renames maintain references

A rename SHALL change the filename and SHALL update affected references, including metadata role
references. The application SHALL show the affected count and require explicit confirmation before
writing. Each affected file SHALL be written atomically. Failures and skipped files SHALL be
reported, and the operation SHALL be safe to re-run. No reference SHALL be rewritten silently.

#### Scenario: Rename is previewed

- **WHEN** the user requests a rename
- **THEN** the application reports how many references in how many notes would change before asking
  for confirmation

#### Scenario: Confirmed rename updates destinations

- **WHEN** the user confirms renaming `Ada Lovelace` to `Ada King`
- **THEN** every resolving `note:Ada Lovelace` destination becomes `note:Ada King`

#### Scenario: Cancelled rename changes nothing

- **WHEN** the user cancels at the preview
- **THEN** no file is renamed and no reference is rewritten

#### Scenario: Custom label is preserved

- **WHEN** a reference label differs from the old name
- **THEN** the rewrite updates the destination and leaves the custom label intact

#### Scenario: Changed file is skipped

- **WHEN** a referring note changed on disk after the preview
- **THEN** that note is skipped and reported rather than overwritten

#### Scenario: Partial failure is reported

- **WHEN** a rewrite fails for one referring note
- **THEN** the application reports which notes were updated and which were not

#### Scenario: Re-run completes the update

- **WHEN** the rename is run again after a partial failure
- **THEN** remaining old-name references are found and updated without duplicating prior work

#### Scenario: Project role names are rewritten

- **WHEN** a project declares `owner: Sam Rivera` or `asked_by: Sam Rivera` and the note named
  `Sam Rivera` is renamed
- **THEN** both matching values are rewritten to the new name

#### Scenario: Step owner names are rewritten

- **WHEN** a step declares `owners: [Sam Rivera, Ada]` and the note named `Sam Rivera` is renamed
- **THEN** only `Sam Rivera` changes and `Ada` remains

#### Scenario: Metadata rewrite is counted in the preview

- **WHEN** the only reference to `Sam Rivera` is a project owner value
- **THEN** the rename preview reports that project as an affected note

### Requirement: Metadata role rewrites preserve surrounding data

A rewrite of a metadata role reference SHALL change only the matching value. Frontmatter unknown
keys, body text, newline style, and every other step metadata key SHALL be preserved. The file SHALL
be written atomically, and a failed rewrite SHALL leave the file unchanged.

#### Scenario: Frontmatter keys survive an owner rewrite

- **WHEN** a project with `owner: Sam Rivera` and an unknown `priority: high` key is rewritten
- **THEN** only the owner value changes and `priority: high` remains

#### Scenario: Step metadata survives an owner rewrite

- **WHEN** a step declares `owners: [Sam Rivera]`, `plan`, `actual`, `tags`, and an unknown key
- **THEN** only the owner name changes and every other metadata key is preserved

#### Scenario: Newlines survive a rewrite

- **WHEN** a CRLF note contains a role reference and the referenced note is renamed
- **THEN** the rewritten note keeps CRLF line endings

#### Scenario: A failed rewrite leaves the file unchanged

- **WHEN** a metadata role rewrite fails
- **THEN** the file's content and modification time are unchanged

### Requirement: Trashing leaves inbound references unresolved

Trashing a note SHALL NOT report or rewrite its inbound references before the move. After the move,
those references SHALL be unresolved and remain in the referring notes. The page's undo action SHALL
restore the note so the references resolve on the next scan.

#### Scenario: Trashing does not report a count

- **WHEN** the user trashes a note that has inbound references
- **THEN** the application moves the note without reporting a reference count first

#### Scenario: References become unresolved

- **WHEN** a referenced note is moved to trash
- **THEN** its inbound references are reported as unresolved and remain in the referring notes

#### Scenario: Undo resolves the references

- **WHEN** a just-trashed note is restored by the page's undo action
- **THEN** its inbound references resolve on the next scan

#### Scenario: Role names remain after trashing

- **WHEN** a trashed note is named as a project owner, requester, or step owner
- **THEN** the project keeps the plain-text value and the connection becomes unresolved

#### Scenario: No referring note is rewritten

- **WHEN** a note is moved to trash
- **THEN** no referring note is modified

### Requirement: External structure changes

Content edits made outside the application SHALL be reindexed. External moves, renames, and deletions SHALL be reported as unsupported structural changes. The application MUST NOT rewrite references to follow them automatically and MAY offer a repair that requires explicit confirmation.

#### Scenario: External content edit is reindexed

- **WHEN** a note body is edited outside the application
- **THEN** the index reflects the new content after the next scan

#### Scenario: External rename leaves broken references

- **WHEN** a note is renamed outside the application
- **THEN** its inbound references are reported as unresolved

#### Scenario: Detection performs no writes

- **WHEN** the application starts or scans a vault and detects an external structural change
- **THEN** it reports the condition and writes no vault file

#### Scenario: Repair requires confirmation

- **WHEN** the application offers to follow an external rename
- **THEN** it changes no reference unless the user explicitly confirms the repair

### Requirement: Trashed notes are outside the catalog

Notes under `trash/` SHALL be excluded from identity and name uniqueness. Their names MAY be reused by active notes. A reference to a trashed note SHALL be unresolved.

#### Scenario: Trashed note is not in the catalog

- **WHEN** a note is moved to `trash/`
- **THEN** it is not part of the active note catalog

#### Scenario: Trashed name can be reused

- **WHEN** a note named `Ada` is in `trash/` and a new `Ada` note is created
- **THEN** the new note is accepted without a numeric suffix

#### Scenario: Reference to a trashed note is unresolved

- **WHEN** a note references a note that is under `trash/`
- **THEN** the reference is reported as unresolved

#### Scenario: Restored note resolves references

- **WHEN** a trashed note is moved back to an active folder
- **THEN** its inbound references resolve on the next scan

#### Scenario: Trash is excluded case-insensitively

- **WHEN** the vault contains `Trash/Ada.md`
- **THEN** it is excluded from identity and resolution

#### Scenario: Trashing does not rewrite notes

- **WHEN** a note is moved to `trash/`
- **THEN** no referring note is modified

### Requirement: Rename keeps a matching heading in step

When a note is renamed, its first level-1 heading SHALL be updated to the new identity only when that heading's text matches the old identity exactly after trimming surrounding whitespace. Any other heading SHALL be preserved. A note without a level-1 heading SHALL NOT gain one.

#### Scenario: Default heading follows the rename

- **WHEN** a note with identity `Ada` and the first heading `# Ada` is renamed to `Ada King`
- **THEN** the heading becomes `# Ada King`

#### Scenario: Custom heading is preserved

- **WHEN** a note with identity `Ada` and the first heading `# Ada, Countess of Lovelace` is renamed
- **THEN** the heading is unchanged

#### Scenario: Missing heading stays missing

- **WHEN** a note with no level-1 heading is renamed
- **THEN** no heading is added and the display title falls back to the new identity

#### Scenario: Heading in code is not a title

- **WHEN** the only matching line is inside a fenced code block
- **THEN** it is not treated as the display title and is not rewritten

#### Scenario: Heading update is part of the confirmed rename

- **WHEN** the user confirms a previewed rename
- **THEN** the heading update and the reference rewrites are applied by that same confirmed operation

#### Scenario: Cancelled rename changes no heading

- **WHEN** the user cancels at the rename preview
- **THEN** no heading is updated

### Requirement: Steps are not notes

Steps SHALL NOT be notes. A step has no filename, no identity, and no entry in the name catalog. A reference MUST NOT resolve to a step, and a step is reachable only through its project page.

#### Scenario: Steps are absent from the catalog

- **WHEN** a vault is scanned
- **THEN** project steps do not appear as notes and do not join name uniqueness

#### Scenario: A link cannot target a step

- **WHEN** a reference name matches a step's text
- **THEN** the reference does not resolve to the step

#### Scenario: Renaming a project does not rename its steps

- **WHEN** a project is renamed
- **THEN** its steps keep their text and are still reached through the project

### Requirement: Log names are ISO dates

A log note's filename stem SHALL be exactly its `date` at its precision: `YYYY`, `YYYY-MM`, or
`YYYY-MM-DD`. The stem MUST NOT be sanitized, suffixed, or derived from the display title. A log note
without a date SHALL use an undated fallback identity and MUST NOT be reachable as a dated log
reference.

#### Scenario: A year entry is named after its year

- **WHEN** a log entry is dated `2025`
- **THEN** its file is named `2025.md`

#### Scenario: A month entry is named after its month

- **WHEN** a log entry is dated `2025-10`
- **THEN** its file is named `2025-10.md`

#### Scenario: A day entry is named after its day

- **WHEN** a log entry is dated `2025-10-12`
- **THEN** its file is named `2025-10-12.md`

#### Scenario: The heading does not change the name

- **WHEN** a log entry's heading is `A quiet Tuesday`
- **THEN** its filename remains the date

### Requirement: A log date change renames, moves, and rewrites references

Changing a log entry's `date` SHALL rename the file, move it to the new date's folder, and rewrite
every inbound `log:` reference. The change SHALL NOT ask for confirmation. The level-1 heading
SHALL follow the date only when it equals a generated default title in any supported locale;
otherwise it SHALL be preserved. Failures SHALL be reported and the operation SHALL be safe to
re-run.

#### Scenario: A date change renames the file

- **WHEN** an entry dated `2025-10-12` is changed to `2025-10-13`
- **THEN** the file becomes `2025-10-13.md`

#### Scenario: A date change moves the file

- **WHEN** an entry dated `2025-10-12` is changed to `2025-11-02`
- **THEN** the file moves from `log/2025/10/` to `log/2025/11/`

#### Scenario: Inbound references are rewritten

- **WHEN** a note links to `log:2025-10-12` and the entry moves to `2025-10-13`
- **THEN** the referring destination becomes `log:2025-10-13`

#### Scenario: No confirmation is required

- **WHEN** the user changes a log entry's date
- **THEN** the rename, move, and rewrites run without a preview dialog

#### Scenario: The generated heading follows the date

- **WHEN** an entry titled `October 12, 2025` changes to `2025-10-13` under English
- **THEN** its heading becomes `October 13, 2025`

#### Scenario: The generated Spanish heading follows the date

- **WHEN** an entry titled `12 de octubre de 2025` changes to `2025-10-13` under Spanish
- **THEN** its heading becomes `13 de octubre de 2025`

#### Scenario: A generated heading from another locale follows the date

- **WHEN** an entry titled `October 12, 2025` changes to `2025-10-13` under Spanish
- **THEN** its heading becomes `13 de octubre de 2025`

#### Scenario: A Spanish generated heading follows the date under English

- **WHEN** an entry titled `12 de octubre de 2025` changes to `2025-10-13` under English
- **THEN** its heading becomes `October 13, 2025`

#### Scenario: The generated heading follows a precision change

- **WHEN** an entry titled `October 2025` changes to `2025`
- **THEN** its heading becomes `2025`

#### Scenario: The heading is kept

- **WHEN** an entry titled `A quiet Tuesday` changes date
- **THEN** its heading remains `A quiet Tuesday`

#### Scenario: A custom heading in another language is kept

- **WHEN** an entry titled `Un martes tranquilo` changes date
- **THEN** its heading remains `Un martes tranquilo`

#### Scenario: A date-shaped custom heading is kept

- **WHEN** an entry titled `2025-10-12` changes date
- **THEN** its heading remains `2025-10-12`

#### Scenario: A failed rewrite is reported

- **WHEN** one referring file changed on disk after the scan
- **THEN** that file is skipped, the entry still moves, and the skipped file is reported

### Requirement: Changing type into or out of log renames and rewrites references

Changing a note's type to `log` SHALL require a valid `date`, rename the file to that date, move it
to the log folder, and rewrite inbound references from their old scheme to `log:<date>`. Changing a
log entry to `reference` or `project` SHALL rename it to its display title, move it to the matching
folder, and rewrite inbound `log:` references to the new scheme. The operation SHALL NOT ask for
confirmation beyond the existing type-change step. An occupied log date SHALL refuse the change.

#### Scenario: A reference becomes a log entry

- **WHEN** a reference dated `2025-10-12` is changed to `log`
- **THEN** its file becomes `log/2025/10/2025-10-12.md` and `note:` links become `log:2025-10-12`

#### Scenario: A log entry becomes a reference

- **WHEN** a log entry is changed to `reference`
- **THEN** its file is renamed to its display title and moves to `reference/`

#### Scenario: A log entry becomes a project

- **WHEN** a log entry is changed to `project`
- **THEN** its file is renamed to its display title and moves to `projects/`

#### Scenario: An undated note cannot become a log

- **WHEN** a note with no `date` is changed to `log`
- **THEN** the change is refused and the user is asked to set a date first

#### Scenario: An occupied date refuses the change

- **WHEN** a note is changed to `log` and its date already has a log entry
- **THEN** the change is refused and nothing is renamed or moved

### Requirement: Reference rewrites report affected notes

Every reference rewrite, including rename, type change, date change, and link repair, SHALL report
which notes were updated and which were not. A skipped or failed note SHALL be named with its reason.
Paths SHALL be shown relative to the vault root.

#### Scenario: Rename reports every affected note

- **WHEN** a rename rewrites one note and skips another
- **THEN** the report names the updated note and the skipped note with its reason

#### Scenario: Type change reports every affected note

- **WHEN** a type change rewrites one note and fails on another
- **THEN** the report names the updated note and the failed note with its reason

#### Scenario: Date change reports every affected note

- **WHEN** a date change rewrites one note and skips another
- **THEN** the report names the updated note and the skipped note with its reason

#### Scenario: Repair reports every affected note

- **WHEN** a link repair rewrites one note and fails on another
- **THEN** the report names the updated note and the failed note with its reason
