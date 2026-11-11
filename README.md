# afanes

[![PyPI - Version](https://img.shields.io/pypi/v/afanes.svg)](https://pypi.org/project/afanes)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/afanes.svg)](https://pypi.org/project/afanes)

-----

## Table of Contents

- [Development](#development)
- [Vault format](#vault-format)
- [Inbox](#inbox)
- [Pages and editing](#pages-and-editing)
- [Processing](#processing)
- [Changelog](#changelog)
- [License](#license)

## Development

Afanes is not yet distributed as a packaged desktop app. Run it from a source checkout:

```console
hatch env create
hatch run python -m afanes
```

`pip install afanes` installs the Python library only, not a runnable desktop app.

The first run downloads and caches the Flet desktop client under `~/.flet/client/`. This is a
one-time development provisioning step; the application itself performs no network I/O. Packaged
builds will bundle the client in a later change.

On first launch, choose a vault folder. Afanes remembers it in the platform configuration
directory and reopens it next time. The [Inbox](#inbox) then lists notes under `inbox/`.

## Vault format

A vault is a directory of Markdown files. A note's filename stem is its identity and the name that
references resolve against. Its display title is the first level-1 heading in the body, falling back
to the filename stem when there is no heading. Directories only classify; moving a note between
folders never changes a reference.

Notes use one of four types:

- `note` is an unprocessed capture or a free-form document.
- `action` is one actionable step.
- `project` is an outcome made of action steps.
- `reference` is non-actionable knowledge. A reference may declare a `category`; for example,
  `category: person` marks a person page. People are reference notes, not a separate type.

```markdown
---
type: action
status: active
people:
  - "person:Ada Lovelace"
project: "project:Turing Machine"
---

# Ask Ada for the draft

Ask [Ada Lovelace](<person:Ada Lovelace>) for the draft and file it under
[Turing Machine](project:TuringMachine).
```

```markdown
---
type: reference
category: person
---

# Ada Lovelace

Ada's contact page.
```

The default vault layout is:

```text
vault/
  inbox/          captures
  trash/          recoverable discards
  reference/      non-actionable notes
    people/       reference notes with category: person
  projects/       project notes
  actions/        action notes
```

These folders are conveniences, not requirements. Existing notes anywhere in the vault still
resolve. Folders are created only when a write needs them. Notes under `trash/` are excluded from
scans, name uniqueness, and reference resolution; moving a note back restores it.

Actions and projects may use `active`, `waiting`, `done`, `cancelled`, `archived`, or `later`.
References may omit status or use `later` or `archived`. A capture has no status; `status: inbox`
is not valid because the folder is the queue.

Use `person:` for reference notes with `category: person`, `project:` for project notes, and
`note:` for notes, actions, and uncategorized references. A note belongs to exactly one scheme.
Names are matched case-insensitively, so `[Ada](<person:ada lovelace>)` resolves to the same note.

## Inbox

Captures live in `inbox/`. Capturing a thought uses the first non-blank line as the filename and
writes that line as a level-1 heading at the start of the body. All other text is preserved, even
when the filename had to sanitize characters that are unsafe on some platforms. The frontmatter
contains only `type: note`. No status, project, people, or due date is inferred; clarification is a
separate step.

Capturing `Call Ada` followed by `about the invoice` writes:

```markdown
---
type: note
---

# Call Ada
about the invoice
```

The Inbox lists every note under `inbox/`, newest first, showing each note's display title with its
vault-relative path as the secondary line. Select a note to open it in the page pane; read its body
or choose Edit to change it. Process remains available for Inbox captures.

## Pages and editing

Select a note in the Inbox to open it in the page pane. Read mode shows the display title and the
rendered Markdown body; tapping an internal reference opens its page. External links, attachments,
and unsafe destinations do nothing. Back returns through the pages you opened, whether they came
from the Inbox list or a link.

Following a reference that has no page opens a draft. The draft uses the reference scheme to choose
its type and default folder:

| Reference | Type | Default folder |
| --- | --- | --- |
| `note:Quarterly budget` | uncategorized reference | `reference/` |
| `person:Ada` | reference with `category: person` | `reference/people/` |
| `project:Release 1.0` | project | `projects/` |

The draft starts with the reference name as its level-1 heading and is written only after you type
body text or change a label. The filename is the sanitized reference name, used exactly; a collision
stops the first save instead of adding a suffix. If the original name was unsafe as a filename, the
first save offers to rewrite the references that still use it. If the safe name already belongs to a
page in the same scheme, that page opens instead of creating a duplicate.

Choose Edit to change the raw Markdown body and the labels: type, category, status, due date, people,
and project. The body includes its level-1 heading, which is the display title. Category is offered
only for references, and status choices follow the selected type. People and project fields suggest
existing pages by display title or identity. Changing the type or category previews the inbound
references that would become unresolved before applying the change.

A dirty draft is written roughly every 30 seconds and when you choose Done, press Back, or open
another page. Before every write, Afanes compares the file with the version it read; if another
program changed it, the save stops and the page offers to reload the file or overwrite it with your
version. If the file was moved or deleted, the page offers to recreate it or discard the draft.

A note whose frontmatter cannot be parsed opens in raw rescue mode, where the complete file text is
editable and labels are unavailable. Saving writes exactly what you typed; once the text parses, the
normal editor returns. Unreadable notes are listed in the Inbox failure banner and can be opened from
there.

Rename and Move to trash are available in read mode. Both show their affected references before
confirming. A rename updates the first heading only when it still matches the old identity; a custom
heading is preserved. Trashed pages move under `trash/`, and their inbound references become
unresolved until a page with that name appears again.

## Processing

Select a capture in the Inbox and choose Process. The wizard asks whether the thought is
actionable. If it is not, choose Trash, Later, or Reference. If it is, choose a single Action or a
multi-step Project, then set a status, optional due date, people, and a project where applicable.

The preview shows the destination and any person or project references that do not have a page
yet. People and project fields suggest existing pages by display title or identity and store the
page identity. Those references are allowed and resolve automatically when the page appears.
Confirming writes the classified frontmatter atomically and then moves the note out of `inbox/`. A
failed move leaves the note in the Inbox so the same plan can be retried.

Project steps are action notes linked by the `project` key. Trash moves the note to `trash/`
without rewriting any referring note; moving it back restores it and resolves its inbound
references again.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the release history.

## License

`afanes` is distributed under the terms of the
[GNU Affero General Public License v3.0 or later](https://spdx.org/licenses/AGPL-3.0-or-later.html).
