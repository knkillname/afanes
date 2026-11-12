# 💻 Command line

The installed `afanes` command starts the application when it is given no subcommand. It also runs
headless commands, which never open a window and never import the interface.

:::{admonition} tl;dr
:class: note

`afanes` starts the app. `afanes vault create` creates and seeds a vault. `afanes vault adopt` adds the
settings file to an older vault. `afanes vault templates` lists the starter content. Headless commands
work without a display server.
:::

## 🗂️ Create a vault

```console
afanes vault create ~/Notes/Afanes
afanes vault create ~/Notes/Work --template work
afanes vault templates
```

`vault create` creates the directory, writes `afanes.yaml` with the current schema, seeds the default
folders, writes the `Getting started` guide, and writes the notes of `--template` when one is supplied.
It prints what it created and makes the new vault the one Afanes opens next launch.

Missing folders in the path are created too, and the report names them:

```text
Created vault /home/you/Notes/Work
Parent folders created: /home/you/Notes
Seeded: inbox/, trash/, reference/, projects/
Settings file: afanes.yaml (schema version 1)
Template: work
Notes written: reference/Getting started.md, projects/Follow up on the incident.md, ...
Remembered as the vault to open next launch.
```

## 🧬 Adopt an existing folder

```console
afanes vault adopt ~/Notes/Afanes
afanes vault adopt ~/Notes/Afanes --no-remember
```

`vault adopt` adds `afanes.yaml` to a folder created before the settings file existed. The folder must
be writable and contain all five default folders (`inbox/`, `trash/`, `reference/`, `projects/`, and
`log/`), matched case-insensitively. `templates/` is optional and extra folders are allowed. Adoption
writes only the settings file, reports its path and schema version, and remembers the vault unless
`--no-remember` is supplied.

A folder that is already versioned is reported unchanged. A folder missing a default folder, a folder
without write access, and an invalid settings file are refused with exit status `1`; no note is
changed.

## ⚙️ Options

- `--template ID` applies a bundled template; omit it to create a vault with only the guide note.
- `vault templates` lists the bundled templates with their identifiers and descriptions without
  opening a vault or writing a file.
- `--no-remember` creates or adopts the vault without changing which vault Afanes opens next launch.

The command refuses a folder that is not empty, a path that is a file, an unknown template, a folder
that cannot be adopted, and a vault that cannot be created. Every created folder is named, so a
mistyped path is visible immediately.

:::{tip}
Use `--no-remember` to prepare a vault for someone else, or to create a second vault without changing
your own next launch.
:::

## 🚦 Exit codes and streams

- `0` success.
- `1` expected failure.
- `2` usage error.

Reports go to standard output and failures to standard error.

:::{important} Remember
Headless commands never start the interface and never require a display. They are safe to run over
SSH or in a script.
:::

## 🧭 See also

- [Vault templates](../reference/templates.md)
- [Create or open your first vault](../getting-started/first-vault.md)
- [Browser mode](browser-mode.md)
