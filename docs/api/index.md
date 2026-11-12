# 🧩 Python API

Afanes is primarily an application, not a library. This reference documents the public Python surface
used by the vault engine, the command line, and contributors. It is generated from the NumPy-style
docstrings in `src/afanes/`.

:::{admonition} tl;dr
:class: note

The documented surface is the non-underscore API of `afanes.models` and `afanes.core`. It is pre-1.0:
incompatible changes are possible before the first stable release.
:::

## 🧱 Modules

- [Models](models.md): note vocabulary, references, and steps.
- [Core](core.md): parsing, links, editing, processing, search, settings, and templates.
- [Vault](vault.md): the vault service family and its read-only snapshot types.

The `ui/` and `cli/` packages are documented through the user guide and the command reference instead
of this API, because they are presentation and adapter layers rather than library surfaces.

```{toctree}
:maxdepth: 2
:hidden:

models
core
vault
```
