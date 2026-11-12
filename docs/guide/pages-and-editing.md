# ✍️ Pages and editing

Select a note in the browser to open it in the page pane. Read mode shows the display title and the
rendered Markdown body. Choose **Edit** to change the body and the labels that control how the note is
classified.

:::{admonition} tl;dr
:class: note

The body is ordinary Markdown. Labels are type, category, status, and due date. Afanes compares the
file before every write and stops if another program changed it.
:::

## 📖 Reading a page

Read mode renders the display title and the Markdown body. Tapping an internal reference opens its page.
External links, attachments, and unsafe destinations do nothing. **Back** returns through the pages you
opened, whether they came from the browser or a link.

A project renders as one step-aware body. Prose stays Markdown, and task lists become interactive step
rows. See [Projects and steps](projects-and-steps.md) for the step actions.

## ✏️ Editing labels

Choose **Edit** to change the raw Markdown body and the labels:

- **Type**: `note`, `reference`, or `project`.
- **Category**: offered only for references; accepts any label.
- **Status**: choices follow the selected type.
- **Due date**: offered only for projects.

The body includes its level-1 heading, which is the display title, and project steps with their
metadata. There are no `people` or `project` fields.

Changing a reference's category previews its new folder and moves the file only after confirmation.
See [References and categories](references-and-categories.md) for the move rules.

Changing the type between the document family (`note` or `reference`) and `project` previews the
inbound references that would become unresolved and requires confirmation. No reference is retargeted
automatically. A change between `note` and `reference` shares the `note` scheme and needs no
confirmation.

## 💾 Autosave and conflicts

A dirty draft is written roughly every 30 seconds and when you choose **Done**, press **Back**, or open
another page. Before every write, Afanes compares the file with the version it read.

If another program changed the file, the save stops and the page offers to reload the file or overwrite
it with your version. If the file was moved or deleted, the page offers to recreate it or discard the
draft.

:::{warning}
Overwriting a conflict discards the other program's edit to that file. Reload when the other edit is
the one you want to keep.
:::

## 🛟 Raw rescue mode

A note whose frontmatter cannot be parsed opens in raw rescue mode. The complete file text is editable
and labels are unavailable. Saving writes exactly what you typed; once the text parses, the normal
editor returns. Unreadable notes are listed in the browser's **Unreadable notes** section and can be
opened from there.

## 🔀 Rename and trash

Rename and Move to trash are available in read mode. Both show their affected references before
confirming.

A rename updates the first heading only when it still matches the old identity; a custom heading is
preserved. Trashed pages move under `trash/`, and their inbound references become unresolved until a
page with that name appears again.

:::{warning}
Renaming or moving a page changes how other notes resolve its name. Review the affected references in
the confirmation before you commit.
:::

## 🧭 See also

- [Workspace and browser](workspace.md)
- [References and categories](references-and-categories.md)
- [Vault format](../reference/vault-format.md)
