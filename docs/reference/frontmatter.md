# 🏷️ Frontmatter

Frontmatter is the optional block between `---` lines at the start of a note. It carries the metadata
Afanes uses to classify the note; the rest of the file is ordinary Markdown.

:::{admonition} tl;dr
:class: note

Only the recognized keys are `type`, `date`, `category`, `status`, `due_date`, `asked_by`, and
`owner`. Unknown keys are preserved, and a missing status means the default for that note type.
:::

## 🧾 Keys

| Key | Valid on | Values |
| --- | --- | --- |
| `type` | every note | `note`, `reference`, `project`, or `log` |
| `date` | every note | an ISO calendar value: `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` |
| `category` | references only | any non-empty single folder label; case is preserved |
| `status` | projects and references | projects: `active`, `waiting`, `done`, `cancelled`, `archived`, `later`; references: `later`, `archived`, or absent |
| `due_date` | projects only | a calendar date written as `YYYY-MM-DD` |
| `asked_by` | projects only | a single non-empty name, treated as a metadata reference |
| `owner` | projects only | a single non-empty name or team, treated as a metadata reference |

Unknown keys are preserved when Afanes rewrites a note. A null `status` or `due_date` is treated as
absent on every note type, including notes and log entries where the key is otherwise forbidden. The
other recognized keys do not accept null. A due date is a date, not a timestamp.

## 🏷️ Type

- `note` is an unclarified capture. It belongs in `inbox/` and means "not clarified yet".
- `reference` is non-actionable knowledge. It may declare a category label; people are references with
  `category: person`, not a separate type.
- `project` is an outcome whose body is a checklist. Each task-list item is a step.
- `log` is a dated diary entry. Its `date` is its identity and its filename.

A capture has no status; `status: inbox` is not valid because the folder is the queue.

### 📓 Log entries

A log entry is a dated page. Its `date` is also its identity: `2025.md`, `2025-10.md`, or
`2025-10-12.md`, filed under `log/<year>/` or `log/<year>/<month>/`. Only one log entry may exist for
each exact date. A log entry has no category, status, due date, requester, or owner. Link to it with
`<log:2025-10-12>`. Changing its date renames and moves it and rewrites inbound `log:` links; the
heading stays as written.

## 📅 Date

Every note may declare a `date`. It is the day, month, or year the note belongs to in the archive and
the Log section. Write it in ISO form; the number of parts selects the precision:

```yaml
date: "2025"          # the whole year
date: "2025-10"       # the whole month
date: "2025-10-12"    # one day
```

A date is a calendar value, not a timestamp. It never carries a time or timezone. A malformed value
stays in the file, keeps the note visible as **Undated**, and shows a warning in the editor until it
is corrected. `date` is independent of a project's `due_date`: the date says where the note belongs
in the archive, while the due date says when the work is due.

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

## 🙋 Asked by

`asked_by` is valid only on projects. It records the person or group that requested the project and is
shown in the project meta row. The value is one plain name in the file. The application treats it as a
metadata reference: the name resolves to the note with that name, so its page lists the project under
**Requested Projects**, the name is searchable and clickable, and renaming the named note rewrites the
value. A name that matches no note stays in the file and appears as a broken link until you create the
note.

## 🧑‍💻 Owner

`owner` is valid only on projects. It records the person or team accountable for delivering the project
and is shown before **Asked by** in the project meta row. The value is one plain name in the file. Like
`asked_by`, it is a metadata reference: the name resolves to the note with that name, its page lists the
project under **Owned Projects**, the name is searchable and clickable, and renaming the named note
rewrites the value. The owner is display-only; it does not change the project's status, group, next
step, or review state.

## 🚫 Retired values

Notes declaring `type: action`, links using `person:Name`, and notes carrying the retired `people` or
`project` frontmatter keys are validation errors. They appear under **Unreadable Notes** and open in
raw rescue mode without being rewritten. There is no automatic migration; create a one-step project
for an action, move its work into the project body as a step, and rewrite `person:Name` links as
`note:Name`. A `category: person` reference remains valid.

## 🧭 See also

- [Vault format](vault-format.md)
- [Step metadata](step-metadata.md)
- [References and categories](../guide/references-and-categories.md)
