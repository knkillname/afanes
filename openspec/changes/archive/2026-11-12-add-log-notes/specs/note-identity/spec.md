# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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

Changing a log entry's `date` SHALL rename the file to the new ISO date, move it to the folder the
new date selects, and rewrite every inbound `log:` reference to the new name. The change SHALL NOT
ask for confirmation. The entry's level-1 heading SHALL be preserved. Failures SHALL be reported and
the operation SHALL be safe to re-run.

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

#### Scenario: The heading is kept

- **WHEN** an entry titled `A quiet Tuesday` changes date
- **THEN** its heading remains `A quiet Tuesday`

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
