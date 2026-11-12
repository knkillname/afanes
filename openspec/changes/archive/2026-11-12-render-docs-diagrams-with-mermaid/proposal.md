# Proposal

## Why

The documentation site has one real diagram: the package-layer sketch in
`docs/develop/architecture.md`. It is hand-drawn box art inside a `text` fence. It does not reflow on
narrow screens, it does not follow the theme, and every edit means re-aligning characters by hand.
The rest of the docs are Markdown, screenshots, and tables, so Mermaid is the missing authoring tool
for relationships and flows.

The docs also promise a local-only build and preview. Mermaid's default Sphinx integration loads the
runtime from a CDN at page load, which would silently break that promise. This change adds Mermaid
without adding a network dependency or a second build toolchain.

## What Changes

- Add `sphinxcontrib-mermaid==2.1.1` to the `docs` dependency group and enable
  `sphinxcontrib.mermaid` in `docs/conf.py`.
- Vendor the Mermaid 11.12.1 ESM runtime under `docs/_static/vendor/mermaid/`, including the entry
  module, its chunks, the MIT license, and a version/source note. No source maps.
- Configure `myst_fence_as_directive = ["mermaid"]` so plain ` ```mermaid ` fences render in Sphinx
  and on GitHub, and point `mermaid_use_local` at the vendored runtime. Keep `mermaid_output_format`
  at `raw` so rendering stays in the browser and the build stays Python-only.
- Replace the ASCII layer diagram with a `flowchart TD` that uses `accTitle` and `accDescr`.
- Keep the vault directory trees and command output as `text` blocks; they are literal, copyable
  content, not diagrams.
- Document the diagram convention in `docs/develop/documentation.md`: when to use Mermaid, when not
  to, the accessibility lines, the offline runtime rule, and the fact that a syntax error is caught
  in `docs:serve`, not by `docs:build`.
- Extend `tests/docs/test_style.py` to reject `+---+` box art, require `accTitle`/`accDescr` in every
  Mermaid fence, and assert that the vendored runtime is present and referenced locally.
- Record the change under `Unreleased` in `CHANGELOG.md`; `README.md` needs no change and no version
  bump is warranted.

Out of scope: a second diagram for the capture → clarify → browse → review flow, build-time SVG
rendering, GitHub Pages publishing, and any application behavior or runtime dependency.

## Capabilities

### New Capabilities

None. This is a documentation and tooling change with no product behavior changes, so the change sets
`skip_specs: true` instead of inventing a requirement.

### Modified Capabilities

None.

## Impact

- `pyproject.toml` gains one docs-only dependency; the shipped application keeps its offline runtime
  and adds no account, telemetry, cloud, or network behavior.
- `docs/conf.py` gains the Mermaid extension and offline configuration.
- `docs/_static/vendor/mermaid/` adds 74 static files: about 2.6 MB on disk and roughly 0.77 MB
  compressed in git. Only pages that contain a diagram load the runtime.
- `docs/develop/architecture.md` and `docs/develop/documentation.md` change; the architecture diagram
  is replaced and the diagram convention is added.
- `tests/docs/test_style.py` gains documentation checks.
- `CHANGELOG.md` records the change under `Unreleased`.
- No application code, vault format, CLI, UI, or public Python API changes. The static runtime is
  cross-platform and needs no Node.js or Chromium.
- A broken Mermaid diagram is a browser-side error, not a build failure. The style test enforces the
  fence structure and accessibility metadata, but Mermaid syntax is verified visually in
  `hatch run docs:serve`.
