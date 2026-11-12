# 📚 References and categories

A reference is something worth keeping that you do not act on: a contact, a place, a topic, a process.
A reference may declare a free-form `category` label that groups it in the browser and selects a
default folder. People are references with `category: person`, not a separate note type.

:::{admonition} tl;dr
:class: note

Categories are labels, not namespaces. Every reference uses the `note:` scheme; the category only
groups the browser and chooses a folder under `reference/`.
:::

## 🏷️ What a reference is

A reference is non-actionable knowledge. It lives under `reference/`, optionally inside one category
folder. A reference may be marked `status: later` or `status: archived`; it may also have no status.

## 🗂️ Categories

The category label is free-form. `person`, `place`, `team`, `process`, `topic`, and `source` are
conventions, not a fixed list. A categorized reference is filed under `reference/<category-folder>/`,
where the folder is derived from the label through the cross-platform filename policy. An existing case
variant is reused.

Changing a reference's category previews its new folder and moves the file only after confirmation. The
name, identity, and inbound references do not change. Cancelling leaves both the category and the file
location unchanged. If a move fails, the note keeps the new category in its old folder; grouping uses
the label, so the drift is invisible in the browser.

## 🔗 Names and links

Use `project:` for project notes and `note:` for every other note, including references in any
category. A note belongs to exactly one scheme. Names are matched case-insensitively, so
`[Ada](<note:ada lovelace>)` resolves to the same note. Categories never select a namespace.

Following a reference that has no page opens a draft. The draft uses the reference scheme to choose its
type and default folder:

| Reference | Type | Default folder |
| --- | --- | --- |
| `note:Quarterly budget` | uncategorized reference | `reference/` |
| `project:Release 1.0` | project | `projects/` |

The draft starts with the reference name as its level-1 heading and is written only after you type body
text or change a label. The filename is the sanitized reference name, used exactly; a collision stops
the first save instead of adding a suffix. If the original name was unsafe as a filename, the first save
offers to rewrite the references that still use it. If the safe name already belongs to a page in the
same scheme, that page opens instead of creating a duplicate.

:::{warning}
Renaming a note or moving it to trash shows the affected references before confirming. A rename updates
the first heading only when it still matches the old identity; a custom heading is preserved.
:::

## 🧭 See also

- [Workspace and browser](workspace.md)
- [Vault format](../reference/vault-format.md)
- [Vault templates](../reference/templates.md)
