# 🚢 Releasing and packaging

A release carries a Linux native build and a Python wheel. A packaged desktop artifact bundles the
interface client, so the application starts with no network access. The native build runs on a pinned
Linux runner; there is no cross-platform desktop build.

:::{admonition} tl;dr
:class: note

Dispatch `.github/workflows/linux-release.yml` on a pinned `ubuntu-24.04` runner. It runs the
automated gates, builds with `hatch run package linux --yes --build-version "$(hatch version)"`, and
uploads the checksummed bundle. Download, verify, and attach the Linux build and the wheel to the
GitHub release by hand. Linux is the only release gate; run its offline-start check before
publishing.
:::

## 📦 Build the Linux artifact

The release build runs in GitHub Actions on `ubuntu-24.04`. The workflow installs the Flutter SDK
through `flet build` and the native toolchain (`clang`, CMake, Ninja, `pkg-config`, and the GTK 3
development libraries), runs `hatch check` and `hatch test --cover`, and builds with the project
version:

```console
gh workflow run linux-release.yml
gh run watch
```

Download the workflow artifact, verify its checksum, and extract it into a dedicated directory:

```console
gh run download <run-id> -n afanes-linux-x64
sha256sum -c afanes-linux-x64-<version>.tar.gz.sha256
mkdir afanes-linux-x64
tar -xzf afanes-linux-x64-<version>.tar.gz -C afanes-linux-x64
```

The run summary records the commit, version, runner image, tool versions, and SHA-256. The workflow
artifact is public, short-lived, and not a release asset. The extracted bundle is the tested and
supported `1.0.0` artifact and the only manual release gate; run the offline-start check on it before
publishing.

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

## 🧾 Release artifacts

The GitHub release carries:

- the Linux native build, tested and supported;
- the Python wheel, installed with `pipx`, for the macOS and Windows browser path.

Native macOS and Windows binaries are not release artifacts. Artifacts are attached by hand for
`1.0.0`; there is no automatic publish pipeline. Every artifact is unsigned. There is no PyPI
publication and no code signing, notarization, or auto-update.

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
by hand; use `hatch version patch`, `hatch version minor`, or `hatch version major` when a coherent
group of work completes.

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
