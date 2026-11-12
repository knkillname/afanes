# template-cards Specification

## Purpose

Defines the user-editable reference and log template cards stored in a vault `templates/` folder, their format, the seeded defaults, validation, and how a card supplies a category or starter body when a matching note is created.

## Requirements

### Requirement: Template cards are vault files

Reference and log template cards SHALL be Markdown files stored under the vault's `templates/`
folder. The folder SHALL be a convention, not a note folder, and users SHALL be able to add, edit, or
delete cards with any text editor.

#### Scenario: A card is a file

- **WHEN** the vault contains `templates/vendor.md`
- **THEN** the card is available to the matching creation picker

#### Scenario: A user adds a card

- **WHEN** the user creates `templates/vendor.md`
- **THEN** the card appears the next time the matching creation picker is opened

#### Scenario: A user deletes a card

- **WHEN** the user removes `templates/person.md`
- **THEN** the card no longer appears in the pickers and existing notes are unchanged

#### Scenario: A missing folder is not created

- **WHEN** a vault has no `templates/` folder and the app opens or scans it
- **THEN** no folder is created and the pickers offer only Empty

#### Scenario: A log card is a file

- **WHEN** the vault contains `templates/daily.md` with `type: log`
- **THEN** the card appears in the log creation picker

### Requirement: The card format declares its metadata and starter body

A card SHALL be a Markdown file whose frontmatter declares `type` and MAY declare `title` and
`description`. A reference card SHALL declare `type: reference` and a `category` label. A log card
SHALL declare `type: log` and MUST NOT declare a category. The Markdown after the frontmatter SHALL
be the starter body. The body MUST NOT contain a level-1 heading, and MAY be empty.

#### Scenario: A complete card parses

- **WHEN** a card declares a reference type, a category, a title, and a description
- **THEN** the picker shows the title and description and uses the category for new notes

#### Scenario: A log card parses

- **WHEN** a card declares `type: log`, a title, and a starter body
- **THEN** the log picker shows the title and uses the body for new entries

#### Scenario: The title falls back to the file name

- **WHEN** a card omits its title
- **THEN** the picker uses the file stem as the title

#### Scenario: The description is optional

- **WHEN** a card omits its description
- **THEN** the card remains valid and the picker shows no description

#### Scenario: A level-1 heading is refused

- **WHEN** a card's starter body contains a level-1 heading
- **THEN** the card is invalid and is reported with the other invalid cards

#### Scenario: A missing category is refused

- **WHEN** a reference card omits its category
- **THEN** the card is invalid and is reported

#### Scenario: A log card category is refused

- **WHEN** a log card declares a category
- **THEN** the card is invalid and is reported

#### Scenario: A non-reference type is refused

- **WHEN** a card declares a type other than reference or log
- **THEN** the card is invalid and is reported

#### Scenario: Workflow keys are refused

- **WHEN** a card declares a status or due date
- **THEN** the card is invalid and is reported

#### Scenario: Malformed frontmatter is refused

- **WHEN** a card's frontmatter cannot be parsed
- **THEN** the card is invalid and is reported

### Requirement: The picker lists valid cards and the Empty option

The reference creation pickers SHALL list every valid reference card and SHALL always offer Empty.
The log creation picker SHALL list every valid log card and SHALL always offer Empty. Each list SHALL
be ordered deterministically by title and then by file path, and duplicate titles SHALL remain
distinguishable by their paths.

#### Scenario: Cards are listed by title

- **WHEN** the folder contains cards titled Person and Place
- **THEN** the reference picker lists both in title order

#### Scenario: Empty is always available

- **WHEN** the folder is missing, empty, or contains only invalid cards
- **THEN** the picker still offers Empty

#### Scenario: Duplicate titles are distinguishable

- **WHEN** two cards share a title
- **THEN** the picker shows both and distinguishes them by their file paths

#### Scenario: Invalid cards are reported

- **WHEN** one card is invalid and others are valid
- **THEN** the picker lists the valid cards and names the invalid file

#### Scenario: The log picker lists only log cards

- **WHEN** the folder contains a reference card and a log card
- **THEN** the log picker lists the log card and not the reference card

### Requirement: A card supplies a category and starter body

Creating a reference from a reference card SHALL set the note's category to the card's category and
SHALL use the card's starter body as appended content. Creating a log entry from a log card SHALL use
only the card's starter body; the card MUST NOT supply a category, status, or date. The card's title
and description SHALL NOT be copied into the note.

#### Scenario: The category is applied

- **WHEN** the user creates a reference from a card with `category: person`
- **THEN** the note declares `category: person` and is filed under `reference/person/`

#### Scenario: The starter body is appended

- **WHEN** the user creates a reference from a card with a starter body
- **THEN** the note's body contains the title followed by the starter body

