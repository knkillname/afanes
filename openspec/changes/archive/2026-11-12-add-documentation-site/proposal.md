# Proposal

## Why

`README.md` has become the de facto manual. It is 503 lines across 18 headings, and its first 180
lines are development setup, desktop packaging, command-line usage, and browser mode before the first
user-facing section. It mixes four audiences — evaluator, end user, operator, and contributor — and
duplicates behavior that already lives in `openspec/specs/`. There is no documentation destination:
`[project.urls] Documentation` in `pyproject.toml` points back at `#readme`.

The product now has a coherent pre-1.0 feature set — vault selection, capture, processing, projects
and steps, browsing, and review — and the README grew one feature at a time. The Python API also has
strict NumPy-style docstrings, so an autodoc reference is now practical. This is the moment to split
documentation ownership before more behavior accumulates.

## What Changes

- Add a Sphinx documentation site under `docs/`, written in MyST Markdown with the Furo theme.
- Build and preview it locally with Hatch only: `hatch run docs:build` and `hatch run docs:serve`.
  Publishing to GitHub Pages is deliberately out of scope for this change.
- Split `README.md` into a short landing page — pitch, screenshot, install, five-minute path, and
  links — and move the manual, reference, build, and contributor content into `docs/`.
- Establish explicit ownership: `openspec/specs/` stays normative, `docs/` becomes the user-facing
  narrative, `README.md` becomes the front door, and `AGENTS.md` stays the operating manual.
- Make documentation review part of every OpenSpec change. Each change updates the affected `docs/`
  page, or records in its tasks and final report why the change has no user-facing documentation
  impact. Encode the rule in `AGENTS.md` and in the archive guidance in `openspec/config.yaml`.
- Add a getting-started path, a user guide, a reference section, contributor onboarding, and an API
  reference for all public `models` and `core` modules. Exclude `ui/` and `cli/` from the API.
- Add screenshots, `tl;dr`/`Tip`/`Warning`/`Remember` admonitions, and emoji-prefixed headings in
  `README.md` and `docs/` only. Machine-read Markdown keeps its current heading format.
- Add a `docs` dependency group and a dedicated Hatch environment so contributors install Sphinx only
  when they build documentation. Treat Sphinx warnings as build failures.
- Update tests, `AGENTS.md`, `CHANGELOG.md`, and `pyproject.toml` to reflect the new documentation
  workflow. No application behavior, runtime dependency, or network access changes.
- Out of scope: GitHub Actions or GitHub Pages deployment, a custom domain, versioned documentation,
  translations, social cards, and API pages for `ui/` or `cli/`.

## Capabilities

### New Capabilities

None. This is a documentation and tooling change with no product behavior changes, so the change sets
`skip_specs: true` instead of inventing a requirement.

### Modified Capabilities

None.

## Impact

- `docs/` is added: Sphinx configuration, landing page, getting-started, guide, reference, developer,
  and API pages, plus screenshots.
- `README.md` is rewritten as a landing page; its current manual content moves into `docs/`.
- `pyproject.toml` gains a `docs` dependency group and a `docs` Hatch environment. The
  `Documentation` URL stays on the README until a published site exists.
- `AGENTS.md` gains documentation commands, read-order guidance, the per-change documentation review
  rule, and documentation checks in the definition of done and release workflow.
- `openspec/config.yaml` archive guidance asks for a `docs/` review alongside the README, and for a
  recorded no-change decision when documentation is unaffected.
- `CHANGELOG.md` records the change under `Unreleased`.
- `tests/core/test_integration.py` reads documented examples from their new `docs/` location; new
  examples are covered.
- `tests/core/test_architecture.py` needs no change because `docs/` will not cite numbered
  `AGENTS.md` sections.
- `src/afanes/core/__init__.py` loses its stale "and indexing" wording, and any docstring role that
  fails the warning-free docs build is corrected.
- Development dependencies grow by Sphinx and its theme/extensions, all dev-only and permissively
  licensed. The shipped application keeps its offline runtime and adds no account, telemetry, cloud,
  or network behavior.
