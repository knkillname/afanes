# Design

## Context

See `proposal.md` for motivation. The current constraints that shape this design:

- `README.md` is 503 lines and serves as the manual, build guide, CLI reference, and release pointer.
  There is no `docs/` directory and no documentation destination in `pyproject.toml`.
- Hatch is the only developer interface. `pyproject.toml` already uses PEP 735 dependency groups for
  `test` and `dev`, and the default environment uses the `uv` installer. Hatch 1.18.1 provides
  `hatch check`; there is no CI.
- `tests/core/test_integration.py::TestDocumentedExamples` parses the project example out of
  `README.md`, so the README is already load-bearing documentation.
- `tests/core/test_architecture.py::_live_documents()` scans `README.md`, `AGENTS.md`,
  `CHANGELOG.md`, the specs, `src/`, and `tests/` for numbered section citations. `docs/` is not
  scanned today.
- Public APIs already require strict NumPy-style docstrings. `src/afanes/core/__init__.py` still says
  "and indexing", which no longer matches the in-memory snapshot architecture.
- There are no screenshots, logo, or favicon assets in the source tree.
- The application is offline-only. A documentation build is a development action, but it must not
  introduce a runtime network dependency or require a hosted service.
- Linux, macOS, and Windows parity is mandatory. `docs/_build/` is already ignored by `.gitignore`.

## Goals / Non-Goals

**Goals:**

- One user-facing narrative lives in `docs/`; `README.md` becomes a short landing page.
- The site builds and previews locally with Hatch, without CI.
- The API reference is generated from the existing public docstrings for `models/` and `core/`.
- The documentation is visual and scannable: screenshots, admonitions, emoji-prefixed headings, and
  a consistent page template.
- Every future OpenSpec change reviews documentation and either updates it or records why it did not.
- The new tooling is dev-only, permissively licensed, offline-capable, and cross-platform.

**Non-Goals:**

- Publishing to GitHub Pages, a custom domain, versioned documentation, translations, or social cards.
- API pages for `ui/` or `cli/`, or a stability promise for the pre-1.0 Python API.
- Changes to application behavior, runtime dependencies, vault format, or the shipped interface.
- Emoji headings or admonitions in machine-read Markdown: `AGENTS.md`, `CHANGELOG.md`, `RELEASE.md`,
  and `openspec/specs/**`.
- Rewriting the OpenSpec schema or templates to force a documentation task.

## Decisions

### Sphinx with MyST and Furo

Use Sphinx with `myst-parser` for prose and the Furo theme. Sphinx is the only candidate that gives
first-class autodoc for the existing NumPy docstrings, cross-references, a generated search index, and
a warning-as-error build without a hosted service. MyST keeps pages in Markdown, so the current README
content moves nearly verbatim and contributors do not need to learn reStructuredText. Furo is MIT,
responsive, supports dark mode, ships its own assets, and needs no network at build time.

Alternatives considered:

- reStructuredText only. Rejected because it imposes a rewrite on a Markdown-native project and raises
  the cost of every docs contribution.
- MkDocs Material. Rejected because the API reference would depend on third-party autodoc plugins and
  the project already has a Sphinx-friendly docstring convention.
- Sphinx's default alabaster theme. Rejected because the site should look deliberate without custom
  theme maintenance.

Extensions and settings:

- `myst_parser`, `sphinx.ext.autodoc`, `sphinx.ext.napoleon`, `sphinx_design`, `sphinx_copybutton`, and
  `sphinx_autobuild` for local preview.
- `myst_heading_anchors = 3`, with explicit `(label)=` targets for headings that other pages link to.
- `nitpicky = True`; the build runs with `-W --keep-going`.
- No `intersphinx` in the default build. It would reach the network and weaken the offline guarantee.
  A future change can add cached inventories if cross-project references become necessary.

### Four-layer documentation ownership

Keep one owner per layer:

