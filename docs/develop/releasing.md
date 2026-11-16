# 🚢 Releasing and packaging

A release carries a Linux native build and a Python wheel. A packaged desktop artifact bundles the
interface client, so the application starts with no network access. The native build runs on a pinned
Linux runner; there is no cross-platform desktop build.

:::{admonition} tl;dr
:class: note

Push a `v<major>.<minor>.<patch>` tag. `.github/workflows/release.yml` verifies the tag against the
project version and the changelog, runs the automated gates, builds the Linux bundle and the wheel,
and publishes the GitHub release with a checksum file. A manual dispatch only builds and uploads.
Linux is the only release gate; run its offline-start check on the dispatch artifact before the tag.
:::

## 🔖 Cut a release

A release is a deliberate act. Archiving a change leaves its entry under `Unreleased` and does not
bump the version or create a tag.

1. Bump with `hatch version patch|minor|major`.
2. Move the `Unreleased` entries under `## [X.Y.Z] - YYYY-MM-DD`, leave a fresh `Unreleased`, and
   commit.
3. Dispatch a dry run for the evidence: `gh workflow run release.yml`, then `gh run watch`. It builds
   and uploads the artifacts and publishes nothing.
4. Download the artifact, verify its checksums, and run the packaged manual gate below.
5. Push the tag: `git tag v1.0.0 && git push origin v1.0.0` (use the version from step 1). The tag run
   repeats the gates and publishes the release.

## 📦 What the workflow builds

The build job runs on a pinned `ubuntu-24.04` runner. It installs the Flutter SDK through `flet build`
and the native toolchain (`clang`, CMake, Ninja, `pkg-config`, and the GTK 3 development libraries),
runs `hatch check` and `hatch test --cover`, builds the bundle with
`hatch run package linux --yes --build-version "$(hatch version)"`, builds the wheel with
`hatch build -t wheel`, and writes `afanes-<version>-checksums.txt` with a SHA-256 entry for each
artifact.

A `preflight` job checks the release identity before anything is built: the tag must match
`v<major>.<minor>.<patch>`, its number must equal `hatch version`, and `CHANGELOG.md` must have a
released section for that version. A manual dispatch or a `release/**` branch build skips the tag
check, builds, uploads, and publishes nothing.

Download a dry-run artifact, verify it, and extract it into a dedicated directory:

```console
gh run download <run-id> -n afanes-release
sha256sum -c afanes-<version>-checksums.txt
mkdir afanes-linux-x64
tar -xzf afanes-linux-x64-<version>.tar.gz -C afanes-linux-x64
```

The run summary records the commit, version, runner image, tool versions, and checksums. The workflow
artifact is short-lived and not a release asset. The extracted Linux bundle is the packaged manual
gate; run the offline-start check on it before pushing the tag. The wheel goes through its own
isolated install check.

A local build remains the fallback. Install the Flutter SDK first; `flet build` stops and names the
toolchain it needs when one is missing. The Linux toolchain is `clang`, CMake, Ninja, `pkg-config`,
and the GTK 3 development libraries. Build only on the host OS:

```console
hatch run package linux --build-version "$(hatch version)"
```

The `package` script compiles the gettext `.mo` catalogs before invoking `flet build`. The artifact is
written under `build/linux/`. `--build-version` records the project version from `hatch version`; the
build never carries a second version number. The launcher is `src/main.py`, and `[tool.flet.app]`
points the build at the `src` directory. Build-time dependency resolution is the only network
activity; the packaged application makes no request at startup.

macOS and Windows use the wheel and `afanes --web`; their local native builds are not release
artifacts.

## 🚀 Publication

The publish job runs only for a `v*` tag and holds the only write token. It downloads the artifact,
re-verifies the checksums, refuses to continue when the tag already has a release, creates a draft
with notes taken from the changelog section plus the version, commit, run, runner image, and
checksums, uploads the bundle, the wheel, and the checksum file, and then publishes the draft. If a
step after the draft fails, the job deletes the draft it created, so a partial release never becomes
public.

A published release is immutable. Re-running the workflow for the same tag fails and names the
existing release; the pipeline never overwrites a published asset. To roll back a bad release, delete
the release, keep the tag, fix forward, and ship a patch version.

## 🧾 Release artifacts

A published release carries:

- the Linux native build, tested and supported;
- the Python wheel, installed with `pipx`, for the macOS and Windows browser path;
- `afanes-<version>-checksums.txt`, also reproduced in the release notes.

Native macOS and Windows binaries are not release artifacts. Every artifact is unsigned. There is no
PyPI publication and no code signing, notarization, or auto-update.

The wheel must prove that `afanes --web` starts with networking unavailable. If the Flet web client is
fetched at startup, bundle it in the wheel or record the limitation in the release notes.

## 🔌 Check the offline start

1. Launch the Linux artifact with networking unavailable.
2. Open a vault.
3. Capture a note.
4. Compare the written Markdown with a source run byte for byte.
5. Confirm the artifact metadata reports the same version as `hatch version`.

The window must open without downloading a client. The automated suite also covers the workspace
refresh behavior when a file changes outside the application.

For the wheel, create an isolated environment with `pipx install`, disable networking, run
`afanes --web`, open the reported address, and confirm the workspace loads and can capture a note.

## 🏷️ Versioning

The version lives in `src/afanes/__about__.py` and is read through `hatch version`. Never edit that file
directly. Versions move only when a release is cut; an archived change keeps its `Unreleased` entry and
leaves the version alone.

`1.0.0` follows only when the whole gate is green: open a vault, capture, clarify, browse, and review
without hand-editing files, plus HIG conformance, English and Spanish, and note reminders. Until then,
incompatible changes to unreleased APIs are MINOR or PATCH bumps, never MAJOR.

## 🧾 Release readiness

`RELEASE.md` is the single definition of the unified gate, the per-flow evidence, the artifact policy,
and the Linux-only platform matrix. `CHANGELOG.md` records observable outcomes under Keep a Changelog
headings. The release workflow also reviews `README.md` and `docs/` and records when neither changed.

## 🧭 See also

- [Run Afanes](../getting-started/install.md)
- [Browser mode](../guide/browser-mode.md)
- [Development setup](setup.md)
- [RELEASE.md](https://github.com/knkillname/afanes/blob/main/RELEASE.md)
