# 📓 Log

The Log is a dated diary and a chronological lens over the vault. It is built from the same Markdown
files as every other section: there is no separate database and no hidden history.

:::{admonition} tl;dr
:class: note

A log entry is a note with `type: log` and a date. Its date is its identity, so it is filed under
`log/<year>/` or `log/<year>/<month>/`. One entry may exist per exact date. The calendar and the
collapsed year tree show the archive; the detail region is the reading and writing area.
:::

## 🗓️ The calendar

Open **Log** in the navigation region. The browser region shows a month calendar and a collapsed date tree.
**Today’s Entry**, **Entries**, and **Everything** share one row above the calendar; they wrap only
when the browser cannot fit them. The calendar is Monday-first in both languages. Its month heading,
month names, and weekday labels follow the active language: **October 2025** with **Mo Tu We Th Fr Sa
Su** in English, and **octubre de 2025** with **Lu Ma Mi Ju Vi Sá Do** in Spanish.

- A day with entries has a tinted cell and a dot.
- A month with a whole-month entry has a dot on its header.
- A year with a whole-year entry has a dot next to the year.
- The arrows move one month at a time.

Clicking a day with one entry opens it in read mode. A day with several entries expands the day in the
tree. An empty day opens an unsaved draft for that date.

## ✍️ Creating an entry

- **Today’s Entry** opens today's entry in read mode, or an unsaved draft when the day is free.
- Clicking an empty calendar day opens an unsaved draft for that day.
- The **+** on an empty month or year row opens an unsaved draft for that whole month or year.
- A month or year that already has an entry shows an open control instead of the plus.

The draft starts with a long date title in the active language: `November 13, 2026`, `November 2026`,
or `2026` in English, and `13 de noviembre de 2026`, `noviembre de 2026`, or `2026` in Spanish. The
heading is editable; the filename stays the ISO date. While the draft has no content beyond that heading, a
**Starter** control in the label row beside Type and Date offers every valid log card and Empty. The
Daily entry card adds the `## What happened`, `## What I learned`, and `## Next` prompts; Empty leaves
only the heading.

The draft is written the first time its body or labels change, or when a starter card is selected.
Leaving an untouched draft creates no file.

## 🌳 The date tree

The tree starts with every year collapsed. Expanding a year shows its months; expanding a month shows
its days; expanding a day shows its entries. A year entry sits directly under the year, a month entry
under the month, and a day entry under the day. Notes without a date appear under **Undated**.

## 🔀 Entries and Everything

The **Entries** mode shows only `type: log` notes. **Everything** is a date lens over every parsed
note: projects, references, and captures appear at the level their `date` names. The Log remembers the
mode for each vault. Search filters both the tree and the calendar.

## 📅 Changing a date

A log entry's date is its identity. Change it in the page's Date field or with the date picker, which
opens in the active language. Afanes writes the new date, renames the file, moves it to the matching
`log/<year>/<month>/` folder, and rewrites inbound `log:` links. Metadata rows show the compact date
for the active language, such as `Nov 13, 2026` or `13 nov 2026`; the Date field, links, and the
filename keep the ISO value.

The heading follows the new date only while it still equals a generated date title in English or
Spanish. The replacement is written in the active language, so an `October 12, 2025` heading becomes
`13 de octubre de 2025` in a Spanish session, and a `12 de octubre de 2025` heading becomes `October
13, 2025` in an English session. A custom heading is preserved in either case. The Rename action is
not offered for a log entry; the Date field is the rename.

A day, month, or year can hold only one log entry. Creating or moving onto an occupied date is refused.

## 🔗 Linking

Link to a log entry with its ISO date:

```markdown
[Tuesday](<log:2025-10-12>)
[October](<log:2025-10>)
[2025](<log:2025>)
```

The `log:` scheme resolves only log entries. A reference and a log entry may share a display title
because they use different namespaces.

## 🧭 See also

- [Workspace and browser](workspace.md)
- [Pages and editing](pages-and-editing.md)
- [Frontmatter](../reference/frontmatter.md)
- [Vault format](../reference/vault-format.md)
