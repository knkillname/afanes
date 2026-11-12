# 🔄 Processing

Select a capture in the Inbox and choose **Process**. The Processing Wizard asks what the capture
should become. It never chooses an outcome from the capture text.

:::{admonition} tl;dr
:class: note

Processing is explicit and confirmed. Every outcome writes the classified note first and then moves it
out of the Inbox, so a failed move leaves the capture available for a retry.
:::

```{image} ../_static/screenshots/processing.png
:alt: The Process capture wizard with Project selected, a status, and a due date field
:class: screenshot
```

## 🎛️ Outcomes

| Outcome | Result |
| --- | --- |
| **Trash** | Moves the capture to `trash/` without rewriting it |
| **Later** | Keeps it as a reference with `status: later` |
| **Reference** | Keeps it as an uncategorized reference with no status |
| **Project** | Turns it into a project with a status and optional due date |
| **Append step** | Adds the capture as a step of an existing project and moves the capture to trash |
| **Done now** | Writes a completed one-step project with `status: done` |

Task list items already in the capture body become steps when the outcome is a project. A project may
start empty.

The preview shows the destination and, when the outcome changes scheme, how many inbound references
will become unresolved.

## 🔗 Append step

Append step suggests existing projects by display title or identity and stores the identity. Text that
matches no project is rejected. The target project is written first and the capture is moved to trash
afterward.

A failed project write leaves both notes unchanged. If the write succeeds and the trash move fails, the
step is already present; retrying the same plan detects the existing step and does not duplicate it.

:::{warning}
Append step moves the capture to `trash/` after writing the project. If you are unsure, choose
**Project** instead and add the step to the new project yourself.
:::

## 🗑️ Trash and retry

Trash moves the note without rewriting any referring note. Moving it back restores it and resolves its
inbound references again.

Every other outcome writes the classified frontmatter atomically and then moves the note out of
`inbox/`. A failed move leaves the note in the Inbox so the same plan can be retried.

:::{important} Remember
Processing never infers a status, category, project, owner, or due date from the capture text. You
choose every label.
:::

## 🧭 See also

- [Inbox](inbox.md)
- [Projects and steps](projects-and-steps.md)
- [Vault format](../reference/vault-format.md)
