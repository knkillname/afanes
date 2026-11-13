# 🔄 Processing

Select a capture in the Inbox and choose **Process…**. The Processing Wizard asks what the capture
should become. It never chooses an outcome from the capture text.

:::{admonition} tl;dr
:class: note

Processing is explicit and confirmed. Every outcome writes the classified note first and then moves it
out of the Inbox, so a failed move leaves the capture available for a retry.
:::

```{image} ../_static/screenshots/processing.png
:alt: The Process capture wizard with Reference selected and a template picker
:class: screenshot
```

## 🎛️ Outcomes

| Outcome | Result |
| --- | --- |
| **Trash** | Moves the capture to `trash/` without rewriting it |
| **Later** | Keeps it as a reference with `status: later`, using the chosen template card or Empty |
| **Reference** | Keeps it as a reference, using the chosen template card or Empty |
| **Project** | Turns it into a project with a status, optional due date, owner, and requester |
| **Log Entry** | Turns it into a dated log entry under `log/`, using the capture's date |
| **Append Step** | Adds the capture as a step of an existing project and moves the capture to trash |
| **Done Now** | Writes a completed one-step project with `status: done` and optional owner and requester |

Task list items already in the capture body become steps when the outcome is a project. A project may
start empty.

Project and Done Now also offer optional **Owner** and **Asked by** fields. Both suggest names already
in the vault and accept a new name typed as-is; the new name is saved on the project and can be created
later by clicking it on the project page. Append Step keeps its current behavior: the appended step gets
no owner, and the project's owner is not copied to it.

The preview shows the destination and, when the outcome changes scheme, how many inbound references
will be affected. **Preview** stays insensitive until an outcome is chosen and its required project
or date is valid. A Log Entry outcome rewrites `note:` links to the new `log:<date>` destination; an
undated capture uses its last-modified date for this conversion. A date that already has a log entry
is refused.

## 🗂️ Template cards

Reference and Later ask which kind of reference you are creating. The **Template** field lists the
valid reference cards from the vault's `templates/` folder plus **Empty**. A card supplies the category
and a starter body; Empty uses `category: general` and adds no starter body. Processing never guesses
the card from the capture text. The Log Entry outcome does not ask for a card and preserves the
capture body.

The starter body is added below the capture text in the same atomic write as the classification. The
preview names the category and says whether a starter body will be added. Invalid cards are skipped
and named in a warning; the valid cards remain available. See
[Template cards](../reference/template-cards.md) for the card format.

Processing finishes on its success panel. It does not open the created note in the page editor, so you
can continue with the next capture or review item.

## 🔗 Append Step

Append Step suggests existing projects by display title or identity and stores the identity. Text that
matches no project is rejected. The target project is written first and the capture is moved to trash
afterward.

A failed project write leaves both notes unchanged. If the write succeeds and the trash move fails, the
step is already present; retrying the same plan detects the existing step and does not duplicate it.

:::{warning}
Append Step moves the capture to `trash/` after writing the project. If you are unsure, choose
**Project** instead and add the step to the new project yourself.
:::

## 🗑️ Trash and retry

The wizard's Trash outcome is applied after you confirm the plan. It moves the note without rewriting
any referring note. The page's Move to Trash action is immediate and offers **Undo** in a toast; Undo
restores the note and resolves its inbound references again while the original path is free.

Every other outcome writes the classified frontmatter atomically and then moves the note out of
`inbox/`. A failed move leaves the note in the Inbox so the same plan can be retried. A failed plan or
apply is reported in a toast while the wizard stays open. If the apply succeeds but the scan refresh
fails, the success state remains and the workspace banner reports the refresh failure.

:::{important} Remember
Processing never infers a status, template card, project, owner, requester, or due date from the
capture text. You choose every label.
:::

## 🧭 See also

- [Inbox](inbox.md)
- [Projects and steps](projects-and-steps.md)
- [Vault format](../reference/vault-format.md)
