# 🗂️ Template cards

A template card is a Markdown file in the vault's `templates/` folder. A reference card supplies a
category and a starter body, so creating a person, place, or process starts with the fields you always
need. A log card supplies only a starter body for a dated log entry.

:::{admonition} tl;dr
:class: note

Template cards live in `templates/` at the vault root. Add, edit, or delete them with any text editor.
Processing, the References section, and a new log draft offer the valid cards plus an **Empty** option.
:::

## 📁 The templates folder

`templates/` is a convention, not a note folder. Files under it are not scanned, do not appear in the
browser or search, do not participate in name uniqueness, and never resolve as references. Opening a
vault does not create the folder, and deleting a card is never undone.

A card file must be a `.md` file directly inside `templates/`. Nested folders are ignored. Any other
file type is ignored.

## 🏷️ Card format

```markdown
---
type: reference
category: person
title: Person
description: A contact, colleague, or someone you deal with.
---

## Contact

- Email:
- Phone:
```

| Key | Required | Meaning |
| --- | --- | --- |
| `type` | Yes | `reference` or `log`. |
| `category` | Reference cards only | Folder label applied to the new note, such as `person` or `place`. A log card must not declare it. |
| `title` | No | Picker label. Falls back to the file name. |
| `description` | No | One-line explanation shown in the picker. |

The Markdown after the frontmatter is the starter body. It is appended below the note's title when a
note is created from the card. The **Starter** control in a new log draft appends the card's body below
the generated heading. The body may be empty, but it must not contain a level-1 heading, because the
note's own title supplies that heading.

A card must not declare `status` or `due_date`. Those keys belong to workflow, not to a reusable
shape.

## 🌱 Seeded cards

Every new vault receives eight editable cards:

| File | Category | Title |
| --- | --- | --- |
| `person.md` | `person` | Person |
| `team.md` | `team` | Team |
| `organization.md` | `organization` | Organization |
| `place.md` | `place` | Place |
| `process.md` | `process` | Process |
| `topic.md` | `topic` | Topic |
| `source.md` | `source` | Source |
| `daily.md` | — | Daily entry |

The Daily entry card declares `type: log` and supplies the `## What happened`, `## What I learned`, and
`## Next` prompts. It does not set a date or a category.

The seeded files are ordinary files from that point on. Edit them, replace them, or delete the ones
you do not use. A new vault is the only time they are written; existing vaults are never seeded on
open.

## 🧭 Empty

The Processing Wizard, the References section, and the Starter control in a new log draft always offer
**Empty**. Empty creates a reference with `category: general` and no starter body. For a log draft,
Empty leaves only the title heading. It is the right choice when no card fits or when you only want a
title.

## ⚠️ Invalid cards

A card that cannot be read, parsed, or validated is skipped. The picker or Starter control still lists
every valid card and names the skipped files in a warning. Nothing is rewritten automatically, so you
can repair the file and reopen the picker.

Invalid cards are also the likeliest explanation when a `templates/` folder from an older vault holds
ordinary notes: that folder is now reserved, so those notes leave the browser and their files are
reported as invalid cards. Move them out of `templates/` to restore them.

## 🧭 See also

- [Vault format](vault-format.md)
- [Vault templates](templates.md)
- [References and categories](../guide/references-and-categories.md)
