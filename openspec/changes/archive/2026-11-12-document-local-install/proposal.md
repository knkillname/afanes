# Proposal

## Why

The README and the getting-started, browser, and troubleshooting pages tell users to install
`afanes[desktop]` or `afanes[web]` from a package index, and the README shows package-index badges.
Afanes is not published, so those instructions cannot work. The maintainer wants local builds only
for now, with a later decision about GitHub release artifacts.

## What Changes

- Remove the package-index badges and `pip install` commands from `README.md`.
- Make the README install section a source-checkout path: clone, `hatch env create`,
  `hatch run afanes`, and `hatch run afanes --web`.
- Rewrite `docs/getting-started/install.md` as "Run Afanes": prerequisites, source checkout,
  browser presentation, and a local packaged build. Remove the extra-install and wheel language.
- Update `docs/guide/browser-mode.md` and `docs/reference/troubleshooting.md` to use the Hatch
  commands from a source checkout.
- Rename the remaining "Install Afanes" links and page title to "Run Afanes".
- Record the local-only distribution decision in `RELEASE.md` and `docs/develop/releasing.md`.
- Add an `Unreleased` changelog entry for the corrected install guidance.
- Out of scope: publishing to any package index, creating GitHub releases, changing the Flet
  runtime extras in `pyproject.toml`, or changing application behavior.

## Capabilities

No capability specs change. This is a documentation-only correction, so the change declares
`skip_specs: true`.

## Impact

- `README.md`
- `docs/index.md`
- `docs/getting-started/install.md`
- `docs/guide/browser-mode.md`
- `docs/reference/troubleshooting.md`
- `docs/develop/releasing.md`
- `RELEASE.md`
- `CHANGELOG.md`

No source, test, dependency, or vault behavior changes.
