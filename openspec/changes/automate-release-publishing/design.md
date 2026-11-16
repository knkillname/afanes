# Design

## Context

See `proposal.md` for motivation. The current pipeline is
`.github/workflows/linux-release.yml`: manual dispatch (plus a `release/**`
push fallback), a read-only token, `runs-on: ubuntu-24.04`, the automated
gates, `hatch run package linux --yes --build-version "$(hatch version)"`, and a
checksummed `tar.gz` uploaded with `retention-days: 14`. It cannot create a
release, does not build the wheel, and its artifact needs a GitHub login to
download.

The version lives in `src/afanes/__about__.py` and is read through
`hatch version`; it is never edited by hand. `hatch build` produces
`dist/afanes-<version>-py3-none-any.whl`, and `hatch_build.py` compiles the
gettext catalogs into the wheel. The `web` and `desktop` extras already exist
in `pyproject.toml`.

`RELEASE.md` defines the `1.0.0` MVP gate and the manual packaged checks; its
work sequence names packaging and Linux evidence as the next step. The change
`add-linux-release-workflow` is still open with tasks 3.1 and 3.2 pending, and
its tasks name the current workflow path.

## Goals / Non-Goals

**Goals:**

- One workflow that builds, gates, and publishes both supported artifacts.
- Tag identity checked before any expensive work starts.
- Publication that is automatic, traceable, and atomic with respect to failure.
- A release pipeline whose published bytes can be re-verified by any user.
- The first real release: `1.0.0` with recorded packaged evidence.

**Non-Goals:**

- Native macOS or Windows builds, code signing, notarization, or auto-update.
- PyPI publication; the wheel is a release asset.
- Build reproducibility or byte-for-byte evidence between the pre-tag artifact
  and the published one.
- Build provenance attestations; deferred to a later change if the project
  adopts them.
- Pre-release tags (`v1.0.0-rc.1`); the pipeline accepts `vX.Y.Z` only.

## Decisions

### D1. One workflow, renamed to `release.yml`

Replace `.github/workflows/linux-release.yml` with
`.github/workflows/release.yml`. Triggers: `workflow_dispatch`, `push` to
`release/**` for a pre-tag dry run, and `push` to tags matching `v*`. Keep the
`release` concurrency group with `cancel-in-progress: false` and the 60-minute
timeout.

Only the tag trigger publishes; the publish job is guarded by
`if: startsWith(github.ref, 'refs/tags/v')`. A dispatch or `release/**` build
runs the same gates, build, and artifact upload, then stops. That keeps the
dry-run path used for `1.0.0` evidence identical to the publishing path.

Alternatives: keeping the `linux-release` name (misleading once it publishes
and ships a wheel), or a separate `workflow_run` publisher (a second checkout
and an indirect commit binding for no benefit).

### D2. The tag and the project version must agree before building

A `preflight` job with `contents: read` and no checkout beyond the commit
compares `GITHUB_REF_NAME` without its `v` prefix against `hatch version`, and
checks that `CHANGELOG.md` contains a released heading `## [<version>] -`. It
also rejects tags that are not `vX.Y.Z`. The build job depends on it.

Rationale: a tag is the release decision, but the version is a single source of
truth in the repository. Checking first fails in seconds instead of after a
Flutter build, and stops a mislabelled artifact from ever existing.

Alternatives: deriving the version from the tag (diverges from the About dialog
and wheel metadata), or checking inside the build job (wastes the build when the
tag is wrong).

### D3. Separate build and publish jobs, with the write token only in publish

The build job keeps `permissions: contents: read` and every pinned action SHA.
It runs the toolchain install, `hatch check`, `hatch test --cover`,
`hatch run package linux --yes --build-version "$(hatch version)"`, and
`hatch build -t wheel`. It writes the bundle `tar.gz`, the wheel, and an
`afanes-<version>-checksums.txt` covering both, then uploads the three files.

The publish job declares `permissions: contents: write`, downloads the
artifact, re-computes the SHA-256 values, and fails if they differ from the
uploaded checksum file. Re-verifying after the download proves the bytes that
are about to be published, and it also catches a truncated artifact transfer.

Alternatives: publishing from the build job (gives every build step a write
token), or computing checksums only at publish time (cannot detect a corrupted
artifact transfer).

### D4. Publish through a draft, then make it public

The publish job refuses to run when `gh release view "$tag"` succeeds; it names
the existing release and fails. Otherwise it creates a draft
(`gh release create --draft --verify-tag --notes-file`), uploads both assets,
and only then flips it with `gh release edit --draft=false`. If any step after
the draft is created fails, the job deletes the draft it created.

Rationale: `gh release create` with assets becomes visible before the uploads
finish, so a failed upload would leave a partial release. The draft gives the
required "no public partial release", and the existence check gives the required
immutability without `--clobber`.

The token is the workflow's `GITHUB_TOKEN`; no repository secret is introduced,
and no third-party release action is added.

Alternatives: `gh release create` directly (partial release visible on failure),
`softprops/action-gh-release` (third-party action with its own retry semantics),
or allowing `--clobber` (published bytes could silently change).

### D5. Publication does not wait for a reviewer

