# Proposal

## Why

The `1.0.0` gate is blocked before the first Linux artifact: the maintainer's
machine has no `clang`, CMake, Ninja, `pkg-config`, or GTK 3 development
headers, and there is no CI to build on another machine. The release documents
also describe a scheduled macOS and Windows nightly workflow that has never
existed in the repository, so the documented release surface is larger than the
one the project can actually produce.

A pinned Linux release workflow on GitHub Actions closes the build gap without
changing the runtime: the application remains offline, and the maintainer still
runs the packaged manual gate on the downloaded artifact.

## What Changes

- Add a manually dispatched Linux release workflow on `ubuntu-24.04` that
  installs the documented native toolchain, runs `hatch check` and
  `hatch test --cover`, builds with the project version, packages the bundle as
  a `tar.gz` with a SHA-256 checksum, uploads it as a workflow artifact, and
  records the commit, runner image, tool versions, and checksum in the run
  summary.
- Update `AGENTS.md` so the operating manual no longer claims there is no CI.
  The Linux release workflow builds and verifies the artifact; the local gates,
  the packaged manual gate, and the release decisions remain local and manual.
- Update `RELEASE.md`, `docs/develop/releasing.md`,
  `docs/getting-started/install.md`, `docs/develop/setup.md`, and `README.md`
  for the workflow build path and the downloaded-artifact evidence.
- Remove the macOS and Windows nightly workflow promise and the experimental
  native binary from the current release surface. The Linux native build and the
  wheel remain the release artifacts; a nightly workflow can land in a later
  change.
- Fix the Python 3.13 failures exposed by the runner gates:
  `afanes.ui.state.navigation` imports `BrowserState` directly instead of
  resolving the submodule through the partially initialized package, and the
  frontmatter round-trip strategy formats month-precision dates with an
  explicit zero-padded year. This restores the supported Python 3.13 runtime
  and changes no behavior on 3.14.
- Add one `Unreleased` changelog entry. No version bump, no runtime behavior
  change, no dependency change, and no new capability requirement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The packaged build already carries the interface client and starts
offline by requirement; this change only changes where and how that artifact is
built and how the release evidence is recorded. The change sets
`skip_specs: true`.

## Impact

- `.github/workflows/linux-release.yml` is new.
- `AGENTS.md`, `RELEASE.md`, `docs/develop/releasing.md`,
  `docs/getting-started/install.md`, `docs/develop/setup.md`, `README.md`, and
  `CHANGELOG.md` change.
- `src/afanes/ui/state/navigation.py` changes one import and one annotation to
  fix the Python 3.13 import order. `tests/core/test_frontmatter.py` formats a
  generated month-precision date explicitly and gains a leading-zero-year
  regression. No dependency, schema, vault-format, or public API change.
- The build uses network access on the runner for the toolchain and Flutter
  dependencies. The packaged application still makes no request at startup.
- The workflow needs the source and workflow file on GitHub. The local `main`
  is currently ahead of `origin/main`, so the implementation must push a branch
  or `main` before the first run.
- The workflow artifact is public, short-lived, and not a release asset.
  Release attachment stays manual, and the packaged manual gate still runs on
  the maintainer's Linux desktop.
