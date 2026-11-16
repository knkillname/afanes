# Proposal

## Why

Afanes has no downloadable release. The Linux workflow uploads a 14-day,
login-only workflow artifact and the wheel is built by hand, so every "download
from the releases page" line in `README.md` and `docs/` currently dead-ends. The
first release is blocked on a manual step that has never been exercised: the
maintainer must download the artifact, verify its checksum, re-upload it, build
and attach the wheel, and write the notes.

The release surface is already defined — a Linux native build and a
platform-independent wheel for the macOS and Windows browser path — and the
build is already automated. Only publication is manual. Automating it removes
the last hand-carried bytes from the release path and makes the documented
installation instructions true.

## What Changes

- Trigger the release pipeline on a `v<major>.<minor>.<patch>` tag push in
  addition to the existing manual dispatch. A preflight job SHALL verify that
  the tag, the project version, and a released `CHANGELOG.md` section agree
  before anything is built.
- Build both release artifacts in CI from the tagged commit: the Linux bundle
  as a `tar.gz` and the Python wheel with its `web` and `desktop` extras. Emit
  a checksum file covering both.
- Publish a GitHub release automatically when the tag build and the automated
  gates pass: the two artifacts, the checksums, and notes naming the version,
  commit, run URL, and checksums. Remove the hand-attachment step.
- Keep the build job read-only and give only the publish job `contents: write`,
  so the build steps never hold a token that can change the repository.
- Make a re-run of the same tag safe: publish MUST NOT overwrite assets that a
  previous run already published, and MUST name the existing release instead.
- Change the version policy: archiving a change keeps its entry under
  `Unreleased` and does not bump the version or create a tag. A release is a
  deliberate act that bumps the version, moves the `Unreleased` entries under
  the released heading, and pushes the tag that publishes it.
- Replace the manual-attachment policy in `RELEASE.md`,
  `docs/develop/releasing.md`, `AGENTS.md` section 2, and the installation
  pages. The packaged manual gate stays required evidence for `1.0.0`; it moves
  to a pre-tag check on the `1.0.0` dispatch artifact instead of gating the
  upload.
- Rename the workflow to `.github/workflows/release.yml` to match its wider
  scope; manual dispatch remains for dry runs and gate evidence.
- Publish `1.0.0` as the first automated release: bump with
  `hatch version major`, move the `Unreleased` entries into the `1.0.0` section,
  complete the unified gate evidence, dispatch once for the packaged manual
  gate, then push `v1.0.0` and verify the published assets.

## Capabilities

### New Capabilities

- `release-distribution`: how Afanes turns a release tag into published,
  verified artifacts — tag and version agreement, required gates, artifact
  contents and checksums, automatic publication, and failure behavior.

### Modified Capabilities

None. The application's startup, offline, and presentation behavior is
unchanged; `app-runtime` already requires a packaged build to start with no
network access, and this change publishes that build rather than changing it.

## Impact

- `.github/workflows/linux-release.yml` is replaced by
  `.github/workflows/release.yml`; the build job keeps its pinned runner,
  toolchain, and read-only token, and a separate publish job gains
  `contents: write`.
- `AGENTS.md` sections 2 and 5.3, `openspec/config.yaml` archive guidance,
  `RELEASE.md`, `docs/develop/releasing.md`,
  `docs/getting-started/install.md`, `docs/guide/browser-mode.md`, `README.md`,
  and `CHANGELOG.md` change.
- Project version becomes `1.0.0`; `hatch version` remains the single source of
  truth and `src/afanes/__about__.py` is never edited by hand.
- No runtime code, test, dependency, schema, or application behavior changes.
  The published application still makes no network request at startup; only the
  build-time dependency resolution and the publication machinery use the
  network.
- Depends on `add-linux-release-workflow` being archived first, because its
  pending tasks 3.1 and 3.2 name the current workflow path and the dry-run
  evidence this change builds on.
- Deferred: native macOS and Windows builds, code signing, notarization,
  auto-update, PyPI publication, and build reproducibility guarantees.
