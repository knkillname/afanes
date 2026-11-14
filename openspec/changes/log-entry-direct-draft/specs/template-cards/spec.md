# Spec Delta

## MODIFIED Requirements

### Requirement: The picker lists valid cards and the Empty option

The reference creation pickers SHALL list every valid reference card and SHALL always offer Empty. A
new log draft's Starter control SHALL list every valid log card and SHALL always offer Empty. Each
list SHALL be ordered deterministically by title and then by file path, and duplicate titles SHALL
remain distinguishable by their paths.

#### Scenario: Cards are listed by title

- **WHEN** the folder contains cards titled Person and Place
- **THEN** the reference picker lists both in title order

#### Scenario: Empty is always available

- **WHEN** the folder is missing, empty, or contains only invalid cards
- **THEN** the picker or Starter control still offers Empty

#### Scenario: Duplicate titles are distinguishable

- **WHEN** two cards share a title
- **THEN** the picker shows both and distinguishes them by their file paths

#### Scenario: Invalid cards are reported

- **WHEN** one card is invalid and others are valid
- **THEN** the picker lists the valid cards and names the invalid file

#### Scenario: The log picker lists only log cards

- **WHEN** the folder contains a reference card and a log card
- **THEN** the Starter control lists the log card and not the reference card

### Requirement: A card supplies a category and starter body

Creating a reference from a reference card SHALL set the note's category to the card's category and
SHALL use the card's starter body as appended content. Choosing a log card in a new log draft SHALL
use only the card's starter body; the card MUST NOT supply a category, status, or date. The card's
title and description SHALL NOT be copied into the note.

#### Scenario: The category is applied

- **WHEN** the user creates a reference from a card with `category: person`
- **THEN** the note declares `category: person` and is filed under `reference/person/`

#### Scenario: The starter body is appended

- **WHEN** the user creates a reference from a card with a starter body
- **THEN** the note's body contains the title followed by the starter body

#### Scenario: The starter body fills a log draft

- **WHEN** the user chooses a log card with a starter body in a new log draft
- **THEN** the draft body contains the title heading followed by the starter body

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

### Requirement: Empty creates an untemplated log entry

The Empty option in a new log draft's Starter control SHALL leave only the title heading and no
starter body. It MUST NOT add a category, status, due date, or requester.

#### Scenario: Empty log entry

- **WHEN** the user creates a log entry from an empty day with Empty
- **THEN** the note has the chosen date and only the title heading in its body

#### Scenario: Empty does not change the reference rule

- **WHEN** the user creates a reference with Empty
- **THEN** the reference still receives `category: general` and no starter body
