# 📄 Vault format

A vault is a directory of Markdown files. A note's filename stem is its identity and the name that
references resolve against. Its display title is the first level-1 heading in the body, falling back to
the filename stem when there is no heading.

:::{admonition} tl;dr
:class: note

Three note types share one Markdown format: `note` for Inbox captures, `reference` for non-actionable
knowledge, and `project` for an outcome whose body holds task-list steps. Folders classify notes; they
do not define identity.
:::

## 🗂️ Files and identity

- The filename stem is the note's identity. Renaming the file renames the note.
- The first level-1 heading is the display title. A filename and a heading may differ.
- Directories only classify notes. Moving a note between folders never changes a reference.
- A note belongs to exactly one folder, and the browser shows it in exactly one group.
- Notes under `trash/` are excluded from scans, name uniqueness, and reference resolution.

## 🏷️ Note types

| Type | Meaning | Default location |
| --- | --- | --- |
| `note` | An unclarified capture | `inbox/` |
| `reference` | Non-actionable knowledge, optionally with a `category` label | `reference/` |
| `project` | An outcome with task-list steps in the body | `projects/` |

People are references with `category: person`, not a separate note type. Categories never select a
reference namespace; every reference uses the `note:` scheme.

## 📋 Frontmatter keys

The recognized keys are:

| Key | Valid on | Values |
| --- | --- | --- |
| `type` | every note | `note`, `reference`, or `project` |
| `category` | references only | any non-empty single folder label; case is preserved |
| `status` | projects and references | projects: `active`, `waiting`, `done`, `cancelled`, `archived`, `later`; references: `later`, `archived`, or absent |
| `due_date` | projects only | a calendar date written as `YYYY-MM-DD` |

Unknown keys are preserved. A capture has no status; `status: inbox` is not valid because the folder is
the queue. A due date is a date, not a timestamp. See [Frontmatter](frontmatter.md) for the full key
reference.

```markdown
---
type: project
status: active
due_date: 2026-11-30
---

# Release migration checklist

- [ ] Draft the checklist <!-- {plan: 2026-11-20} -->
- [ ] Ask [Ada Lovelace](<note:Ada Lovelace>) to review it <!-- {owners: [Ada Lovelace], tags: [review]} -->
- [x] Open the tracking page <!-- {plan: 2026-11-14, actual: 2026-11-15} -->
```

```markdown
---
type: reference
category: person
---

# Ada Lovelace

Ada's contact page.
```

## 📁 Default layout

```text
vault/
  inbox/          captures
  trash/          recoverable discards
  reference/      non-actionable notes
    <category>/   optional category folders, such as reference/person/
  projects/       project notes
```

These folders are conveniences, not requirements. Existing notes anywhere in the vault still resolve.
Folders are created only when a write needs them. A newly created vault also contains the `Getting
started` guide and the chosen template's notes; a vault opened later is never seeded or repaired.

A categorized reference is filed under `reference/<category-folder>/`, where the folder is derived
from the label through the cross-platform filename policy. An existing case variant is reused.

## 🧩 Steps in a project body

A task list item is a list item whose content begins with `[ ]` or `[x]`. Only a project body
contributes steps; checkboxes in any other note are ordinary Markdown. Ticking a step writes `[x]` and
adds `actual: <today>`; unticking removes `actual` and keeps `plan`.

Steps have no filename, identity, or reference namespace. See [Step metadata](step-metadata.md) for the
trailing comment format.

## 🗑️ Trash

Moving a note to `trash/` makes its inbound references unresolved without rewriting the referring
notes. Moving the note back restores it and resolves those references again. Trash is a folder
convention, not a hidden database state.

## 🧭 See also

- [Create or open your first vault](../getting-started/first-vault.md)
- [Vault templates](templates.md)
