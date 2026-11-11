# afanes

[![PyPI - Version](https://img.shields.io/pypi/v/afanes.svg)](https://pypi.org/project/afanes)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/afanes.svg)](https://pypi.org/project/afanes)

-----

## Table of Contents

- [Development](#development)
- [Vault format](#vault-format)
- [Inbox](#inbox)
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

A vault is a directory of Markdown files. A note's filename stem is its name and title, and
directories only classify; moving a note between folders never changes a reference. Internal
references are standard Markdown links with a typed scheme:

```markdown
---
type: action
status: active
people:
  - "person:Ada Lovelace"
project: "project:Turing Machine"
---

Ask [Ada Lovelace](<person:Ada Lovelace>) for the draft and file it under
[Turing Machine](project:TuringMachine).
```

Use `note:` for notes, actions, and references. Names are matched case-insensitively, so
`[Ada](<person:ada lovelace>)` resolves to the same note.

## Inbox

Captures live in `inbox/`. Capturing a thought uses the first non-blank line as the filename and
writes the complete text as the body, with only `type: note` in the frontmatter. No status,
project, people, or due date is inferred; clarification is a separate step.

The Inbox lists every note under `inbox/`, newest first, and opens notes read-only.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the release history.

## License

`afanes` is distributed under the terms of the
[GNU Affero General Public License v3.0 or later](https://spdx.org/licenses/AGPL-3.0-or-later.html).
