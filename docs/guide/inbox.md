# 📥 Inbox

Captures live in `inbox/`. A capture is a thought that has not been clarified yet: it declares
`type: note` and nothing else. Clarification is a separate action, so the Inbox stays a queue rather
than a decision.

:::{admonition} tl;dr
:class: note

Type one line in the composer at the top of the Inbox browser region, or press **Ctrl+N** from any
destination. The first non-blank line becomes the filename and heading. Open the capture when you are
ready to process it.
:::

## ✍️ Capture a thought

Capturing a thought uses the first non-blank line as the filename and writes that line as a level-1
heading at the start of the body. All other text is preserved, even when the filename had to sanitize
characters that are unsafe on some platforms.

Capturing `Call Ada` followed by `about the invoice` writes:

```markdown
---
type: note
---

# Call Ada
about the invoice
```

The frontmatter contains only `type: note`. No status, category, project, owner, or due date is
inferred. A blank capture is reported in a transient toast and the composer keeps its text; a scan
failure that remains true stays in a banner.

:::{tip}
The first non-blank line is the identity. Make it the title you will recognize later, and put the
detail on the following lines.
:::

## 🗂️ How the Inbox is ordered

The **Inbox** group lists every note under `inbox/`, newest first. Each row shows the display title
with the vault-relative path as the secondary line. A note whose body has no level-1 heading falls back
to its filename stem as the display title.

## 📄 Open and edit

Select a capture to open it in the detail region. Read its body or choose **Edit** to change it.
**Process…** remains available for Inbox captures. Moving a capture out of `inbox/` by hand leaves it
under **Needs Attention**; use the Inbox or the Processing Wizard instead.

:::{warning}
A capture outside `inbox/` cannot be processed. The **Needs Attention** group lists those notes; move
them back to the Inbox or classify them by hand.
:::

## 🧭 See also

- [Your first five minutes](../getting-started/capture-clarify-review.md)
- [Workspace and browser](workspace.md)
- [Vault format](../reference/vault-format.md)