- `openspec/specs/` is normative. It says what must be true and is backed by tests.
- `docs/` is the user-facing narrative. It explains how to use the behavior, with screenshots and
  examples.
- `README.md` is the front door. It answers what Afanes is, how to install it, and where to go next.
- `AGENTS.md` is the operating manual for contributors and agents. `RELEASE.md` and `CHANGELOG.md`
  remain the release checklist and history.

Documentation links to `AGENTS.md` and `RELEASE.md` instead of copying their rules. Docs must not cite
numbered `AGENTS.md` sections; a link to the file is stable when sections are renumbered. This keeps
`TestDocumentationCitations` unchanged.

### Information architecture follows the user journey

```
docs/
  index.md
  getting-started/   install, first vault, capture -> clarify -> review
  guide/             workspace, inbox, projects, references, editing, processing, review,
                     browser mode, command line
  reference/         vault format, frontmatter, step metadata, names and links, templates,
                     migration, troubleshooting
  develop/           setup, architecture, testing, releasing, documentation policy
  api/               index, models, core, vault
```

The guide is organized by what the user does, not by module boundaries. `docs/develop/documentation.md`
is the style guide: page template, ownership rules, admonition usage, emoji palette, anchor rules, and
build commands.

### Local-first build with a dedicated Hatch environment

Add a `docs` dependency group and a `docs` Hatch environment, so a normal development environment does
not install Sphinx. The commands are:

```console
hatch run docs:build   # sphinx-build -W --keep-going -b html docs docs/_build/html
hatch run docs:serve   # sphinx-autobuild docs docs/_build/html --host 127.0.0.1
```

Publishing is a separate change. Until a site exists, `[project.urls] Documentation` stays on the
README and `html_baseurl` is not set. The README links to pages in `docs/` on GitHub so the links work
before Pages exists. Sphinx is a documentation builder, not a second linter or test runner; `AGENTS.md`
section 2.1 will say so explicitly.

### API reference covers all public models and core

Generate the reference from `afanes.models` and `afanes.core`, excluding `afanes.ui`, `afanes.cli`,
`afanes.__main__`, and the thin package `__init__` modules. Use three hand-written pages —
`api/models.md`, `api/core.md`, and `api/vault.md` — with `automodule` sections instead of
`autosummary` stub files. The source tree stays explicit and there is no generated file tree to
explain.

`napoleon` renders the NumPy-style sections; `autodoc_typehints = "description"` keeps signatures
readable. The API index carries a pre-1.0 note: the documented modules are the public Python surface,
but incompatible changes are still possible before 1.0. Fixing a docstring role that fails `-W` is in
scope; changing application behavior is not.

Alternatives considered:

- `autosummary` generated stubs. Rejected because the generated directory adds build-time files and
  makes the published structure harder to review.
- Documenting `ui/` as well. Rejected because the layer is presentational and imports Flet; its
  behavior belongs in the guide, not the API reference.
- A curated subset of `core`. Rejected because the project already treats non-underscore names as
  public and requires docstrings for them; an arbitrary subset would be harder to explain.

### Admonitions and emoji headings are user-facing conventions

Use built-in MyST admonitions, with no custom CSS:

| Label | Syntax | Use |
| --- | --- | --- |
| `tl;dr` | `{admonition} tl;dr` with `:class: note` | Short summary at the top of a long page |
| Tip | `{tip}` | Shortcut, keyboard action, easier path |
| Warning | `{warning}` | Destructive or irreversible action, conflict, data loss |
| Remember | `{important} Remember` | Invariant that applies beyond the page |

Headings in `README.md` and `docs/` start with one emoji from a curated, semantic palette. The palette
and usage rules live in `docs/develop/documentation.md`. Machine-read Markdown keeps its current
heading format.

GitHub's slugger turns an emoji-prefixed heading into an anchor with a leading hyphen, so the README
landing page will not carry an internal table of contents; it links to docs pages instead. In Sphinx,
cross-referenced headings get explicit MyST targets so links do not depend on generated emoji anchors.
The in-page table of contents still works.

