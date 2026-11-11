# afanes

[![PyPI - Version](https://img.shields.io/pypi/v/afanes.svg)](https://pypi.org/project/afanes)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/afanes.svg)](https://pypi.org/project/afanes)

-----

## Table of Contents

- [Development](#development)
- [Running in a browser](#running-in-a-browser)
- [Vault format](#vault-format)
- [Workspace browser](#workspace-browser)
- [Inbox](#inbox)
- [Projects](#projects)
- [Pages and editing](#pages-and-editing)
- [Processing](#processing)
- [Review](#review)
- [Changelog](#changelog)
- [License](#license)

## Development

Afanes is not yet distributed as a packaged desktop app. Run it from a source checkout:

```console
hatch env create
hatch run python -m afanes
```

`pip install afanes` installs the Python library and the Flet SDK, but no interface runtime. Install
the runtime for the presentation you use:

```console
pip install "afanes[desktop]"   # native window; the client is cached on first run
pip install "afanes[web]"       # browser runtime; no native client is installed
```

Installing a runtime through the package manager is the only supported path. Afanes never installs
packages while starting. The first desktop run downloads and caches the Flet desktop client under
`~/.flet/client/`; this is a one-time development provisioning step and the application itself
performs no network I/O. The `web` runtime ships its browser client inside its wheel, so it needs no
download. Packaged builds will bundle the desktop client in a later change.

Afanes supports Flet 1.0.4 and later 1.x releases. `hatch test --all` runs the suite on every
supported interpreter and against the oldest supported dependency versions. The development
environment installs both interface runtimes, so `hatch run python -m afanes --web` works from a
clean checkout.

## Running in a browser

Machines that block the native Flet client can serve the same interface to a browser instead:

```console
pip install "afanes[web]"
python -m afanes --web
```

The desktop window stays the default; `--web` is the explicit opt-in and Afanes never switches
presentation on its own. The server binds the loopback interface only and refuses other machines, so
Afanes remains a single-user local application. Every interface asset comes from the local
installation, so a session works with no network access after installation.

Options:

- `--vault DIR` opens that folder for this run without replacing the remembered vault.
- `--port N` chooses the listening port. The default asks the operating system for a free one.

A browser cannot return a folder path from a file dialog, so a browser session asks for an absolute
path instead of opening a picker, and the Change vault action asks the same way. One browser session
can drive the workspace at a time: a second tab shows a notice until the first one closes. If the
desktop client cannot start, Afanes reports the failure and exits rather than switching
presentations silently.

If a browser tab shows a spinner with "Working…", the tab has lost its Python session, usually
because the server process exited. Start the server again and reload the tab. Closing a tab releases
its session, so Afanes can be reopened in a new one.

On first launch, choose a vault folder. Afanes remembers it in the platform configuration
directory and reopens it next time. The [workspace browser](#workspace-browser) then lists every
note in the vault and opens on the [Inbox](#inbox) group.

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

## Workspace browser

The workspace keeps a navigation browser beside the page pane. The browser groups every parsed
note by type:

- **Inbox** lists captures under `inbox/`, newest first.
- **Projects** lists project notes grouped by status.
- **Actions** lists action notes.
- **People** lists reference notes with `category: person`.
- **References** lists uncategorized reference notes.
- **Notes** lists free-form notes outside the inbox.

A note appears in exactly one group. Notes under `trash/` are absent. A note that cannot be parsed
appears in **Unreadable notes**, where selecting it opens the complete file in raw rescue mode.
Selecting any entry opens it in the page pane without changing the browser section.

The search field filters the active section by display title or identity. Matching ignores case,
Unicode form, and repeated whitespace. Search does not read note bodies; a term that appears only in
a body does not match.

The capture field stays at the top of the workspace. It behaves exactly like the Inbox composer:
the first non-blank line becomes the filename and heading, and the note is written under `inbox/`
with only `type: note`.

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

The Inbox group lists every note under `inbox/`, newest first, showing each note's display title with
its vault-relative path as the secondary line. Select a note to open it in the page pane; read its
body or choose Edit to change it. Process remains available for Inbox captures.

## Projects

The Projects group lists every parsed project under **Active**, **Waiting**, **Later**, and
**Closed**. A project without a status is active. `done`, `cancelled`, and `archived` projects are
closed, and the Closed group starts collapsed.

Each project row shows its status, optional due date, count of open actions, and next action. An
action is open when it has no status or is `active` or `waiting`; `later`, `done`, `cancelled`, and
`archived` actions are not open. A project's next action is computed, never stored: the open action
with the earliest due date wins; when no open action has a due date, `active` ranks before
`waiting`, then the display title breaks the tie.

An action belongs to a project only when its `project` frontmatter reference resolves uniquely to
that project. Links in the body do not count as steps, and an ambiguous or unresolved reference is
not attributed to any project. Changing actions never changes a project's status automatically, and
closing a project never changes its actions.

## Pages and editing

Select a note in the browser to open it in the page pane. Read mode shows the display title and the
rendered Markdown body; tapping an internal reference opens its page. External links, attachments,
and unsafe destinations do nothing. Back returns through the pages you opened, whether they came
from the browser or a link.

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
normal editor returns. Unreadable notes are listed in the browser's **Unreadable notes** section and
can be opened from there.

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

## Review

The **Review** entry shows how many items need attention: pending Inbox captures plus open projects
with no open action. Healthy open projects do not contribute to the badge. Selecting Review with
zero pending items shows the zero state and starts no session.

Starting a review snapshots a queue in this order:

1. Pending Inbox captures.
2. Open projects with no next action.
3. Healthy open projects, for a quick confirmation.

Closed projects are excluded. Notes created during a session appear in the browser immediately but
wait for the next review session.

An Inbox item opens the existing Processing Wizard. Confirming an outcome applies it and advances
the session; cancelling leaves the capture in the Inbox. The review never chooses an outcome or
metadata from the capture text.

A project card shows the project title, status, optional due date, its next action, and any other
open actions. Open project or the next action to work on either page. For a project with no open
action, the card offers creating a next action, marking the project done, deferring it to `later`,
or skipping. Creating an action requires a title and writes an action linked to the project; the
project note itself is unchanged. Marking done and deferring both require confirmation. Skip leaves
the project exactly as it was, so it remains in the next session's pending count.

After the last item, the session reports how many items were reviewed and skipped and returns to the
browser. The session is not persisted across restarts; the pending count is always recomputed from
the vault.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the release history.

## License

`afanes` is distributed under the terms of the
[GNU Affero General Public License v3.0 or later](https://spdx.org/licenses/AGPL-3.0-or-later.html).