The publish job runs when the tag build is green. The packaged manual gate is no
longer a publication gate; it stays a required acceptance check for `1.0.0` and
is run on a dispatch artifact from the same commit before the tag is pushed.

Trade-off, accepted by the maintainer: a bundle that nobody has launched can
become public. Mitigations: the preflight and full automated gates, the
pre-tag packaged gate for `1.0.0`, immutable checksummed assets, release notes
that name the commit and run, and a documented rollback that deletes the
release while keeping the tag and ships the fix as a patch release.

Alternative: a GitHub Environment with required reviewers; that reintroduces
the manual step this change removes and was declined.

### D6. Release notes come from the changelog plus build metadata

The publish job extracts the `## [<version>] -` section from `CHANGELOG.md`
with `awk`, asserts it is non-empty, and appends the version, commit, run URL,
runner image, and both SHA-256 values. No new script is added.

Rationale: the changelog is already the curated user-facing record, and the
metadata is what makes an unsigned artifact traceable. Keeping the extraction
in the workflow avoids a maintained script and its tests for a few lines of
text handling.

Alternatives: `--generate-notes` (drops the curated changelog), or a Python
helper under `scripts/` (more surface than the problem warrants).

### D7. The `1.0.0` bump and tag happen in this change, after the pipeline lands

Order: archive `add-linux-release-workflow`; land the workflow and documentation;
`hatch version major`; move `Unreleased` into `## [1.0.0] - <date>`; dispatch a
dry run at `1.0.0`; download that artifact, run the complete packaged manual
gate, and record the evidence in `RELEASE.md`; commit; push `v1.0.0`; verify the
published assets and both installation paths.

This absorbs step 8 of `RELEASE.md`'s work sequence. `AGENTS.md` section 5.3 is
updated so the version bump happens before the tag and the archive step records
the archive without a second bump. `src/afanes/__about__.py` is still never
edited by hand.

### D8. Documentation names the released assets, not the workflow artifact

`README.md`, `docs/getting-started/install.md`, `docs/guide/browser-mode.md`,
`docs/develop/releasing.md`, `AGENTS.md`, and `RELEASE.md` describe the releases
page as the download source for both artifacts, the tag push as the publish
trigger, and the checksum file as the verification step. The workflow artifact
stays documented as a debugging and pre-tag evidence path with its 14-day
retention, never as the user-facing download.

### D9. Keep the platform surface unchanged

The Linux native bundle remains the only native artifact. The wheel is
platform-independent and covers the macOS and Windows browser path with the
`web` extra. The published application still starts with no network access; the
build-time dependency resolution and the publication machinery are the only
network activity.

### D10. Versions move only when a release is cut

Routine change archives keep their entries under `Unreleased`; no version bump,
tag, or release follows an archive. `AGENTS.md` section 5.3,
`openspec/config.yaml` archive guidance, `RELEASE.md`, and
`docs/develop/releasing.md` change accordingly. The preflight check enforces the
result: a tag cannot publish while the changelog still lists that version under
`Unreleased`, and a tag that disagrees with the project version fails.

A release remains the deliberate act: `hatch version patch|minor|major`, move
the `Unreleased` entries under the released heading, run the gates, push the
tag. The `1.0.0` bump in this change is that act, not an archive by-product.

Alternatives: keep bumping per archive (rejected: it manufactures a version and
a changelog section for every change, which the tag pipeline would then
publish), or let the pipeline derive the version from the tag (rejected: the
repository would stop being the single source of truth).

## Risks / Trade-offs

- **Published bytes differ from the pre-tag artifact.** Flutter builds are not
  byte-reproducible → the notes and `RELEASE.md` evidence name the commit and
  run so the gate is understood to cover the commit and version, not identical
  bytes; provenance attestations are deferred.
- **Unreviewed publication.** A green build can publish without a human →
  preflight, the full gates, the `1.0.0` pre-tag packaged gate, checksums, and
  the delete-release rollback.
- **A failed upload leaves a draft.** → the job deletes the draft it created;
  the existence check still blocks a second draft for the same tag.
- **Tag push rights equal publish rights.** → document that tag protection and
  repository permissions are the access control; no secret with broader scope is
  introduced.
- **`hatch version` output and the tag can drift** after the tag is pushed → no
  workflow edits the version; a mismatch fails preflight and the tag is deleted
  and re-pushed.
- **The first tag build is slow** on a cold runner (Flutter SDK and client
  download) → accepted, matching the existing workflow; caching is not a
  correctness requirement.
- **The wheel depends on the web extra** to work on macOS and Windows → the
  `1.0.0` gate installs the published wheel with `[web]` and starts it with
  networking unavailable, per `RELEASE.md`.

## Migration Plan

1. Archive `add-linux-release-workflow` after its tasks 3.1 and 3.2 complete.
2. Land `release.yml` with the docs and `AGENTS.md` updates; dispatch once to
   confirm the build and dry-run paths.
3. Bump to `1.0.0`, update the changelog, dispatch the dry run, download the
   `1.0.0` artifact, run the packaged manual gate, and record the evidence.
4. Commit, then push `v1.0.0`; verify the release assets, the checksum file, and
   both installation paths.
5. Rollback for a bad release: delete the published release, keep the tag, fix
   forward with a patch version and tag. Never overwrite published assets.
