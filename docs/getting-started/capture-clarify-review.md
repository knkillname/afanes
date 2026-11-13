# 🚀 Your first five minutes

This is the shortest path through Afanes: capture a thought, clarify it, work the resulting project,
and review what is due. The full guide explains each surface in detail.

:::{admonition} tl;dr
:class: note

Capture one line in the Inbox. Open it and choose **Process** to turn it into a project or reference.
Work the project's steps, then let **Review** show what needs attention.
:::

## 🧠 Capture a thought

The capture field at the top of the workspace writes a note under `inbox/`. The first non-blank line
becomes the filename and the heading. All other text is preserved.

Capturing `Call Ada` followed by `about the invoice` writes:

```markdown
---
type: note
---

# Call Ada
about the invoice
```

The frontmatter contains only `type: note`. No status, category, project, owner, or due date is
inferred. Clarification is a separate step.

:::{tip}
The first non-blank line is the identity. Write the thought as if it were the note's title, and put the
detail on the following lines.
:::

## 🔄 Clarify it

Select the capture in the Inbox and choose **Process**. The wizard asks what the capture should become:

- **Trash** moves it to `trash/` without rewriting it.
- **Later** keeps it as a reference with `status: later`.
- **Reference** keeps it as an uncategorized reference with no status.
- **Project** turns it into a project with a status, optional due date, owner, and requester.
- **Append step** adds the capture as a step of an existing project and moves the capture to trash.
- **Done now** writes a completed one-step project with `status: done` and optional owner and requester.

Project and Done now offer optional **Owner** and **Asked by** fields that suggest names already in the
vault. A new name is saved as written and can be created later by clicking it on the project page.

The preview shows the destination and, when the outcome changes scheme, how many inbound references
will become unresolved. Append step suggests existing projects by title or identity and stores the
identity.

:::{warning}
Moving a note to `trash/` does not rewrite the notes that refer to it. Those links stay unresolved
until a page with that name appears again. Moving the note back restores them.
:::

## 🎯 Work the project

Open the project and add task-list steps such as `- [ ] Draft the checklist`. The first unchecked step
in document order is the project's next step. Ticking a step writes `[x]` and records the date; the
calendar action sets or clears the plan date; the person action manages owners.

A project may have no steps at all. Checking every step does not close the project, and closing a
project does not change its steps. See the [vault format](../reference/vault-format.md) for the note
and step syntax.

## ✅ Review what is due

The **Review** entry counts pending Inbox captures, due or overdue own steps, waiting steps, and open
projects with no open step. At launch, a digest appears when own work is due or overdue. Selecting
Review with nothing pending shows the zero state and starts no session.

A review never classifies a capture, changes a project status, checks a step, or creates a note without
an explicit choice. The session is not saved across restarts; the count is always recomputed from the
vault.

:::{important} Remember
Opening or scanning a vault never creates a file or folder. Afanes writes only when you capture,
clarify, edit, or act on a step.
:::

## 🧭 Next steps

- [Create or open your first vault](first-vault.md)
- [Understand the vault format](../reference/vault-format.md)
- [Browse the templates](../reference/templates.md)
