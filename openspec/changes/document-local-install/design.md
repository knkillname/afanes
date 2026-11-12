# Design

## Context

See `proposal.md` for motivation. `AGENTS.md` already defines Hatch as the only developer
interface and `docs/develop/releasing.md` already describes local packaged artifacts under
`build/<platform>/`. The documentation contradicts those documents by presenting package-index
installs as the primary path.

## Goals / Non-Goals

**Goals:**

- Give one reproducible installation path today: a source checkout run through Hatch.
- Keep the browser presentation available from the same checkout.
- Present local packaged builds as the only distributable artifact.
- Leave no package-index commands or badges in the user-facing documentation.

**Non-Goals:**

- Publishing a package or configuring GitHub Releases.
- Removing the `desktop` and `web` extras from `pyproject.toml`; they remain packaging metadata.
- Changing the launcher, runtime checks, or Flet client provisioning.

## Decisions

### Source checkout is the primary path

Document `git clone`, `hatch env create`, and `hatch run afanes`. The browser form is
`hatch run afanes --web`. The module form is `hatch run python -m afanes`. This matches
`docs/develop/setup.md` and the repository operating manual.

### Packaged builds are local artifacts

Document `hatch run flet build <platform> --build-version "$(hatch version)"` as the packaged
path, with the Flutter and native-toolchain prerequisite and a link to the release guide. Artifacts
stay unsigned and local. GitHub release publishing is explicitly a later decision.

### Verification stays documentation-focused

Run `hatch run docs:build`, the documentation style test, `hatch check`, `openspec validate`, and
the vocabulary grep. A documentation-only change does not need the full test matrix, but the
existing suite must not regress.

## Risks / Trade-offs

- **Users expect an install command** -> The README states the source-checkout requirement in the
  first install section and links to the run page.
- **Stale links still say "Install"** -> Rename the page title and every inbound link to "Run
  Afanes".
- **Future GitHub releases change the story** -> Keep the decision in `RELEASE.md` as a current
  constraint, not a permanent promise.

## Migration Plan

1. Update the README and run page.
2. Update the browser, troubleshooting, and release pages.
3. Record the constraint and changelog entry.
4. Build the docs and run the gates.

## Open Questions

None blocking.
