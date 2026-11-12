# 🗂️ Workspace and browser

The workspace keeps a navigation browser beside the page pane. The browser is the map of the vault: it
groups every parsed note, filters the active section, and opens a note without changing where you are.

:::{admonition} tl;dr
:class: note

The browser has one group per kind of note. A note appears in exactly one group, and anything under
`trash/` or `templates/` is absent. Search filters the group you are looking at.
:::

```{image} ../_static/screenshots/workspace.png
:alt: The Afanes workspace with the browser groups, search field, and a capture open in the page pane
:class: screenshot
```

## 🧭 Browser groups

| Group | Contains |
| --- | --- |
| **Inbox** | Captures under `inbox/`, newest first |
| **Projects** | Project notes, grouped by status |
| **References** | Reference notes, grouped by their category label; uncategorized references appear under the plain **References** heading |
| **Needs attention** | Parsed `type: note` notes found outside `inbox/` |
| **Unreadable notes** | Files that could not be parsed; selecting one opens raw rescue mode |

A capture under `inbox/` appears only under **Inbox**. A note under `trash/` appears nowhere, and a
file under `templates/` is a template card rather than a note. Selecting an entry opens it in the page
pane without changing the browser section.

The **References** section also offers **New reference**. The dialog asks for a name and a template
card or Empty, writes the note immediately, and opens it in edit mode. See
[References and categories](references-and-categories.md) for the creation rules.

**Needs attention** exists because a capture outside the Inbox cannot be processed. Move it back to the
Inbox or clarify it by editing its frontmatter by hand. **Unreadable notes** opens the complete file in
raw rescue mode so the text is never lost.

## 🔍 Search

The search field filters the active section by display title, identity, prose body text, and step text.
Matching ignores case, Unicode form, and repeated whitespace. Step metadata comments are excluded, so
an owner name or date inside a comment is not a search result.

## ✍️ Capture field

The capture field stays at the top of the workspace. It behaves exactly like the Inbox composer: the
first non-blank line becomes the filename and heading, and the note is written under `inbox/` with only
`type: note`.

## 🧭 See also

- [Inbox](inbox.md)
- [Projects and steps](projects-and-steps.md)
- [References and categories](references-and-categories.md)
- [Understand the vault format](../reference/vault-format.md)
