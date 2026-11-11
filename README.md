# afanes

[![PyPI - Version](https://img.shields.io/pypi/v/afanes.svg)](https://pypi.org/project/afanes)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/afanes.svg)](https://pypi.org/project/afanes)

-----

## Table of Contents

- [Installation](#installation)
- [Vault format](#vault-format)
- [Changelog](#changelog)
- [License](#license)

## Installation

```console
pip install afanes
```

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

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the release history.

## License

`afanes` is distributed under the terms of the
[GNU Affero General Public License v3.0 or later](https://spdx.org/licenses/AGPL-3.0-or-later.html).
