# vault-templates Specification

## Purpose

Defines the starter content Afanes can write into a newly created vault: the bundled template
catalog, its locale-scoped layout, the always-present guide note, and the rules that keep every
bundled tree valid.

## Requirements

### Requirement: Bundled templates are partial vaults

Afanes SHALL ship starter content as bundled Markdown trees. A template SHALL consist only of notes
and the folders that hold them, and applying it SHALL reproduce the same relative paths inside a
newly created vault. Applied notes SHALL be ordinary notes with no marker, provenance key, or
special status.

#### Scenario: Notes reproduce their relative paths

- **WHEN** a template containing `projects/Home projects.md` is applied
- **THEN** the created vault contains `projects/Home projects.md`

#### Scenario: Applied notes are ordinary notes

- **WHEN** a note from a template is opened after creation
- **THEN** it is renamed, edited, and trashed by the same actions as any other note

#### Scenario: No provenance is recorded

- **WHEN** a templated vault is created
- **THEN** no marker file is written, no settings entry records which notes came from a template, and
  no note carries a key identifying its origin

### Requirement: The catalog is fixed and ordered

Afanes SHALL offer a fixed, ordered catalog of bundled templates: Personal, Work, and Study, with
the identifiers `personal`, `work`, and `study`. Each entry SHALL carry a short label and a
one-sentence description, and the catalog MUST be readable without a vault being open.

#### Scenario: Catalog lists every template

- **WHEN** the catalog is requested
- **THEN** it reports personal, work, and study in that order

#### Scenario: Identifiers are stable

- **WHEN** a template is selected by identifier
- **THEN** the identifier is the kebab-case catalog entry, independent of its label

#### Scenario: Catalog needs no vault

- **WHEN** no vault is open
- **THEN** the catalog and its descriptions are still available

### Requirement: Templates differ in labels and shape

Each template SHALL declare a distinct set of reference category labels and a distinct project
shape. No two catalog entries may be content-identical.

#### Scenario: Labels are distinct

- **WHEN** Personal, Work, and Study are compared
- **THEN** Personal uses `person` and `place`, Work uses `team` and `process`, and Study uses `topic`
  and `source`

#### Scenario: Shapes are distinct

- **WHEN** two templates are compared
- **THEN** they differ in project count, step granularity, or both, and neither is a copy of the
  other with renamed titles

### Requirement: Template content is locale-scoped with a fallback

Template content SHALL live under one folder per locale. When the requested locale has no tree, the
application SHALL fall back to the base language rather than failing. Adding a locale MUST NOT change
a template identifier or its position in the catalog.

#### Scenario: Localized tree is preferred

- **WHEN** a template has a tree for the requested locale
- **THEN** that tree is applied

#### Scenario: Missing locale falls back

- **WHEN** a template has no tree for the requested locale
- **THEN** the base-language tree is applied and creation succeeds

#### Scenario: Identifier survives translation

- **WHEN** a localized tree is added for a template
- **THEN** the identifier, label, and catalog order are unchanged

### Requirement: A guide note is written into every created vault

Every created vault SHALL contain exactly one guide note at `reference/Getting started.md`
explaining the note model, including the `log` type. The guide SHALL declare `type: reference` with
no category, SHALL NOT be selectable as a template, and SHALL be an ordinary note afterwards.

#### Scenario: Blank creation writes the guide

- **WHEN** a vault is created without a template
- **THEN** `reference/Getting started.md` exists and the vault contains no other note

#### Scenario: Templated creation also writes the guide

- **WHEN** a vault is created from a template
- **THEN** the guide note exists alongside the template's notes

#### Scenario: The guide is a reference note

- **WHEN** the guide note is parsed
- **THEN** it has `type: reference`, no category, no status, and appears in the references section

#### Scenario: The guide name is reserved

- **WHEN** a bundled template declares a note whose stem is `Getting started`
- **THEN** the template is refused as invalid

#### Scenario: The guide can be removed

- **WHEN** the user trashes the guide note
- **THEN** the vault continues to work and nothing recreates the note

#### Scenario: The guide explains the log type

- **WHEN** the guide note is read
- **THEN** it describes the log note type, its editable date, and the Log section

### Requirement: Starter content never creates pending work

Bundled starter content MUST NOT introduce work the user did not write. Templates SHALL contain no
captures under `inbox/` and no step owners. A project due date and an unchecked step plan date SHALL
be after the creation date. An actual date SHALL appear only on a checked step and SHALL NOT be after
the creation date. Every open project in a template SHALL carry at least one unchecked step.

#### Scenario: New vault reports zero pending work

- **WHEN** a vault is created from any template
- **THEN** the review count is zero

#### Scenario: No captures are seeded

- **WHEN** a templated vault is created
- **THEN** `inbox/` contains no note

#### Scenario: Due dates are in the future

- **WHEN** a template project declares a due date
- **THEN** the written date is after the creation date

#### Scenario: Open steps are planned in the future

- **WHEN** a template step is unchecked and declares a plan date
- **THEN** the written date is after the creation date

