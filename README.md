# afanes

[![PyPI - Version](https://img.shields.io/pypi/v/afanes.svg)](https://pypi.org/project/afanes)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/afanes.svg)](https://pypi.org/project/afanes)

-----

## Table of Contents

- [Development](#development)
- [Command line](#command-line)
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
hatch run afanes
```

`hatch run afanes` opens the desktop window. The module form, `hatch run python -m afanes`, is
equivalent and remains available.

`pip install afanes` installs the Python library and the Flet SDK, but no interface runtime. Install
the runtime for the presentation you use:

```console
pip install "afanes[desktop]"   # native window; the client is cached on first run
pip install "afanes[web]"       # browser runtime; no native client is installed
```

With a runtime installed, the `afanes` command starts the application; `python -m afanes` does the
same.

Installing a runtime through the package manager is the only supported path. Afanes never installs
packages while starting. The first desktop run downloads and caches the Flet desktop client under
`~/.flet/client/`; this is a one-time development provisioning step and the application itself
performs no network I/O. The `web` runtime ships its browser client inside its wheel, so it needs no
download. Packaged builds will bundle the desktop client in a later change.

Afanes supports Flet 1.0.4 and later 1.x releases. `hatch test --all` runs the suite on every
supported interpreter and against the oldest supported dependency versions. The development
environment installs both interface runtimes, so `hatch run afanes --web` works from a clean
checkout.

## Command line

The installed `afanes` command starts the application when it is given no subcommand. It also runs
headless commands, which never open a window and never import the interface:

```console
afanes vault create ~/Notes/Afanes
afanes vault create ~/Notes/Work --template work
afanes vault templates
```

`vault create` creates the directory, seeds the default folders, writes the `Getting started` guide,
and writes the notes of `--template` when one is supplied. It prints what it created and makes the
new vault the one Afanes opens next launch. Missing folders in the path are created too, and the
report names them:

```text
Created vault /home/you/Notes/Work
Parent folders created: /home/you/Notes
Seeded: inbox/, trash/, reference/, projects/
Template: work
Notes written: reference/Getting started.md, projects/Quarterly planning.md, ...
Remembered as the vault to open next launch.
```

- `--template ID` applies a bundled template; omit it to create a vault with only the guide note.
- `vault templates` lists the bundled templates with their identifiers and descriptions without
  opening a vault or writing a file.
- `--no-remember` creates the vault without changing which vault Afanes opens next launch.
- The command refuses a folder that is not empty, a path that is a file, an unknown template, and a
  vault that cannot be created. Every created folder is named, so a mistyped path is visible
  immediately.
- Exit codes: `0` success, `1` expected failure, `2` usage error. Reports go to standard output and
  failures to standard error.

## Running in a browser

Machines that block the native Flet client can serve the same interface to a browser instead:

```console
pip install "afanes[web]"
afanes --web
```

The module form, `python -m afanes --web`, works the same.

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

On first launch, choose an existing folder or create a new vault. **New vault** opens a form with
the folder path, a **Choose folder** button on desktop, the starter-content choice, and a preview. It
writes `reference/Getting started.md` plus the notes of the chosen template, seeds `inbox/`,
`trash/`, `reference/`, and `projects/`, and remembers the result in the platform configuration
directory. Afanes reopens that vault next time, and the [workspace browser](#workspace-browser)
lists every note in it, opening on the [Inbox](#inbox) group.

The same choice is available from **Change vault → Create a new vault** while a vault is open, so a
second vault can be created without closing the application. Only the create action seeds the
default folders and writes starter content: opening an existing empty folder through **Open another
vault** leaves it unseeded, and Afanes creates each folder only when a write needs it. Opening or
scanning a vault never creates a folder or a file.

**Change vault → Close vault** saves an open page draft, forgets the remembered vault, and returns to
the welcome screen, so the next launch starts there. A pending page dialog or disk conflict keeps the
vault open and explains what to resolve.

## Vault format

A vault is a directory of Markdown files. A note's filename stem is its identity and the name that
references resolve against. Its display title is the first level-1 heading in the body, falling back
to the filename stem when there is no heading. Directories only classify; moving a note between
folders never changes a reference.

Notes use one of three types:

- `note` is an unclarified capture. It belongs in `inbox/` and means "not clarified yet".
- `reference` is non-actionable knowledge. A reference may declare a free-form `category` label;
  for example, `category: person` marks a person page. People are references, not a note type.
- `project` is an outcome whose body is a checklist. Each task list item is a step; steps have no
  filename, identity, or reference namespace.

```markdown
---
type: project
status: active
due_date: 2026-11-30
---

# Release migration checklist

- [ ] Draft the checklist <!-- {plan: 2026-11-20} -->
- [ ] Ask [Ada Lovelace](<note:Ada Lovelace>) to review it <!-- {owners: [Ada Lovelace], tags: [review]} -->
- [x] Open the tracking page <!-- {plan: 2026-11-14, actual: 2026-11-15} -->
```

```markdown
---
type: reference
category: person
---

# Ada Lovelace

Ada's contact page.
```

The recognized frontmatter keys are:

| Key | Valid on | Values |
| --- | --- | --- |
| `type` | every note | `note`, `reference`, or `project` |
| `category` | references only | any non-empty single folder label; case is preserved |
| `status` | projects and references | projects: `active`, `waiting`, `done`, `cancelled`, `archived`, `later`; references: `later`, `archived`, or absent |
| `due_date` | projects only | a calendar date written as `YYYY-MM-DD` |

Unknown keys are preserved. A capture has no status; `status: inbox` is not valid because the folder
is the queue. A due date is a date, not a timestamp.

The default vault layout is:

```text
vault/
  inbox/          captures
  trash/          recoverable discards
  reference/      non-actionable notes
    <category>/   optional category folders, such as reference/person/
  projects/       project notes
```

These folders are conveniences, not requirements. Existing notes anywhere in the vault still
resolve. Folders are created only when a write needs them. A newly created vault also contains the
`Getting started` guide, and a chosen template's notes; a vault opened later is never seeded or
repaired. A categorized reference is filed under `reference/<category-folder>/`, where the folder is
derived from the label through the cross-platform filename policy and an existing case variant is
reused. Notes under `trash/` are excluded from scans, name uniqueness, and reference resolution;
moving a note back restores it.

### Step metadata

Steps are Markdown task list items. A task list item is a list item whose content begins with `[ ]`
or `[x]`. Only a project body contributes steps; checkboxes in any other note are ordinary Markdown.
Ticking a step writes `[x]` and adds `actual: <today>`; unticking removes `actual` and keeps `plan`.

A step may end with one metadata comment made of a flow-style YAML object:

```markdown
- [ ] Call the plumber <!-- {owners: [Ada], plan: 2026-11-20, actual: 2026-11-14, tags: [phone]} -->
```

| Key | Meaning |
| --- | --- |
| `owners` | people the step waits on. No owner means the step is yours. |
| `plan` | day the step was supposed to happen, as `YYYY-MM-DD` |
| `actual` | day it was completed, as `YYYY-MM-DD`; written by ticking |
| `tags` | free-form labels used only to filter steps |

The comment must be the last content on the line and the line must end with `-->`; text after the
comment makes it prose. Every key is optional, and a comment without a mapping is prose. Unknown keys
are preserved when the step is rewritten. A malformed comment or invalid value drops only that key,
keeps the note readable, and reports the line. A value containing `--` cannot appear inside an HTML
comment, so the app reports it instead of writing invalid metadata. Step owners resolve through the
same catalog as `note:` references.

### Schemes and categories

Use `project:` for project notes and `note:` for every other note, including references in any
category. A note belongs to exactly one scheme. Names are matched case-insensitively, so
`[Ada](<note:ada lovelace>)` resolves to the same note. Categories never select a namespace; they
only group references in the browser and choose a default folder.

### Upgrading from the four-type model

This release is a hard break. Notes declaring `type: action`, links using `person:Name`, and notes
carrying the retired `people` or `project` frontmatter keys are validation errors. They appear under
**Unreadable notes** and open in raw rescue mode without being rewritten. There is no automatic
migration: create a one-step project for an action, move its work into the project body as a step,
and rewrite `person:Name` links as `note:Name`. Any `category: person` reference remains valid and
keeps working.

## Workspace browser

The workspace keeps a navigation browser beside the page pane. The browser groups every parsed note:

- **Inbox** lists captures under `inbox/`, newest first.
- **Projects** lists project notes grouped by status.
- **References** lists reference notes, grouped by their category label. Uncategorized references
  appear under the plain **References** heading.
- **Needs attention** lists parsed `type: note` notes found outside `inbox/`. They cannot be
  processed; move them back to the Inbox or clarify them by hand.
- **Unreadable notes** lists files that could not be parsed. Selecting one opens the complete file in
  raw rescue mode.

A note appears in exactly one group. Captures under `inbox/` appear only under **Inbox**, and notes
under `trash/` are absent. Selecting any entry opens it in the page pane without changing the
browser section.

The search field filters the active section by display title, identity, prose body text, and step
text. Matching ignores case, Unicode form, and repeated whitespace. Step metadata comments are
excluded, so an owner name or date inside a comment is not a search result.

The capture field stays at the top of the workspace. It behaves exactly like the Inbox composer:
the first non-blank line becomes the filename and heading, and the note is written under `inbox/`
with only `type: note`.

## Inbox

Captures live in `inbox/`. Capturing a thought uses the first non-blank line as the filename and
writes that line as a level-1 heading at the start of the body. All other text is preserved, even
when the filename had to sanitize characters that are unsafe on some platforms. The frontmatter
contains only `type: note`. No status, category, project, people, or due date is inferred;
clarification is a separate step.

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

Each project row shows its status, optional due date, count of open steps, and next step. An open
step is an unchecked task list item in the project body; checked steps are not counted. The next
step is the first unchecked step in document order. Dates and owners never reorder the steps. When
the first unchecked step has an owner, the row marks it as waiting.

Steps belong to a project by containment: the project whose body holds the task list item owns it.
A body link to a project does not create a step, and a project may have no steps at all. Checking
every step does not close the project, and closing a project does not change its steps. Adding,
ticking, or removing a step updates the workspace after the next scan or save.

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
| `project:Release 1.0` | project | `projects/` |

The draft starts with the reference name as its level-1 heading and is written only after you type
body text or change a label. The filename is the sanitized reference name, used exactly; a collision
stops the first save instead of adding a suffix. If the original name was unsafe as a filename, the
first save offers to rewrite the references that still use it. If the safe name already belongs to a
page in the same scheme, that page opens instead of creating a duplicate.

Choose Edit to change the raw Markdown body and the labels: type, category, status, and due date.
The body includes its level-1 heading, which is the display title, and project steps with their
metadata. Category is offered only for references and accepts any label. The due date is offered
only for projects. Status choices follow the selected type. There are no `people` or `project`
fields.

Read mode renders a project's steps as rows with the step text, checked state, owners, plan and
actual dates, and tags. Metadata comments are hidden from the rendered text. Ticking or unticking a
step rewrites only that line atomically and leaves every other byte of the file unchanged.

Changing a reference's category previews its new folder and moves the file only after confirmation.
The name, identity, and inbound references do not change. Cancelling leaves both the category and
the file location unchanged; if a move fails, the note keeps the new category in its old folder and
the drift is invisible because grouping uses the label.

Changing the type between the document family (`note` or `reference`) and `project` previews the
inbound references that would become unresolved and requires confirmation; no reference is
retargeted automatically. A change between `note` and `reference` shares the `note` scheme and needs
no confirmation.

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

Select a capture in the Inbox and choose Process. The wizard asks what the capture should become:

- **Trash** moves it to `trash/` without rewriting it.
- **Later** keeps it as a reference with `status: later`.
- **Reference** keeps it as an uncategorized reference with no status.
- **Project** turns it into a project with a status and optional due date. Task list items already in
  the capture body become steps, and a project may start empty.
- **Append step** adds the capture as a step of an existing project and moves the capture to trash.
- **Done now** writes a completed one-step project with `status: done`.

The preview shows the destination and, when the outcome changes scheme, how many inbound references
will become unresolved. Append step suggests existing projects by display title or identity and
stores the identity; text that matches no project is rejected.

Append step writes the target project first and then moves the capture to trash. A failed project
write leaves both notes unchanged. If the write succeeds and the trash move fails, the step is
already present; retrying the same plan detects the existing step and does not duplicate it.

Trash moves the note without rewriting any referring note; moving it back restores it and resolves
its inbound references again. Every other outcome writes the classified frontmatter atomically and
then moves the note out of `inbox/`. A failed move leaves the note in the Inbox so the same plan can
be retried.

## Review

At launch Afanes shows a digest when one or more own steps are due or overdue. The digest reports the
count, writes nothing, and starts the guided review when activated. With no due work, no digest is
shown.

The **Review** entry shows how many items need attention: pending Inbox captures, due or overdue own
steps, waiting steps, and open projects with no open step. Healthy open projects do not contribute
to the badge. Selecting Review with zero pending items shows the zero state and starts no session.

Starting a review snapshots a queue in this order:

1. Pending Inbox captures.
2. Due or overdue own steps.
3. Waiting steps.
4. Open projects with no open step.
5. Healthy open projects, for a quick confirmation.

Closed projects are excluded. Notes created during a session appear in the browser immediately but
wait for the next review session.

An Inbox item opens the existing Processing Wizard. Confirming an outcome applies it and advances
the session; cancelling leaves the capture in the Inbox. The review never chooses an outcome or
metadata from the capture text.

A due step card offers do it now, postpone, delegate, open project, and skip. Do it now checks the
step and records `actual`; postpone replaces `plan`; delegate adds an owner and moves the step to
waiting; open project shows the project page; skip changes nothing. A waiting step card shows its
owners and offers reassign, open project, and skip. Reassign replaces the owners.

A project card shows the project title, status, optional due date, its next step, and any other open
steps. Open project to work on the page. For a project with no open step, the card offers adding a
next step, marking the project done, deferring it to `later`, or skipping. Adding a step requires
text and appends a task list item to the project body; the refreshed card shows it as the next step.
Marking done and deferring both require confirmation. Skip leaves the project exactly as it was, so
it remains in the next session's pending count.

The review never classifies captures, changes a project status, checks a step, or creates a note
without an explicit choice. After the last item, the session reports how many items were reviewed
and skipped and returns to the browser. The session is not persisted across restarts; the pending
count is always recomputed from the vault.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the release history.

## License

`afanes` is distributed under the terms of the
[GNU Affero General Public License v3.0 or later](https://spdx.org/licenses/AGPL-3.0-or-later.html).
