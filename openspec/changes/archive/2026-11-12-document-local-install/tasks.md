# Tasks

## 1. Local installation documentation

- [x] 1.1 Remove the package-index badges and `pip install` commands from `README.md`; replace
  the install section with the source-checkout Hatch path and the browser command. Verify the
  README renders with the existing heading and admonition rules.
- [x] 1.2 Rewrite `docs/getting-started/install.md` as "Run Afanes": prerequisites, source
  checkout, browser presentation, local packaged build, provisioning table, and the Hatch
  installation check. Update the inbound "Install Afanes" wording in `docs/index.md`.
- [x] 1.3 Update `docs/guide/browser-mode.md` and `docs/reference/troubleshooting.md` to use
  `hatch env create` and `hatch run afanes` commands, and rename their "Install Afanes" links.
- [x] 1.4 Record the local-only distribution constraint in `RELEASE.md` and
  `docs/develop/releasing.md`, and add an `Unreleased` changelog entry for the corrected guidance.

## 2. Verification

- [x] 2.1 Run `hatch run docs:build`, `hatch test tests/docs/test_style.py`, `hatch check`,
  `openspec validate --all --strict`, `openspec doctor`, and the section 6.1 vocabulary grep.
  Confirm no package-index install command remains in `README.md` or `docs/`.

## Workflow follow-up

- Archive the change after review and after every task is checked.
- Run the post-archive release workflow in `AGENTS.md` section 5.3.