#### Scenario: Completed steps carry a past actual date

- **WHEN** a template step is checked and declares an actual date
- **THEN** the written date is not after the creation date

#### Scenario: Unchecked steps carry no actual date

- **WHEN** a template step is unchecked
- **THEN** it declares no actual date

#### Scenario: No owners are seeded

- **WHEN** a template step is parsed
- **THEN** it declares no owner and is never reported as waiting

#### Scenario: Every open project has a step

- **WHEN** a template declares a project without a status or with an open status
- **THEN** that project contains at least one unchecked step

### Requirement: Creation resolves date placeholders

Bundled notes MAY write a date placeholder where a calendar date belongs, using the form
`{{ date:+Nd }}` or `{{ date:-Nd }}`, where `N` is a whole number of up to three digits and
surrounding whitespace is ignored. Creation SHALL replace each placeholder with the creation date
offset by that many days, written as `YYYY-MM-DD`. A written note MUST contain no placeholder, and a
note with a placeholder that cannot be resolved SHALL be refused before anything is written.

#### Scenario: Positive offset is applied

- **WHEN** a bundled note declares `{{ date:+14d }}`
- **THEN** the written note contains the date fourteen days after creation

#### Scenario: Negative offset is applied

- **WHEN** a bundled note declares `{{ date:-2d }}`
- **THEN** the written note contains the date two days before creation

#### Scenario: No placeholder is written

- **WHEN** any templated vault is created
- **THEN** no written note contains `{{`

#### Scenario: Malformed placeholder is refused

- **WHEN** a bundled note declares a placeholder that is not the supported form
- **THEN** the template is refused and creation writes nothing

### Requirement: Bundled trees satisfy the vault validity rules

Before applying bundled content, the application SHALL verify that every note parses, that stems are
unique across the template and the guide, that stems pass the cross-platform filename policy, that
every internal reference resolves inside the tree, that folder placement matches note type and
category, that no note sits under `inbox/` or `trash/`, and that every locale tree of one template
has the same shape. A tree that violates any rule MUST be refused, and nothing SHALL be written.

#### Scenario: Malformed note is refused

- **WHEN** a bundled note has malformed frontmatter
- **THEN** the template is refused and creation writes nothing

#### Scenario: Duplicate stem is refused

- **WHEN** two bundled notes share a stem
- **THEN** the template is refused and creation writes nothing

#### Scenario: Unresolved reference is refused

- **WHEN** a bundled note references a name that does not exist in the same tree
- **THEN** the template is refused and creation writes nothing

#### Scenario: Misplaced note is refused

- **WHEN** a bundled project is stored under `reference/`
- **THEN** the template is refused and creation writes nothing

#### Scenario: Locale trees must match in shape

- **WHEN** a localized tree has fewer projects or steps than the base tree
- **THEN** the template is refused and creation writes nothing

### Requirement: Applying a template reports partial writes

When writing a bundled note fails, creation SHALL stop, report the note that failed and the notes
already written, and leave the written notes in place. The failure SHALL be reported like any other
creation refusal, and the affected folder MUST remain openable as a vault.

#### Scenario: Failure names the note and the count

- **WHEN** writing the fourth of eight bundled notes fails
- **THEN** the failure names the failing note and reports the notes already written

#### Scenario: Written notes are kept

- **WHEN** template application fails partway
- **THEN** the notes already written remain in the vault and the folder can be opened as a vault

#### Scenario: Failure is reported as a refusal

- **WHEN** template application fails partway
- **THEN** the created folder is not remembered as the vault and the previous screen or vault remains

### Requirement: Templates apply only when a vault is created

Template content and the guide note SHALL be written only as part of creating a vault. Opening,
scanning, recovering, or reindexing an existing vault MUST NOT write template content or the guide
note.

#### Scenario: Opening writes nothing

- **WHEN** a created vault is opened again
- **THEN** no template note or guide note is added or restored

#### Scenario: A blank vault never gains a template

- **WHEN** a vault was created without a template
- **THEN** no later operation applies a template to it

### Requirement: A created vault contains the guide, template cards, and chosen template

Vault creation SHALL write the guide note, the eight template cards under `templates/`, and, when a
starter template is chosen, the notes that template declares. Creation MUST NOT write any other file,
and applying a starter template MUST NOT write outside the new vault.

#### Scenario: Blank vault holds the guide and cards

- **WHEN** a vault is created without a starter template
- **THEN** it contains the guide note and the eight template cards, and no other note

#### Scenario: Templated vault holds the guide, cards, and notes

- **WHEN** a vault is created from a starter template
- **THEN** it contains the guide, the eight cards, and exactly the notes the starter template declares

#### Scenario: Cards land in templates

- **WHEN** a vault is created
- **THEN** the eight cards exist under `templates/` and no card appears as a note

#### Scenario: Opening does not restore cards

- **WHEN** a card is deleted and the vault is reopened
- **THEN** the card is not recreated

#### Scenario: The log card is written

- **WHEN** a vault is created
- **THEN** `templates/daily.md` exists and declares `type: log`
