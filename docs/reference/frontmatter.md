# 🏷️ Frontmatter

Frontmatter is the optional block between `---` lines at the start of a note. It carries the metadata
Afanes uses to classify the note; the rest of the file is ordinary Markdown.

:::{admonition} tl;dr
:class: note

Only four keys are recognized: `type`, `category`, `status`, and `due_date`. Unknown keys are
preserved, and a missing status means the default for that note type.
:::

## 🧾 Keys

| Key | Valid on | Values |
| --- | --- | --- |
| `type` | every note | `note`, `reference`, or `project` |
| `category` | references only | any non-empty single folder label; case is preserved |
| `status` | projects and references | projects: `active`, `waiting`, `done`, `cancelled`, `archived`, `later`; references: `later`, `archived`, or absent |
| `due_date` | projects only | a calendar date written as `YYYY-MM-DD` |

Unknown keys are preserved when Afanes rewrites a note. A due date is a date, not a timestamp.

## 🏷️ Type

- `note` is an unclarified capture. It belongs in `inbox/` and means "not clarified yet".
- `reference` is non-actionable knowledge. It may declare a category label; people are references with
  `category: person`, not a separate type.
- `project` is an outcome whose body is a checklist. Each task-list item is a step.

A capture has no status; `status: inbox` is not valid because the folder is the queue.

## 🗂️ Category

`category` is valid only on references and accepts any non-empty single folder label. Case is
preserved. The label groups references in the browser and chooses a default folder under `reference/`;
it never selects a reference namespace. See [References and categories](../guide/references-and-categories.md).

## 🚦 Status

A project without a status is active. `done`, `cancelled`, and `archived` projects are closed.
`later` defers a project without closing it. A reference may be `later`, `archived`, or have no status.

## 📅 Due date

`due_date` is valid only on projects and must be a calendar date written as `YYYY-MM-DD`. It is not
tied to any step. A project may have a due date without steps, and a step may have a plan date without
the project having a due date.

## 🚫 Retired values

Notes declaring `type: action`, links using `person:Name`, and notes carrying the retired `people` or
`project` frontmatter keys are validation errors. They appear under **Unreadable notes** and open in
raw rescue mode without being rewritten. There is no automatic migration; create a one-step project
for an action, move its work into the project body as a step, and rewrite `person:Name` links as
`note:Name`. A `category: person` reference remains valid.

## 🧭 See also

- [Vault format](vault-format.md)
- [Step metadata](step-metadata.md)
- [References and categories](../guide/references-and-categories.md)
