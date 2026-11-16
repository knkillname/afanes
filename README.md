# 🗂️ afanes

Afanes is an offline, local-first Markdown vault: a personal wiki and project engine that keeps every
note as an ordinary `.md` file you own.

![The Afanes workspace with navigation and browser groups on the left and a capture open in the detail region](https://raw.githubusercontent.com/knkillname/afanes/main/docs/_static/screenshots/workspace.png)

## 📦 Run from a source checkout

Afanes runs from a source checkout with Hatch. You need Python 3.13 or newer, Git, and
[Hatch](https://hatch.pypa.io/).

```console
git clone https://github.com/knkillname/afanes.git
cd afanes
hatch env create
hatch run afanes
```

For the browser presentation:

```console
hatch run afanes --web
```

The first desktop run downloads and caches the Flet client once under `~/.flet/client/`. The running
application makes no network request. The release workflow builds the packaged Linux artifact and the
wheel on a pinned `ubuntu-24.04` runner and publishes them when a release tag is pushed; the
[release guide](https://github.com/knkillname/afanes/blob/main/docs/develop/releasing.md) covers the
pipeline and the local fallback. A packaged build bundles the client.

## 🖥️ Platform support

- **Linux.** Native desktop builds are supported and tested, and Linux is the only `1.0.0` release
  gate. GitHub Actions builds the artifact on a pinned `ubuntu-24.04` runner. Download
  `afanes-linux-x64-<version>.tar.gz` from the
  [releases page](https://github.com/knkillname/afanes/releases), verify it against
  `afanes-<version>-checksums.txt`, and run the extracted `afanes` binary.
- **macOS and Windows.** Install the released wheel with `pipx` and start the browser presentation:

  ```console
  pipx install "/path/to/afanes-<version>-py3-none-any.whl[web]"
  afanes --web
  ```

  Download `afanes-<version>-py3-none-any.whl` from the releases page and pass its path; verify it
  against `afanes-<version>-checksums.txt` first. The wheel is the supported macOS and Windows path.

Only Linux carries release evidence. The browser presentation binds loopback only, serves local
assets, and allows one session at a time; see the
[browser mode guide](https://github.com/knkillname/afanes/blob/main/docs/guide/browser-mode.md).

The interface, command line, dates, and starter content ship in English and Spanish. Choose the
language from the welcome state or the workspace primary menu; the choice is saved outside the vault
and applies on the next launch. See
[Workspace and browser](https://github.com/knkillname/afanes/blob/main/docs/guide/workspace.md#language).

Every interactive control exposes an accessible name, banners and toasts are announced to assistive
technology, and the layout follows the operating system's text scale and high-contrast preference
instead of clipping. Empty destinations, an empty search, empty Trash, and the no-page detail show a
symbolic placeholder page with guidance. The application carries an original SVG identity icon. Press
`Ctrl+?` or choose **Keyboard Shortcuts…** from the primary menu to see the grouped shortcut sheet.
See [Workspace and browser](https://github.com/knkillname/afanes/blob/main/docs/guide/workspace.md).

## 🚀 First five minutes

1. **Open or create a vault.** A vault is a folder of Markdown files with an `afanes.yaml` settings
   file at its root; opening a versioned vault is read-only. A folder from an older release can be
   adopted explicitly.
   [Create or open your first vault](https://github.com/knkillname/afanes/blob/main/docs/getting-started/first-vault.md)
2. **Capture a thought.** Type one line in the Inbox. The first line becomes the note's name and
   title.
3. **Clarify it.** Select the capture and choose **Process** to make it a project, a reference, or a
   discarded note.
4. **Work the project.** Add task-list steps and tick them as you go.
5. **Review.** The Review entry shows due reminders, pending captures, due steps, waiting steps, and
   projects without a next step. Due reminders come first and can be opened or dismissed.

A reference, project, or log entry can carry one reminder. Choose a daily, weekday, monthly, or
one-shot schedule with one or more times and a stored IANA time zone; the Review count refreshes while
the application is open. Dismissing records the occurrence without changing the note body or status.
Afanes never sends operating-system notifications or contacts a server. The vault format is schema
`2`; a writable schema `1` vault is upgraded when it opens, and a read-only one opens for browsing
with reminders off.

Discarded notes move to **Trash**, where each entry keeps its title and birthplace and stays
recoverable for 30 days. Restore returns it to where it was; an occupied birthplace asks before it is
replaced. Managed entries can also be deleted permanently or emptied together, and global search finds
them in a separate Trash group.

The full walkthrough is in
[Your first five minutes](https://github.com/knkillname/afanes/blob/main/docs/getting-started/capture-clarify-review.md).

## 📚 Documentation

- [Run Afanes](https://github.com/knkillname/afanes/blob/main/docs/getting-started/install.md)
- [Workspace and browser](https://github.com/knkillname/afanes/blob/main/docs/guide/workspace.md)
- [Inbox](https://github.com/knkillname/afanes/blob/main/docs/guide/inbox.md) and
  [projects](https://github.com/knkillname/afanes/blob/main/docs/guide/projects-and-steps.md)
- [Pages, editing, and reminders](https://github.com/knkillname/afanes/blob/main/docs/guide/pages-and-editing.md)
- [Review](https://github.com/knkillname/afanes/blob/main/docs/guide/review.md)
- [Log](https://github.com/knkillname/afanes/blob/main/docs/guide/log.md)
- [Dates](https://github.com/knkillname/afanes/blob/main/docs/guide/dates.md)
- [Vault format](https://github.com/knkillname/afanes/blob/main/docs/reference/vault-format.md)
- [Command line](https://github.com/knkillname/afanes/blob/main/docs/guide/command-line.md)
- [Browser mode](https://github.com/knkillname/afanes/blob/main/docs/guide/browser-mode.md)
- [Development setup](https://github.com/knkillname/afanes/blob/main/docs/develop/setup.md)
- [Python API](https://github.com/knkillname/afanes/blob/main/docs/api/index.md)

The documentation site is built locally with `hatch run docs:build`. A published site is a later
change; the links above work on GitHub today.

## 🧭 Project status

Afanes is pre-1.0. The unified `1.0.0` gate is defined in
[RELEASE.md](https://github.com/knkillname/afanes/blob/main/RELEASE.md), and the release history is in
[CHANGELOG.md](https://github.com/knkillname/afanes/blob/main/CHANGELOG.md). Linux native builds are
supported and tested; macOS and Windows use the released wheel and `afanes --web`. Every artifact is
unsigned; code signing, notarization, and auto-update are not part of the project.

## 🛠️ Build and contribute

```console
hatch run afanes          # desktop
hatch run afanes --web    # browser
hatch check               # lint, format, types
hatch test --cover        # tests and coverage floor
```

The [development setup](https://github.com/knkillname/afanes/blob/main/docs/develop/setup.md) covers
the environment, tests, and documentation commands.
[AGENTS.md](https://github.com/knkillname/afanes/blob/main/AGENTS.md) is the operating manual for
contributors and agents.

## ⚖️ License

Afanes is distributed under the terms of the
[GNU Affero General Public License v3.0 or later](https://spdx.org/licenses/AGPL-3.0-or-later.html).
