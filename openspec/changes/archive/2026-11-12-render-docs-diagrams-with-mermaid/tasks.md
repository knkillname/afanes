# Tasks

## 1. Docs toolchain and offline runtime

- [x] 1.1 Add `sphinxcontrib-mermaid==2.1.1` to the `docs` dependency group and enable
  `sphinxcontrib.mermaid` in `docs/conf.py`, with `myst_fence_as_directive = ["mermaid"]`,
  `mermaid_output_format = "raw"`, `mermaid_use_local = "vendor/mermaid/mermaid.esm.min.mjs"`,
  `mermaid_version = "11.12.1"`, and `mermaid_height = "auto"`. Verify `hatch run docs:build`
  completes with no warnings.
- [x] 1.2 Vendor the Mermaid 11.12.1 ESM entry, `chunks/mermaid.esm.min/`, the upstream `LICENSE`,
  and a `README.md` that records the version, source URL, and replacement procedure under
  `docs/_static/vendor/mermaid/`, excluding source maps. Verify the entry and at least one chunk
  exist and that `hatch run docs:build` copies them into
  `docs/_build/html/_static/vendor/mermaid/`.
- [x] 1.3 Extend `tests/docs/test_style.py` to assert that the vendored entry module and at least one
  chunk exist, and that the configured `mermaid_use_local` path is local rather than a URL. Verify
  `hatch test tests/docs/test_style.py` passes against the new runtime.

## 2. Architecture diagram and author convention

- [x] 2.1 Replace the ASCII layer block in `docs/develop/architecture.md` with a `flowchart TD` that
  uses `accTitle`, `accDescr`, and `used by` edges, keeping the surrounding prose and the
  `models <- core <- ui` dependency explanation. Verify `hatch run docs:serve` renders the diagram in
  light and dark themes and at a narrow window.
- [x] 2.2 Confirm that the vault layout blocks in `docs/getting-started/first-vault.md` and
  `docs/reference/vault-format.md`, and the output block in `docs/guide/command-line.md`, remain
  `text` fences. Verify the three pages in `docs:serve` and confirm no other `+---+` box art remains
  in `docs/`.
- [x] 2.3 Add a Diagrams section to `docs/develop/documentation.md` covering when to use Mermaid,
  when to keep literal text, the plain ` ```mermaid ` fence syntax, the required `accTitle` and
  `accDescr` lines, the offline runtime rule, and the fact that syntax errors are verified in
  `docs:serve` rather than `docs:build`. Add a Diagrams row to the emoji palette. Verify
  `hatch run docs:build` and the docs style test pass.
- [x] 2.4 Extend `tests/docs/test_style.py` to reject `+---+` box art in fenced blocks and require
  `accTitle` and `accDescr` in every `mermaid` fence. Verify `hatch test tests/docs/test_style.py`
  passes, and that the checks fail on synthetic box-art and missing-accessibility inputs.

## 3. Release record and integration

- [x] 3.1 Add an `Unreleased` → `Added` entry to `CHANGELOG.md` that names the Mermaid architecture
  diagram and the offline vendored runtime, and record that `README.md` needs no change. Verify the
  entry is under `Unreleased` and no version bump is made.
- [x] 3.2 Run `hatch run docs:build`, `hatch test tests/docs/test_style.py`, `hatch check`,
  `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and both vocabulary
  greps. Verify the built architecture page references the local Mermaid runtime and no `jsdelivr`
  URL, and that no docs command requires Node.js or `mmdc`.

## Workflow follow-up

- Archive the change after review. This is a docs-only change and does not complete the `1.0.0` MVP
  milestone, so keep the changelog entry under `Unreleased` and do not bump the version.
