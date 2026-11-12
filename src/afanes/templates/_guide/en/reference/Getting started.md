---
type: reference
---

# Getting started

Afanes reads and writes a folder of Markdown files called a vault. Every file is one note. The
first block between `---` lines holds the metadata Afanes uses; the rest of the file is ordinary
Markdown. Nothing is stored anywhere else, so the files stay readable and portable without the
application.

## Three kinds of notes

- **Note** — a thought that has not been clarified yet. Captures live in `inbox/`, and a note may
  only sit there.
- **Reference** — something worth keeping that you do not act on: a contact, a place, a topic, a
  process. References live in `reference/`, optionally inside one category folder.
- **Project** — an outcome that needs more than one action. Projects live in `projects/`, and the
  steps that advance them are checkbox items in the same file.

## Category labels

A reference can declare a `category` key. The label is free-form: it groups references under one
heading in the browser and gives them a folder inside `reference/`. `person`, `place`, `team`,
`process`, `topic`, and `source` are conventions, not a fixed list; write any label that helps you
find the note again.

## Reference template cards

Every new vault includes a `templates/` folder with reference template cards. A card declares a
`category` and a starter body, so choosing it in processing or in the browser creates a reference with
the right folder and the fields you usually need. The seeded cards cover a person, a team, an
organization, a place, a process, a topic, and a source.

The folder is not part of your notes. Files in `templates/` are left out of the browser and out of
searches, and their names never collide with note names. Edit, add, or delete cards with any text
editor; a card removed from the folder stays removed.

## How a capture becomes a project

1. Write one line in the Inbox. The first line becomes the note's name and title.
2. Open the capture and choose **Process**. Pick an outcome: Trash, Later, Reference, Project,
   Append step, or Done now.
3. A Project outcome asks for an optional status and due date. The capture moves to `projects/` and
   its body becomes the project body.
4. Open the project and add steps such as `- [ ] Draft the checklist`. The first unchecked step in
   document order is the project's next step.

## Names and links

A note's filename stem is its identity. Renaming the file renames the note, and other notes reach it
by that name. The display title comes from the first level-1 heading in the body, so a filename and a
heading may differ.

Link to a reference or capture with `[Label](<note:Name>)`, or to a project with
`[Label](<project:Name>)`. Use angle brackets when the name contains spaces so the destination stays
unambiguous.

## Working by hand

Nothing here is hidden. Edit any note in a text editor; Afanes reindexes the folder when it opens.
Move a note to `trash/` to stop seeing it. This guide is an ordinary reference note: rename it, edit
it, or move it to `trash/` whenever you no longer need it.
