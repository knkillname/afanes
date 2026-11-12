# Tasks

## 1. Docs toolchain and style contract

- [x] 1.1 Add a `docs` dependency group to `pyproject.toml` with Sphinx, MyST-Parser, Furo,
  sphinx-design, sphinx-copybutton, and sphinx-autobuild, and add a `docs` Hatch environment with
  `build` and `serve` scripts. Create `docs/conf.py` and a minimal `docs/index.md` toctree. Verify
  `hatch run docs:build` writes `docs/_build/html/index.html` with no warnings and `hatch check` keeps
  `docs/conf.py` clean.
- [x] 1.2 Write `docs/develop/documentation.md` with the ownership model, page template, admonition
  rules, emoji palette, anchor rules, per-change documentation review rule, and local build commands.
  Verify the page is linked from `docs/index.md` and appears in the built site.
- [x] 1.3 Add `tests/docs/test_style.py` that parses `docs/**/*.md` with `markdown-it-py` and checks
  emoji-prefixed headings plus the `tl;dr` requirement on guide and reference pages. Verify with
  `hatch test tests/docs/test_style.py`; the test must pass against the pages that exist at this point.

## 2. Getting started

- [x] 2.1 Create `docs/getting-started/install.md` from the current README installation and runtime
  content: desktop, web, source checkout, and the one-time client provisioning note. Verify
  `hatch run docs:build` and every internal link on the page.
- [x] 2.2 Create `docs/getting-started/first-vault.md` from the in-app guide and the vault
  selection/creation behavior. Cover open, create, template choice, and what a new vault seeds. Verify
  the built page and its links to the vault-format and template pages.
- [x] 2.3 Create `docs/getting-started/capture-clarify-review.md` with the five-minute loop. Add the
  capture example to the documented-example tests and verify with
  `hatch test tests/core/test_integration.py::TestDocumentedExamples`.

## 3. User guide

- [x] 3.1 Create `docs/guide/workspace.md`, `inbox.md`, `projects-and-steps.md`, and
  `references-and-categories.md`, using the existing README behavior as the source. Verify
  `hatch run docs:build` and the style test.
- [x] 3.2 Create `docs/guide/pages-and-editing.md`, `processing.md`, `review.md`, `browser-mode.md`,
  and `command-line.md`, including the destructive-action warnings and the review actions. Verify the
  build and the style test.
- [x] 3.3 Add the step-metadata example to the documented-example tests and verify with
  `hatch test tests/core/test_integration.py::TestDocumentedExamples`.

## 4. Reference

- [x] 4.1 Create `docs/reference/vault-format.md`, `frontmatter.md`, and `step-metadata.md`; move the
  project example into the vault-format page and update `TestDocumentedExamples` to read the new path.
  Verify `hatch test tests/core/test_integration.py::TestDocumentedExamples`.
- [x] 4.2 Create `docs/reference/names-and-links.md`, `templates.md`, `migration.md`, and
  `troubleshooting.md`. Verify `hatch run docs:build` with no broken references and the style test.

## 5. Contributor and API reference

- [x] 5.1 Create `docs/develop/setup.md`, `architecture.md`, `testing.md`, and `releasing.md`. Link to
  `AGENTS.md` and `RELEASE.md` instead of copying their rules, and do not cite numbered AGENTS
  sections. Verify the build and the links.
- [x] 5.2 Create `docs/api/index.md`, `models.md`, `core.md`, and `vault.md` with `automodule` sections
  for all public `models/` and `core/` modules. Fix the stale "and indexing" wording in
  `src/afanes/core/__init__.py` and any docstring role that fails the build. Verify
  `hatch run docs:build` is warning-free and the API pages list the expected modules.
- [x] 5.3 Confirm the API reference excludes `afanes.ui`, `afanes.cli`, `afanes.__main__`, and the
  thin package initializers, and that the build does not import Flet. Verify with a grep of the API
  pages and the build log.

## 6. Screenshots and README split

- [x] 6.1 Create a synthetic vault from the bundled `work` template, capture the workspace, project
  step page, processing wizard, and review card at a consistent window size, and store them under
  `docs/_static/screenshots/` with alt text. Verify the files exist and the built pages reference them.
- [x] 6.2 Rewrite `README.md` as a landing page: pitch, one screenshot, install, five-minute path,
  links to the docs, project status, and license. Extend the style test to cover README headings.
  Verify `hatch test tests/docs/test_style.py`, `hatch run docs:build`, and that the README links work
  on GitHub and in the PyPI long description.
- [x] 6.3 Reconcile every old README section against the new docs pages. Verify no behavior, build,
  or CLI content is stranded, and record the reconciliation in the change notes used for review.

## 7. Documentation policy and integration

- [x] 7.1 Update `AGENTS.md`: the project snapshot and read order, section 2 commands, section 2.1
  docs-tool wording, section 4.8 definition of done, section 5.2 apply review, and section 5.3
  release review for README and docs. Verify `hatch test tests/core/test_architecture.py` and the
  updated sections by inspection.
- [x] 7.2 Update the `operations.archive.guidance` in `openspec/config.yaml` to review `docs/`
  alongside `README.md` and to record when neither changes. Verify `openspec doctor` and
  `openspec validate --all --strict`.
- [x] 7.3 Add the change to `CHANGELOG.md` under `Unreleased` and name the delivered documentation
  behavior. Verify the entry is present and follows the existing style.
- [x] 7.4 Run the full local gates: `hatch run docs:build`, `hatch check`, `hatch test --cover`,
  `openspec validate --all --strict`, `openspec doctor`, and the section 6.1 vocabulary grep. Verify
  all pass before reporting the change ready for review.

## Workflow follow-up

- Archive the change after review and after every task is checked.
- Run the post-archive release workflow in `AGENTS.md` section 5.3.
- Open a later change for the GitHub Pages workflow, the published site URL, and the `Documentation`
  URL update.
