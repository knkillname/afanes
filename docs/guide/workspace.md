# 🗂️ Workspace and browser

The workspace has three regions. The **navigation** region lists destinations, counts, the vault
name, and the primary menu. The **browser** region holds the active destination's title and actions
in its header, a permanent search row beneath that header, and the list, calendar, or review queue.
The **detail** region holds the open page or focused flow and its toolbar. The browser stays visible
while a page is open.

:::{admonition} tl;dr
:class: note

The browser has one group per kind of note. A note appears in exactly one group, and anything under
`trash/` or `templates/` is absent from those groups. **Trash** is its own destination for managed
discarded notes. Search filters the whole vault, not only the active destination.
:::

```{image} ../_static/screenshots/workspace.png
:alt: The Afanes workspace with navigation, browser, and detail regions, and a capture open in the detail region
:class: screenshot
```

## 🧭 Browser groups

| Group | Contains |
| --- | --- |
| **Inbox** | Captures under `inbox/`, newest first |
| **Projects** | Project notes, grouped by status |
| **References** | Reference notes, grouped by their category label; uncategorized references appear under the plain **References** heading |
| **Log** | Dated diary entries, with a month calendar and a collapsed year/month/day tree |
| **Needs Attention** | Parsed `type: note` notes found outside `inbox/` |
| **Unreadable Notes** | Files that could not be parsed; selecting one opens raw rescue mode |
| **Trash** | Managed discarded notes, with the title and **From** birthplace on each row |

A capture under `inbox/` appears only under **Inbox**. A log entry appears under **Log**. A note under
`trash/` appears in no active-note group; only a managed entry appears under **Trash**. A file under
`templates/` is a template card rather than a note. Selecting an entry opens it in the detail region
without changing the browser destination. In the **Review** destination, the browser shows the snapshot
queue instead of the note groups.

**Trash** lists one row per managed entry. Selecting a row opens the note read-only with its birthplace
and trashed day. **Restore** returns it to the birthplace, and **Delete Permanently…** sits in the
secondary menu. When managed entries exist, **Empty Trash…** appears in the browser header. Both delete
actions ask for confirmation and place Cancel first. The Trash destination remains usable in a
read-only vault; maintenance failures appear in a persistent banner.

The **Log** section offers a calendar and a collapsed date tree instead of a flat list. **Entries** shows
only log notes; **Everything** is a date lens over every parsed note. **Today’s Entry** opens today's
entry in read mode, or an unsaved draft when the day is free. The calendar and tree controls follow the
same rule for a chosen day, month, or year. See
[Log](log.md) for the calendar marks, date rules, and linking.

The **References** section also offers **New Reference…** in the browser header. The dialog asks for a
name and a template card or Empty, writes the note immediately, and opens it in edit mode. See
[References and categories](references-and-categories.md) for the creation rules.

**Needs Attention** exists because a capture outside the Inbox cannot be processed. Move it back to the
Inbox or clarify it by editing its frontmatter by hand. **Unreadable Notes** opens the complete file in
raw rescue mode so the text is never lost.

## 🧭 Navigation and the primary menu

The navigation region names the vault. Hovering the name shows its full folder path, so no status bar is
needed. The primary menu above the destinations offers **Open Another Vault…**, **Create a New Vault…**, **Close Vault**, and **About Afanes**. **About Afanes** shows the application name, version, and license.

On a window narrower than 1100 pixels, the navigation moves behind a toggle in the browser header. A
narrow browser presentation shows one region at a time: the browser comes first, and **Back** returns
from a note to the browser. The window cannot shrink below 1024x600.

## 🔍 Search

The search field sits in its own full-width row beneath the browser header, so it is available from
every destination without becoming a destination itself. It filters the whole vault by display title,
identity, prose body text, step text, and role names: a project's `owner`, its `asked_by`, and the
owners of its steps. Results are grouped by destination, including a separate **Trash** group for
managed discarded notes; the active destination does not limit them. Selecting a Trash result opens
the note read-only. The navigation counts stay at each destination's total. Matching ignores case, Unicode form, and
repeated whitespace. Other step metadata and unknown frontmatter keys are excluded, so a plan date or
tag inside a comment is not a search result.

While a query is active, the browser title reads **Search Results** and the destination's own controls
step aside: the Inbox composer, the References **New Reference…** action, the Log calendar and date
tree, and the Review queue are hidden. A search started in the Log returns the same grouped results as
the same search started in any other destination. Clearing the query restores the active destination's
title, controls, and normal list or calendar.

The navigation lists no Search entry: search is a global browser filter, not a location. Switching
destinations clears the query and returns to that destination's normal browser. Press **Ctrl+F** to
focus the search field, **Esc** to clear a non-empty query, or use the clear action at the end of the
search row. When the query is already empty, **Esc** closes the navigation drawer instead.

## ✍️ Capture field

The capture field sits at the top of the Inbox browser region. It behaves exactly like the Inbox
composer: the first non-blank line becomes the filename and heading, and the note is written under
`inbox/` with only `type: note`. **Capture** stays insensitive while the field is blank. Press
**Ctrl+N** or choose the **New Capture** toolbar action to switch to the Inbox and focus the field
from any other destination.

## 🧱 Detail toolbar

The detail toolbar shows **Back**, the page title, one primary action, and a secondary menu. **Process…**
is primary for an unclarified capture, **Edit** for a readable note, **Done** while editing, and
**Restore** for a trashed note. Rename and Move to Trash live in the secondary menu of an active note;
Delete Permanently lives there for a trashed note. The page path, metadata, and save status sit below
the toolbar with the page content, and long-form text stays within a comfortable reading width on large
windows.

## 🎨 Appearance

The interface follows the operating system's light or dark appearance and has no separate in-app
switch. Each mode uses the Adwaita palette. In light mode the note view is the brightest surface, the
window sits below it, and the navigation region recedes one more step. In dark mode the note view is
darker than the window, and the navigation is lighter than the window, so a panel reads as recessed
rather than raised. The browser shares the window surface, and a thin outline keeps the detail visible
in both modes. The window fits the 1024x600 desktop minimum.

One blue accent marks suggested actions, links, keyboard focus, and log entries. Selection uses a
neutral row shade, not the accent, matching the GNOME navigation sidebar. Section icons are
monochrome; the label, icon, and neutral fill identify the active destination without relying on color.
Move to Trash is immediate: a toast offers **Undo**, and the page returns to its original path while
that path is free. Restoring from Trash over an occupied birthplace warns that the existing note will
be permanently replaced; the warning places Cancel first. **Delete Permanently…** and **Empty Trash…**
also require confirmation. The 30-day retention pass is the deliberate exception: it runs silently
when the vault opens or Trash is selected. One-time results and failures use a transient toast; a
persistent condition such as a page conflict or refresh failure uses a banner owned by the page or
session. Field and form problems
stay inline with the control that caused them. Due-work notices use a warm attention surface.
Typography uses the platform font family and the GNOME standard styles: title-1 for the rendered page
heading, title-3 in the detail toolbar, title-2 for a step headline, heading for compact headings, body
for prose, and caption for metadata.

## 🧭 See also

- [Inbox](inbox.md)
- [Projects and steps](projects-and-steps.md)
- [References and categories](references-and-categories.md)
- [Understand the vault format](../reference/vault-format.md)
