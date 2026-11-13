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

The search field filters the active section by display title, identity, prose body text, step text, and
role names: a project's `owner`, its `asked_by`, and the owners of its steps. Matching ignores case,
Unicode form, and repeated whitespace. Other step metadata and unknown frontmatter keys are excluded,
so a plan date or tag inside a comment is not a search result. In the **Log**, the same query filters
both the date tree and the calendar accents.

## ✍️ Capture field

The capture field stays at the top of the workspace. It behaves exactly like the Inbox composer: the
first non-blank line becomes the filename and heading, and the note is written under `inbox/` with only
`type: note`.

## 🎨 Appearance

The interface follows the operating system's light or dark appearance and has no separate in-app
switch. Each mode uses the Adwaita palette. In light mode the note view is the brightest surface, the
window sits below it, and the browser sidebar recedes one more step. In dark mode the note view is
darker than the window, and the sidebar is lighter than the window, so a panel reads as recessed
rather than raised. A thin outline keeps the steps visible in both modes. The window fits the
1024x600 desktop minimum.

One blue accent marks suggested actions, links, keyboard focus, and log entries. Selection uses a
neutral row shade, not the accent, matching the GNOME navigation sidebar. Section icons are
monochrome; the label, icon, and neutral fill identify the active section without relying on color.
Actions that move a note to the trash use the red destructive style. Due-work notices use a warm
attention surface. Typography uses the platform font family and the GNOME standard styles: title-1
for the page title, title-2 for a step headline, heading for compact headings, body for prose, and
caption for metadata.

## 🧭 See also

- [Inbox](inbox.md)
- [Projects and steps](projects-and-steps.md)
- [References and categories](references-and-categories.md)
- [Understand the vault format](../reference/vault-format.md)
