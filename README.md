# 🗂️ afanes

[![PyPI - Version](https://img.shields.io/pypi/v/afanes.svg)](https://pypi.org/project/afanes)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/afanes.svg)](https://pypi.org/project/afanes)

Afanes is an offline, local-first Markdown vault: a personal wiki and project engine that keeps every
note as an ordinary `.md` file you own.

![The Afanes workspace with browser groups on the left and a capture open in the page pane](https://raw.githubusercontent.com/knkillname/afanes/main/docs/_static/screenshots/workspace.png)

## 📦 Install

For the desktop window:

```console
pip install "afanes[desktop]"
afanes
```

For the browser presentation:

```console
pip install "afanes[web]"
afanes --web
```

The first desktop run downloads and caches the Flet client once under `~/.flet/client/`. The running
application makes no network request. A packaged build bundles the client; see the
[release guide](https://github.com/knkillname/afanes/blob/main/docs/develop/releasing.md).

From a source checkout, use Hatch:

```console
hatch env create
hatch run afanes
```

## 🚀 First five minutes

1. **Open or create a vault.** A vault is a folder of Markdown files; opening one is read-only.
   [Create or open your first vault](https://github.com/knkillname/afanes/blob/main/docs/getting-started/first-vault.md)
2. **Capture a thought.** Type one line in the Inbox. The first line becomes the note's name and
   title.
3. **Clarify it.** Select the capture and choose **Process** to make it a project, a reference, or a
   discarded note.
4. **Work the project.** Add task-list steps and tick them as you go.
5. **Review.** The Review entry shows pending captures, due steps, waiting steps, and projects without
   a next step.

The full walkthrough is in
[Your first five minutes](https://github.com/knkillname/afanes/blob/main/docs/getting-started/capture-clarify-review.md).

## 📚 Documentation

- [Install and run](https://github.com/knkillname/afanes/blob/main/docs/getting-started/install.md)
- [Workspace and browser](https://github.com/knkillname/afanes/blob/main/docs/guide/workspace.md)
- [Inbox](https://github.com/knkillname/afanes/blob/main/docs/guide/inbox.md) and
  [projects](https://github.com/knkillname/afanes/blob/main/docs/guide/projects-and-steps.md)
- [Vault format](https://github.com/knkillname/afanes/blob/main/docs/reference/vault-format.md)
- [Command line](https://github.com/knkillname/afanes/blob/main/docs/guide/command-line.md)
- [Browser mode](https://github.com/knkillname/afanes/blob/main/docs/guide/browser-mode.md)
- [Development setup](https://github.com/knkillname/afanes/blob/main/docs/develop/setup.md)
- [Python API](https://github.com/knkillname/afanes/blob/main/docs/api/index.md)

The documentation site is built locally with `hatch run docs:build`. A published site is a later
change; the links above work on GitHub today.

## 🧭 Project status

Afanes is pre-1.0. The first usable MVP is defined in
[RELEASE.md](https://github.com/knkillname/afanes/blob/main/RELEASE.md), and the release history is in
[CHANGELOG.md](https://github.com/knkillname/afanes/blob/main/CHANGELOG.md). Packaged desktop builds
are unsigned local artifacts; code signing, notarization, auto-update, and a publishing pipeline are
not part of the project yet.

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
