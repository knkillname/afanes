# 🗂️ Workspace and browser

The workspace keeps a navigation browser beside the page pane. The browser is the map of the vault: it
groups every parsed note, filters the active section, and opens a note without changing where you are.
The vault path and vault actions sit in a status bar along the bottom, leaving the note canvas the
full height of the window.

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
| **Log** | Dated diary entries, with a month calendar and a collapsed year/month/day tree |
| **Needs attention** | Parsed `type: note` notes found outside `inbox/` |
| **Unreadable notes** | Files that could not be parsed; selecting one opens raw rescue mode |

A capture under `inbox/` appears only under **Inbox**. A log entry appears under **Log**. A note under
`trash/` appears nowhere, and a file under `templates/` is a template card rather than a note. Selecting
an entry opens it in the page pane without changing the browser section.

The **Log** section offers a calendar and a collapsed date tree instead of a flat list. **Entries** shows
only log notes; **Everything** is a date lens over every parsed note. **Today's entry** opens or creates
today's page, and the calendar and tree controls create entries for a chosen day, month, or year. See
[Log](log.md) for the calendar marks, date rules, and linking.

The **References** section also offers **New reference**. The dialog asks for a name and a template
card or Empty, writes the note immediately, and opens it in edit mode. See
[References and categories](references-and-categories.md) for the creation rules.

**Needs attention** exists because a capture outside the Inbox cannot be processed. Move it back to the
Inbox or clarify it by editing its frontmatter by hand. **Unreadable notes** opens the complete file in
raw rescue mode so the text is never lost.

## 🔍 Search

The search field filters the active section by display title, identity, prose body text, and step text.
Matching ignores case, Unicode form, and repeated whitespace. Step metadata comments are excluded, so
an owner name or date inside a comment is not a search result. In the **Log**, the same query filters
both the date tree and the calendar accents.

## ✍️ Capture field

The capture field stays at the top of the workspace. It behaves exactly like the Inbox composer: the
first non-blank line becomes the filename and heading, and the note is written under `inbox/` with only
`type: note`.

## 🎨 Appearance

The interface follows the operating system's light or dark appearance and has no separate in-app
switch. In both modes the page, the browser sidebar, and the content cards use distinct surface steps
with a thin outline, so regions stay separated instead of blending together.

A familiar engineering-tool palette keeps the interface recognizable: white surfaces separated by
thin borders, one blue accent, and green filled primary buttons. The note canvas stays white in both
the page and edit modes. Blue marks selection, links, and keyboard focus; green marks primary
actions; the two never swap roles. Due-work notices use a warm attention surface. Each browser
section tints only its leading icon, and the active entry also shows an accent edge, so the section
stays identifiable without relying on color alone. Typography uses the platform font in one family;
hierarchy comes from size, weight, and the muted metadata color.

## 🧭 See also

- [Inbox](inbox.md)
- [Projects and steps](projects-and-steps.md)
- [References and categories](references-and-categories.md)
- [Understand the vault format](../reference/vault-format.md)
