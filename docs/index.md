# 🏠 Afanes documentation

Afanes is an offline, Markdown-native personal wiki and project engine. Your notes are ordinary
Markdown files in a folder you own.

:::{admonition} tl;dr
:class: note

Afanes captures thoughts in an Inbox, lets you clarify them into projects or references, and gives you
a review queue for due work. Nothing leaves your machine.

:::

```{image} _static/screenshots/workspace.png
:alt: The Afanes workspace with browser groups on the left and a capture open in the page pane
:class: screenshot
```

## 🧭 Start here

The documentation follows the user journey: run Afanes from a source checkout, open a vault, capture a
thought, clarify it, and review what is due.

```{toctree}
:maxdepth: 2
:caption: Getting started

getting-started/install
getting-started/first-vault
getting-started/capture-clarify-review
```

```{toctree}
:maxdepth: 2
:caption: Guide

guide/workspace
guide/inbox
guide/projects-and-steps
guide/references-and-categories
guide/log
guide/pages-and-editing
guide/processing
guide/review
guide/browser-mode
guide/command-line
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/vault-format
reference/frontmatter
reference/step-metadata
reference/templates
reference/template-cards
reference/names-and-links
reference/migration
reference/troubleshooting
```

```{toctree}
:maxdepth: 2
:caption: Build and contribute

develop/setup
develop/architecture
develop/interface-standard
develop/testing
develop/releasing
develop/documentation
```

```{toctree}
:maxdepth: 2
:caption: API

api/index
```

## 🛠️ Build the site

The site is built with Sphinx and MyST Markdown. From the repository root:

```console
hatch run docs:build
hatch run docs:serve
```

The built HTML lands in `docs/_build/html/`.
