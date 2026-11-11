# note-identity Specification

## Purpose

Defines how a note's filename becomes its name, title, and identity, and how Afanes keeps names unique and references stable across directory moves and renames.

## Requirements

### Requirement: Filename determines name and title

A note's filename stem SHALL be its name and identity. The directory and the `.md` extension SHALL NOT be part of the name. No stored `id` or `title` key SHALL participate in identity. The display title SHALL be derived from the body as defined by "Display title comes from the first level-1 heading".

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
- **THEN** the key is preserved as unknown data and does not override the heading-derived display title

#### Scenario: Display preserves case

- **WHEN** a note is named `Turing Machine.md` and has no level-1 heading
- **THEN** its title is displayed as `Turing Machine` and not lowercased

### Requirement: Names are unique per scheme

Within a scheme, one name SHALL identify exactly one note across the vault, using the same normalization as reference matching. Two notes with the same name in different directories SHALL be duplicates. Different schemes MAY reuse a name.

#### Scenario: Duplicate in different directories

- **WHEN** two notes of type `person` are named `Ada` in different directories
- **THEN** the vault is reported as having duplicate person names

#### Scenario: Cross-scheme reuse is allowed

- **WHEN** a person note and a project note are both named `Ada`
- **THEN** `person:Ada` and `project:Ada` resolve to their respective notes

#### Scenario: External duplicate is ambiguous

- **WHEN** a duplicate name is introduced outside the application
- **THEN** references to that name are reported as ambiguous and are not resolved to either note

### Requirement: Uniqueness is enforced on write

The application SHALL guarantee per-scheme name uniqueness when it creates or renames a note. At creation, a derived name already used in its scheme, or already present as a file in the target directory, SHALL receive the smallest available integer suffix. An explicit rename to a name already used in the same scheme SHALL be rejected with an actionable message.

#### Scenario: Creation collision is suffixed

- **WHEN** a second person note is created with the derived name `Ada`
- **THEN** it is created as `Ada 2`

#### Scenario: Rename collision is rejected

- **WHEN** a rename targets a name already used in the same scheme
- **THEN** the rename is rejected and the note keeps its current name

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

A rename SHALL change the filename and SHALL update affected references. The application SHALL show the affected count and require explicit confirmation before writing. Each affected file SHALL be written atomically. Failures and skipped files SHALL be reported, and the operation SHALL be safe to re-run. No reference SHALL be rewritten silently.

#### Scenario: Rename is previewed

- **WHEN** the user requests a rename
- **THEN** the application reports how many references in how many notes would change before asking for confirmation

#### Scenario: Confirmed rename updates destinations

- **WHEN** the user confirms renaming `Ada Lovelace` to `Ada King`
- **THEN** every resolving `person:Ada Lovelace` destination becomes `person:Ada King`

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

### Requirement: Deletion reports inbound references

Before deleting a note, the application SHALL report how many references point to it. After deletion, those references SHALL become unresolved. Deletion MUST NOT rewrite or remove references.

#### Scenario: Inbound count is shown

- **WHEN** the user requests deletion of a referenced note
- **THEN** the application reports the number of inbound references before confirmation

#### Scenario: References remain unresolved

- **WHEN** a referenced note is deleted
- **THEN** its inbound references are reported as unresolved and remain in the referring notes

#### Scenario: Deletion removes no reference text

- **WHEN** a referenced note is deleted
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
