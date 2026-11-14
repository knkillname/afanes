---
type: reference
---

# Getting started

Afanes reads and writes a folder of Markdown files called a vault. Every file is one note. The
first block between `---` lines holds the metadata Afanes uses; the rest of the file is ordinary
Markdown. Nothing is stored anywhere else, so the files stay readable and portable without the
application.

## Four kinds of notes

- **Note** — a thought that has not been clarified yet. Captures live in `inbox/`, and a note may
  only sit there.
- **Reference** — something worth keeping that you do not act on: a contact, a place, a topic, a
  process. References live in `reference/`, optionally inside one category folder.
- **Project** — an outcome that needs more than one action. Projects live in `projects/`, and the
  steps that advance them are checkbox items in the same file.
- **Log** — a dated diary entry. Its date is its identity, and it lives under `log/`.

## Category labels

A reference can declare a `category` key. The label is free-form: it groups references under one
heading in the browser and gives them a folder inside `reference/`. `person`, `place`, `team`,
`process`, `topic`, and `source` are conventions, not a fixed list; write any label that helps you
find the note again.

## Reference template cards

Every new vault includes a `templates/` folder with reference and log template cards. A reference
card declares a `category` and a starter body; a log card declares `type: log` and a starter body.
Choosing a card in processing, in the browser, or in the Log creates a note with the right shape.
The seeded cards cover a person, a team, an organization, a place, a process, a topic, a source, and
a daily entry.

The folder is not part of your notes. Files in `templates/` are left out of the browser and out of
searches, and their names never collide with note names. Edit, add, or delete cards with any text
editor; a card removed from the folder stays removed.

## Log entries

A log entry is a diary page. Its `date` is its identity and its filename: `2025.md`, `2025-10.md`, or
`2025-10-12.md`, filed under `log/<year>/` or `log/<year>/<month>/`. Only one log entry may exist for
each exact date. The first heading is the display title, so the filename stays a date.

Open the **Log** section to see the calendar and the collapsed year tree. **Today's entry** opens
today's page in read mode, or an unsaved draft when the day is free; an empty calendar day or the plus
on an empty month or year row opens the same draft for that date. A **Starter** control in the draft
offers the log cards until the body has content. **Entries** shows only log notes; **Everything** is a
date lens over the whole vault. Changing an entry's date renames and moves it, updates inbound
`log:` links, and rewrites the heading only while it still equals the old generated date title.

## How a capture becomes a project

1. Write one line in the Inbox. The first line becomes the note's name and title.
2. Open the capture and choose **Process**. Pick an outcome: Trash, Later, Reference, Project,
   Log entry, Append step, or Done now.
3. A Project outcome asks for an optional status and due date. The capture moves to `projects/` and
   its body becomes the project body.
4. Open the project and add steps such as `- [ ] Draft the checklist`. The first unchecked step in
   document order is the project's next step.

## Names and links

A note's filename stem is its identity. Renaming the file renames the note, and other notes reach it
by that name. The display title comes from the first level-1 heading in the body, so a filename and a
heading may differ.

Link to a reference or capture with `[Label](<note:Name>)`, to a project with
`[Label](<project:Name>)`, or to a log entry with `[Label](<log:2025-10-12>)`. Use angle brackets when
the name contains spaces so the destination stays unambiguous.

## Working by hand

Nothing here is hidden. Edit any note in a text editor; Afanes reindexes the folder when it opens.
Move a note to `trash/` to stop seeing it. This guide is an ordinary reference note: rename it, edit
it, or move it to `trash/` whenever you no longer need it.
