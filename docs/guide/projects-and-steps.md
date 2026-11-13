# 🎯 Projects and steps

A project is an outcome whose body holds the steps that advance it. The Projects group keeps those
outcomes visible, and the page renders the steps where you read them.

:::{admonition} tl;dr
:class: note

A project's next step is its first unchecked task-list item in document order. Steps belong to the
project whose body contains them; links between notes do not create steps.
:::

```{image} ../_static/screenshots/project-page.png
:alt: A project page with status and due date, a step card, and calendar and person actions
:class: screenshot
```

## 📊 Project groups

The Projects group lists every parsed project under **Active**, **Waiting**, **Later**, and **Closed**.
A project without a status is active. `done`, `cancelled`, and `archived` projects are closed, and the
Closed group starts collapsed.

Each project row shows its status, optional due date, count of open steps, and next step. The next
step leads the row in body text; status, due date, and open-step count share one muted metadata line
under it. An open step is an unchecked task-list item in the project body; checked steps are not
counted. The next step is rendered Markdown, so links and emphasis appear as labels rather than raw
source; raw Markdown appears only in edit mode.

## ➡️ The next step

The next step is the first unchecked step in document order. Dates and owners never reorder the steps
or change which step is next. When the first unchecked step has an owner, the row marks it as waiting.

Steps belong to a project by containment: the project whose body holds the task-list item owns it. A
body link to a project does not create a step, and a project may have no steps at all.

:::{important} Remember
Steps have no filename, identity, or reference namespace. They live only inside the project body.
:::

## 🙋 Owner and requester

A project can record two roles. The **owner** is the person or team accountable for delivering the
project; the **requester** is the person or group that asked for it. They live in the project
frontmatter as `owner` and `asked_by` and appear in the header in that order, after the status and
before the due date. Set or clear each one in edit mode with the **Owner** and **Asked by** fields, or
from read mode with the owner and requester actions beside the names. Both fields are offered only for
projects and suggest names from the vault while still accepting free text.

Both values are metadata references in the `note:` namespace. They resolve to the note with that name,
so it appears under **Owned projects** or **Requested projects** on that page, the name is searchable
and clickable, and renaming the named note rewrites the value. A value that matches no note stays in
the file and is shown as a broken link. Neither role changes the project's status, group, or next step.

## ✅ Completing steps

Checking every step does not close the project, and closing a project does not change its steps. Adding,
ticking, or removing a step updates the workspace after the next scan or save.

In read mode, a project renders as one step-aware body. Prose stays Markdown, and each contiguous task
list becomes an accent card of step rows with the step text, checked state, owners, plan and actual
dates, and tags. Metadata comments are hidden from the rendered text.

Every step row keeps a calendar action and a person action visible. They are understated until hover or
keyboard focus and remain reachable with touch. The calendar action sets or clears the step's plan date;
the person action adds or removes owners, suggesting names from notes in the vault.

Ticking or unticking a step, or editing its plan or owners, rewrites only that line atomically and
leaves every other byte of the file unchanged. A project's own due date is not tied to any step: read
mode shows the status and due date under the title, and its calendar action sets or clears `due_date`
in the frontmatter without touching the body.

A body shape that cannot be split safely, such as a mixed list or a task list inside a blockquote,
stays ordinary Markdown, so nothing is dropped or rewritten.

## 🏷️ Step metadata

A step may end with one metadata comment made of a flow-style YAML object:

```markdown
- [ ] Call the plumber <!-- {owners: [Ada], plan: 2026-11-20, actual: 2026-11-14, tags: [phone]} -->
```

The comment must be the last content on the line and the line must end with `-->`. Text after the
comment makes it prose. Every key is optional, and a comment without a mapping is prose. Unknown keys
are preserved when the step is rewritten. A malformed comment or invalid value drops only that key,
keeps the note readable, and reports the line.

A value containing `--` cannot appear inside an HTML comment, so the app reports it instead of writing
invalid metadata. Step owners resolve through the same catalog as `note:` references.

## 🧭 See also

- [Workspace and browser](workspace.md)
- [Vault format](../reference/vault-format.md)
- [Your first five minutes](../getting-started/capture-clarify-review.md)
