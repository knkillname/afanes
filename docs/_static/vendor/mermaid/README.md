# Mermaid 11.12.1 (vendored)

This directory carries the unmodified Mermaid browser runtime so the documentation renders diagrams
without a network request. Do not edit these files.

## Contents

- `mermaid.esm.min.mjs` — the ESM entry module.
- `chunks/mermaid.esm.min/` — the ESM chunks the entry imports.
- `LICENSE` — the upstream MIT license.

Source maps (`*.map`) and the `README` files from the package are not copied.

## Source

- Package: `mermaid@11.12.1`
- Tarball: <https://registry.npmjs.org/mermaid/-/mermaid-11.12.1.tgz>
- Package page: <https://www.npmjs.com/package/mermaid/v/11.12.1>

## Replacing the runtime

1. Download the tarball for the target version and unpack it into a temporary directory.
2. Copy `package/dist/mermaid.esm.min.mjs` over the entry module here.
3. Replace `chunks/mermaid.esm.min/` with `package/dist/chunks/mermaid.esm.min/`, keeping only
   `*.mjs` files.
4. Copy `package/LICENSE` over `LICENSE`.
5. Update the version in this file and `mermaid_version` in `docs/conf.py`; keep both in step with the
   files above.
6. Run `hatch run docs:build`, open the architecture page with `hatch run docs:serve` in both themes,
   and confirm the diagram still renders.

The extension is expected to bundle its own runtime in its 3.0 line. When that release is adopted,
this directory and `mermaid_use_local` can be removed without changing the page source.
