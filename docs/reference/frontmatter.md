# 🏷️ Frontmatter

Frontmatter is the optional block between `---` lines at the start of a note. It carries the metadata
Afanes uses to classify the note; the rest of the file is ordinary Markdown.

:::{admonition} tl;dr
:class: note

Only the recognized keys are `type`, `date`, `category`, `status`, `due_date`, `asked_by`, `owner`,
and `reminder`. Unknown keys are preserved, and a missing status means the default for that note type.
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
| `reminder` | references, projects, and log entries | one optional schedule mapping; see [Reminder](#reminder-key) |

Unknown keys are preserved when Afanes rewrites a note. A null `status` or `due_date` is treated as
absent on every note type, including notes and log entries where the key is otherwise forbidden. The
other recognized keys do not accept null. A due date is a date, not a timestamp.

A note under `trash/` adds `trashed_from` (its vault-relative birthplace) and `trashed_on` (the local
calendar day it was trashed). These two keys are trash metadata, not editable labels; restoring the
note removes them. See [Vault format](vault-format.md).

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

The page's calendar action writes the same ISO values and never stores a localized form. A date is a
calendar value, not a timestamp. It never carries a time or timezone. A malformed value
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

`due_date` is valid only on projects and must be a calendar date written as `YYYY-MM-DD`. The page's
calendar action writes that day-only form. It is not
tied to any step. A project may have a due date without steps, and a step may have a plan date without
the project having a due date.

(reminder-key)=
## ⏰ Reminder

A reference, project, or log entry may declare one `reminder` mapping. A capture cannot carry an
effective reminder; the key is ignored with a warning and left in the file. The mapping contains a
`zone`, exactly one of `recurrence` or `once`, and an optional `handled` instant.

A recurring reminder names one kind and one or more 24-hour times:

```yaml
reminder:
  zone: America/Mexico_City
  recurrence:
    kind: weekdays
    weekdays: [mon, wed, fri]
    times: ["09:00", "17:30"]
```

The kinds are `daily`, `weekdays` with one or more `weekdays`, `month_day` with `day` from 1 to 31,
`nth_weekday` with `nth` from 1 to 5 and a `weekday`, `last_day`, and `last_weekday` with a `weekday`.
Weekdays are written `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, or `sun`, and times use `HH:MM` on the
24-hour clock. An `nth_weekday` of 5 or a `month_day` of 29 through 31 skips months that do not contain
that date.

A one-shot stores one local date and time instead:

```yaml
reminder:
  zone: America/Mexico_City
  once: 2026-11-20T09:00
```

The one-shot date portion offers the shared day-only calendar action. The time stays typed, and
choosing a new date keeps it. The stored value remains an ISO date followed by a 24-hour time.

`zone` is an IANA time-zone name such as `America/Mexico_City`, `Europe/Madrid`, or `Asia/Tokyo`. When
the key is absent, the computer's current zone is used. An unknown zone is a warning. A daylight-saving
gap skips that occurrence, and a repeated hour produces at most one entry.

`handled` is the absolute instant of the last dismissed occurrence:

```yaml
reminder:
  zone: America/Mexico_City
  recurrence:
    kind: daily
    times: ["09:00"]
  handled: 2026-11-14T15:00:00+00:00
```

Dismissing writes `handled`; it never changes the body, status, or schedule. Editing the recurrence,
the one-shot, or the zone clears `handled` so the edited schedule starts from its latest occurrence.
Saving the body alone, or saving an unchanged schedule, preserves it. A future `handled` value is
treated as absent so a hand-edited value cannot suppress a reminder indefinitely.

A malformed mapping keeps the page readable, shows a warning, and is preserved exactly as written.
The schedule is ignored until the value is corrected or removed, and opening or scanning the vault
never rewrites it. Unknown keys inside the reminder mapping are preserved. See
[Review](../guide/review.md) for due occurrences and dismissal.

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