### Documentation review is part of every change

Encode the policy in four places:

- `AGENTS.md` section 4.8: the definition of done includes a documentation update or a recorded
  no-change reason.
- `AGENTS.md` section 5.2: applying a change includes checking the affected `docs/` page.
- `AGENTS.md` section 5.3: the release review covers `README.md` and `docs/`, and records when neither
  changed.
- `openspec/config.yaml` archive guidance: review `docs/` alongside the README.

The OpenSpec schema and templates are not changed. A schema-level forced task would add noise to
changes that genuinely have no user-facing effect; the review rule plus the archive guidance is easier
to apply honestly. `docs/develop/documentation.md` documents the rule for contributors.

### Documentation checks are local and deterministic

- `hatch run docs:build` fails on warnings and broken internal references.
- `TestDocumentedExamples` moves to the new docs paths; capture and step-metadata examples gain the
  same parse coverage as the project example.
- A small documentation-style test parses `README.md` and `docs/**/*.md` with `markdown-it-py`, which is
  already a runtime dependency, and checks that headings start with a curated emoji and that guide and
  reference pages carry a `tl;dr`. The test is deterministic and cheap; if it becomes brittle, it can
  be narrowed without weakening application tests.
- External link checking is not part of the gate because it needs network access. It remains an
  optional manual command.

### Screenshots come from a synthetic vault

Capture four screenshots from a vault created with the bundled `work` template: the workspace, a
project page with step rows, the processing wizard, and a review card. Use a consistent window size and
light theme, synthetic content only, and store the images in `docs/_static/screenshots/`. Every image
gets alt text. The README uses one screenshot; relative images render on GitHub, while PyPI may show
only the alt text, which is acceptable until a published site exists.

## Risks / Trade-offs

- **Docs drift from specs** -> Ownership rules, the per-change review policy, and tested examples keep
  the narrative honest; the specs remain the normative source.
- **Autodoc exposes internals or fails on docstring roles** -> The API index states the pre-1.0 status;
  `-W` turns role mistakes into build failures that are fixed in the same change.
- **Emoji headings break anchors** -> No README table of contents; explicit MyST targets for
  cross-referenced docs headings.
- **Emoji overuse hurts accessibility** -> One meaningful emoji per heading from a curated palette,
  alt text on images, and no color-only admonition meaning.
- **Screenshots go stale** -> They are generated from the bundled templates and reviewed with the
  affected page; the style guide records the capture command.
- **Documentation dependencies grow** -> They live in a dedicated `docs` group, not the runtime or the
  default development environment.
- **The docs build imports `core`** -> The environment installs the project; `ui` is excluded so Flet
  is not imported during the build. Any import-time side effect found here is a documentation task, not
  an application change.
- **A shorter README weakens the PyPI page** -> The landing page keeps the pitch, install command, and
  five-minute path self-contained, and links to the full docs.
- **Local-first means no public URL yet** -> The README and `Documentation` URL keep working; a later
  change adds the Pages workflow and updates the URL.

## Migration Plan

1. Add the docs tooling and Sphinx configuration.
2. Create the site pages by moving and expanding the current README content.
3. Rewrite `README.md` as the landing page and fix the documented-example tests.
4. Add screenshots and the API reference.
5. Update `AGENTS.md`, `openspec/config.yaml`, `CHANGELOG.md`, and the Hatch configuration.
6. Run `hatch run docs:build`, `hatch check`, `hatch test --cover`, `openspec validate --all --strict`,
   `openspec doctor`, and the vocabulary check.

There is no runtime migration or rollback. If the docs build cannot be made warning-free, the change
stays unarchived and the README split is not committed separately. Publishing to GitHub Pages is a
future change with its own workflow and URL update.

## Open Questions

None blocking. GitHub Pages deployment, a custom domain, versioned documentation, translations, and
API pages for `ui/` or `cli/` are deliberately deferred.
