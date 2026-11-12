# 🏗️ Architecture

Afanes is a local-first Markdown vault with a layered Python package. The Markdown files are
authoritative; the application scans them into an in-memory snapshot and derives every view from that
snapshot.

:::{admonition} tl;dr
:class: note

The dependency direction is `models <- core <- ui` and `core <- cli`. `ui` and `cli` never import each
other, `core` never imports Flet, and `models` imports only the standard library.
:::

## 🧱 Layers

```text
                 +------------------+
                 |      models      |  value objects, standard library only
                 +--------+---------+
                          |
                 +--------v---------+
                 |       core       |  parsing, names, links, steps, vault I/O,
                 |                  |  search, settings, templates
                 +---+----------+---+
                     |          |
            +--------v--+    +--v--------+
            |    ui     |    |    cli    |
            | Flet app  |    | argparse  |
            +-----------+    +-----------+
```

- `models/` holds immutable value objects: note vocabulary, references, and steps.
- `core/` owns parsing, filename policy, linking, step parsing, vault I/O, processing, search, settings,
  and templates.
- `ui/` is presentational: the Flet shell, state controllers, views, and shared components.
- `cli/` is a thin adapter over `core` for headless commands.

The import graph is acyclic at submodule level. Import modules for functions and constants, and import
CamelCase types directly. No relative imports, wildcard imports, or `TYPE_CHECKING` blocks.

## 🧠 The vault snapshot

There is no SQLite index. Each vault is scanned into an in-memory `VaultSnapshot`; `core/search.py`
derives the browser, project, and review views from it. `Browser`, `ProjectBoard`, and `ReviewPlanner`
are read-only over the snapshot and never read files.

Do not add an indexer, a persistent index, or a background index process without an approved change.

## 🔒 Write rules

All vault writes go through the `Vault` service family. The root is resolved once, every candidate path
must stay inside it, and writes use the same-directory atomic writer. Existing body text, unknown
frontmatter keys, and the newline style are preserved.

One writer owns a vault at a time. Renames, moves, and trash require confirmation and never follow
symlinks outside the vault. Startup and scanning are read-only: opening a vault does not create a file
or folder.

## 🧩 Object ownership

Every new unit is one of:

- a value object: immutable data plus invariants;
- a service object: owns one resource and validates it at construction;
- a pure function: stateless transformation;
- a controller or view: UI state plus presentation.

The architecture test is the hard gate: module-level functions, duplicate view helpers, `AppState`
fields, public surface budgets, and the import graph are checked mechanically. Add a temporary
exemption only through an approved change, and remove it when the phase passes.

## 🧭 See also

- [Development setup](setup.md)
- [Testing](testing.md)
- [Documentation guide](documentation.md)
- [AGENTS.md](https://github.com/knkillname/afanes/blob/main/AGENTS.md) for the full rules
