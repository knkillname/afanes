# 📄 Vault format

A vault is a directory of Markdown files with an `afanes.yaml` settings file at its root. A note's
filename stem is its identity and the name that references resolve against. Its display title is the
first level-1 heading in the body, falling back to the filename stem when there is no heading.

:::{admonition} tl;dr
:class: note

Four note types share one Markdown format: `note` for Inbox captures, `reference` for non-actionable
knowledge, `project` for an outcome whose body holds task-list steps, and `log` for dated diary
entries. Folders classify notes; they do not define identity.
:::

## 🗂️ Files and identity

- The filename stem is the note's identity. Renaming the file renames the note.
- The first level-1 heading is the display title. A filename and a heading may differ.
- Directories only classify notes. Moving a note between folders never changes a reference.
- A note belongs to exactly one folder. In normal browsing it has one type group; the Log's
  Everything mode is an additional date lens.
- Notes under `trash/` are excluded from scans, name uniqueness, and reference resolution.
- Files under `templates/` are reference template cards, not notes. They are excluded from scans, the
  browser, name uniqueness, and reference resolution. See [Template cards](template-cards.md).

## 🏷️ Note types

| Type | Meaning | Default location |
| --- | --- | --- |
| `note` | An unclarified capture | `inbox/` |
| `reference` | Non-actionable knowledge, optionally with a `category` label | `reference/` |
| `project` | An outcome with task-list steps in the body | `projects/` |
| `log` | A dated diary entry whose date is its identity | `log/<year>/` or `log/<year>/<month>/` |

People are references with `category: person`, not a separate note type. Categories never select a
reference namespace; every reference uses the `note:` scheme. Log entries use the `log:` scheme.

## 📋 Frontmatter keys

The recognized keys are:

| Key | Valid on | Values |
| --- | --- | --- |
| `type` | every note | `note`, `reference`, `project`, or `log` |
| `date` | every note | an ISO calendar value: `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` |
| `category` | references only | any non-empty single folder label; case is preserved |
| `status` | projects and references | projects: `active`, `waiting`, `done`, `cancelled`, `archived`, `later`; references: `later`, `archived`, or absent |
| `due_date` | projects only | a calendar date written as `YYYY-MM-DD` |
| `asked_by` | projects only | a single non-empty name; a metadata reference |
| `owner` | projects only | a single non-empty name or team; a metadata reference |

Unknown keys are preserved. A capture has no status; `status: inbox` is not valid because the folder is
the queue. A due date is a date, not a timestamp. `asked_by` records who requested the project and
`owner` records who is accountable for it. Both are shown in the project meta row and resolve through
the `note:` catalog, so their pages list the project and rename rewrites the value. See
[Frontmatter](frontmatter.md) for the full key reference.

A note's `date` is an ISO calendar value: `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`. It places the note in
the archive and the Log section and is independent of a project's `due_date`. A malformed date keeps
the note readable and shows it as Undated until it is corrected.

```markdown
---
type: project
status: active
date: 2025-10-12
due_date: 2026-11-30
asked_by: Priya Nair
owner: Sam Rivera
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

## ⚙️ Vault settings file

A vault root contains `afanes.yaml`. The filename is exact and must be a regular UTF-8 file, not a
symbolic link or a directory. The current contents are exactly:

```yaml
schema_version: 1
```

The file records the on-disk vault format, not the Afanes package version. Opening a folder without a
valid file is refused. Opening a versioned vault never creates, changes, or repairs the file, so a
read-only vault with a valid file still opens for browsing.

The file is validated strictly. Extra keys, duplicate keys, malformed YAML, a missing
`schema_version`, a non-integer value, and any version other than `1` are refused. An invalid or
unsupported file is preserved byte for byte; Afanes never guesses, rewrites, or deletes it.

A folder created before this file existed can be adopted. Adoption is offered only for a writable
folder that contains all five default folders: `inbox/`, `trash/`, `reference/`, `projects/`, and
`log/`. Folder names are matched case-insensitively, `templates/` is optional, and extra folders are
allowed. Adoption writes only `afanes.yaml`; it does not create notes, folders, the guide, or template
cards. Use the adoption action in the interface or `afanes vault adopt DIR` on the command line.

The schema version changes only when the on-disk vault contract changes. Before 1.0, a schema change
may refuse older vaults. From 1.0 onward, every schema bump ships with a forward migration. A newer
schema is always refused by an older application, and downgrades are not supported. The application
preferences file is separate and lives outside the vault.

## 📁 Default layout

```text
vault/
  afanes.yaml     schema version
  inbox/          captures
  trash/          recoverable discards
  reference/      non-actionable notes
    <category>/   optional category folders, such as reference/person/
  projects/       project notes
  log/            dated diary entries
    2025/10/      year and month folders selected by the entry date
  templates/      reference template cards, not notes
```

These folders are conveniences, not requirements. Existing notes anywhere in the vault still resolve.
Folders are created only when a write needs them. A newly created vault also contains `afanes.yaml`,
the `Getting started` guide, the eight template cards under `templates/`, and the chosen template's
notes; a vault opened later is never seeded or repaired.

:::{warning}
`templates/` is reserved. If an existing vault already used that folder for ordinary notes, those
notes stop appearing in the browser and search because the folder is now read as template cards. Move
them out of `templates/` to restore them.
:::

A categorized reference is filed under `reference/<category-folder>/`, where the folder is derived
from the label through the cross-platform filename policy. An existing case variant is reused.

## 📓 Log entries

A log entry is a dated page. Its `date` is its identity and its filename:

```text
log/2025/2025.md                    # whole year
log/2025/10/2025-10.md              # whole month
log/2025/10/2025-10-12.md           # one day
```

Only one log entry may exist for each exact date. The entry's first level-1 heading is its display
title and is not part of its identity. Link to it with `[Tuesday](<log:2025-10-12>)`. A log entry has
no `category`, `status`, `due_date`, `asked_by`, or `owner`.

Changing a log entry's date renames and moves it and rewrites inbound `log:` links automatically. A
note that changes type into or out of `log` is moved and renamed the same way; a note without a date
cannot become a log entry.

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
