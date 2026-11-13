# 🔗 Names and links

Notes reach each other by name. The filename stem is the identity, and the display title is separate.
This page covers identity, schemes, matching, and what happens when a reference has no page.

:::{admonition} tl;dr
:class: note

Use `note:` for every non-project note and `project:` for projects. Names match case-insensitively, and
categories never change the namespace.
:::

## 🪪 Identity

A note's filename stem is its identity and the name that references resolve against. The display title
is the first level-1 heading in the body, falling back to the filename stem when there is no heading.

Directories only classify. Moving a note between folders never changes a reference. Renaming the file
renames the note.

## 🧭 Schemes

| Scheme | Resolves to | Example |
| --- | --- | --- |
| `note:` | A capture or reference, including references in any category | `[Ada](<note:Ada Lovelace>)` |
| `project:` | A project | `[Release](<project:Release 1.0>)` |

A note belongs to exactly one scheme. Use angle brackets when the name contains spaces so the
destination stays unambiguous.

## 🔤 Matching

Names are matched case-insensitively, so `[Ada](<note:ada lovelace>)` resolves to the same note.
Matching also ignores Unicode form and repeated whitespace. Category labels do not participate in name
resolution.

## 🧷 What a link does

- An internal reference with a page opens that page.
- An internal reference with no page opens a draft; the scheme chooses its type and default folder.
- An external link, attachment, or unsafe destination does nothing.

The draft starts with the reference name as its level-1 heading and is written only after you type body
text or change a label. The filename is the sanitized reference name, used exactly. A collision stops
the first save instead of adding a suffix.

A project's `owner` and `asked_by` names and every step owner name behave as links too, even though
they are plain text in the file. A resolved name opens its page and an ambiguous name shows the
candidate picker. A missing name is styled as a broken link; selecting it asks for a category, which
defaults to `person` and offers existing and template card categories, then creates the note from the
matching template card and opens it in edit mode. Cancelling writes nothing.

## 🧹 Renames, trash, and unresolved links

A rename updates the first heading only when it still matches the old identity; a custom heading is
preserved. Renaming a note also rewrites every resolving body reference and every metadata role name
that uses it: a project's `owner` and `asked_by` values and a step's `owners`. When a rewrite cannot
update every note, the report names the updated notes and the skipped or failed ones with the reason,
using vault-relative paths. Moving a note to `trash/` makes its inbound references unresolved without
rewriting the referring notes, including role names. Moving the note back restores them.

If a reference name was unsafe as a filename, the first save offers to rewrite the references that still
use it, including role names. If the safe name already belongs to a page in the same scheme, that page
opens instead of creating a duplicate.

## ↩️ Connections use the same resolution

The **Connections** section of a page is the inbound direction of the same name rules. A note appears
under **Linked From** only when its body reference resolves to exactly one page. A missing or ambiguous
reference is attributed to no page, and notes under `trash/` never contribute.

Step owners and a project's `owner` and `asked_by` values resolve in the `note:` namespace, so any note
with a matching name can own steps, own a project, or request work; the note does not need a person
category. A role name that matches no note stays in the file and appears in no Connections section; in
the page it is shown as a broken link that can create the missing note. A project appears under
**Owned Projects** once, under **Requested Projects** once, and an owner can own several steps in the
same project.

Connections are derived from the scan and are not stored. Nothing in the vault records a backlink,
and reading or toggling the section writes no file. See [Pages and editing](../guide/pages-and-editing.md)
for the section itself.

## 🗂️ Categories are labels, not namespaces

A category groups references in the browser and chooses a default folder under `reference/`. It never
selects a reference scheme. See [References and categories](../guide/references-and-categories.md).

## 🧭 See also

- [Vault format](vault-format.md)
- [Frontmatter](frontmatter.md)
- [References and categories](../guide/references-and-categories.md)