#### Scenario: Metadata is not copied

- **WHEN** a card declares a title and description
- **THEN** the new note does not gain a title or description key from the card

#### Scenario: An empty body is valid

- **WHEN** a card declares a category and an empty starter body
- **THEN** the new note is created with the category and no added body

#### Scenario: The category folder is reused

- **WHEN** `reference/Place/` already exists and a card uses `category: place`
- **THEN** the new note is filed in the existing `reference/Place/` folder

#### Scenario: A log card supplies no workflow labels

- **WHEN** a log entry is created from a log card
- **THEN** the note declares no category, status, due date, or requester

### Requirement: Empty creates a general reference

The Empty option SHALL create a reference with `category: general` and no starter body. The note SHALL be filed under `reference/general/`.

#### Scenario: Browser Empty

- **WHEN** the user creates a reference from the browser with Empty
- **THEN** the note declares `category: general` and has no starter body

#### Scenario: Processing Empty

- **WHEN** the user processes a capture with Empty
- **THEN** the note declares `category: general` and keeps the capture text

#### Scenario: Later Empty

- **WHEN** the user processes a capture with Later and Empty
- **THEN** the note declares `category: general`, `status: later`, and keeps the capture text

### Requirement: Cards apply only when a reference is created

A card SHALL be applied only when a note of the card's type is created from it. Opening, scanning,
renaming, or changing the category of an existing note MUST NOT insert or repair a starter body.

#### Scenario: Category change does not add a starter body

- **WHEN** the user changes an existing reference's category
- **THEN** the file moves and its body is unchanged

#### Scenario: Link-created drafts are unaffected

- **WHEN** the user follows a missing `note:` link
- **THEN** the draft is an uncategorized reference with no starter body

#### Scenario: Existing notes are not repaired

- **WHEN** a card's starter body changes after a note was created
- **THEN** the existing note is unchanged

#### Scenario: An existing log is not repaired

- **WHEN** a log card changes after a log entry was created
- **THEN** the existing entry is unchanged

### Requirement: Cards leave no provenance

A note created from a card SHALL be an ordinary reference. It MUST NOT record which card produced it, and no marker, settings entry, or catalog file SHALL be written for the card catalog.

#### Scenario: No card key is written

- **WHEN** a note is created from a card
- **THEN** its frontmatter contains no key naming the card

#### Scenario: The note is ordinary

- **WHEN** a note created from a card is opened
- **THEN** it can be edited, renamed, categorized, and trashed like any reference

#### Scenario: Deleting the card does not affect the note

- **WHEN** the user deletes the card that created a note
- **THEN** the note remains unchanged

### Requirement: Seeding failures are reported

When a default card cannot be written during vault creation, creation SHALL stop and report the
failing card and the cards already written. The written cards SHALL remain in place, and the folder
SHALL remain openable as a vault.

#### Scenario: A default card fails partway

- **WHEN** the fifth of eight cards cannot be written
- **THEN** the failure names the card and the cards already written
- **AND** the folder can still be opened as a vault

### Requirement: New vaults seed eight default cards

A newly created vault SHALL contain eight editable template cards: Person, Team, Organization,
Place, Process, Topic, Source, and Daily entry. Each card SHALL declare its type, a title, a
description, and its starter body; each reference card SHALL also declare its category, and the
Daily entry card SHALL declare `type: log` with no category.

#### Scenario: A new vault has the eight cards

- **WHEN** a vault is created
- **THEN** `templates/` contains person, team, organization, place, process, topic, source, and daily
  cards

#### Scenario: The Daily entry card is a log card

- **WHEN** a new vault is created
- **THEN** `templates/daily.md` declares `type: log`, no category, and a reflection body

#### Scenario: A blank vault also has the cards

- **WHEN** a vault is created without a vault starter template
- **THEN** it still contains the eight template cards

#### Scenario: The cards create no pending work

- **WHEN** a vault is created from any starter template
- **THEN** the review count is zero and no card appears as a note

#### Scenario: The cards are editable

- **WHEN** the user edits a seeded card
- **THEN** the edited card is used the next time a picker opens

#### Scenario: Deleted cards are not restored

- **WHEN** the user deletes a seeded card and reopens the vault
- **THEN** the card is not recreated

### Requirement: Empty creates an untemplated log entry

The Empty option in the log creation picker SHALL create a log entry with no starter body. It MUST
NOT add a category, status, due date, or requester.

#### Scenario: Empty log entry

- **WHEN** the user creates a log entry from an empty day with Empty
- **THEN** the note has the chosen date and only the title heading in its body

#### Scenario: Empty does not change the reference rule

- **WHEN** the user creates a reference with Empty
- **THEN** the reference still receives `category: general` and no starter body
