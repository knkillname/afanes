# 🚢 Releasing and packaging

A release carries a Linux native build, a Python wheel, and any qualifying experimental macOS or
Windows native binary. A packaged desktop artifact bundles the interface client, so the application
starts with no network access. Each native artifact is built on its own operating system; there is no
cross-platform desktop build.

:::{admonition} tl;dr
:class: note

Build with `flet build <platform> --build-version "$(hatch version)"` on the host OS. Attach the
Linux build and the wheel to the GitHub release by hand. Linux is the only release gate; run its
offline-start check before publishing.
:::

## 📦 Build a desktop app

Install the Flutter SDK first; `flet build` stops and names the toolchain it needs when one is missing.
The native build tools are also required: Xcode command line tools on macOS, Visual Studio Build Tools
on Windows, and `clang`, CMake, Ninja, and the GTK 3 development libraries on Linux.

```console
hatch run flet build linux --build-version "$(hatch version)"
hatch run flet build macos --build-version "$(hatch version)"
hatch run flet build windows --build-version "$(hatch version)"
```

Run only the command for the machine you are on. The artifact is written under `build/<platform>/`.
`--build-version` records the project version from `hatch version`; the build never carries a second
version number. The launcher is `src/main.py`, and `[tool.flet.app]` points the build at the `src`
directory. Build-time dependency resolution is the only network activity; the packaged application
makes no request at startup.

Build and test the Linux artifact on Linux. That build is the supported `1.0.0` artifact and the only
manual release gate. The macOS and Windows builds are experiments: a scheduled workflow attempts them,
and a binary is attached to the release only when that platform's tests and build both pass in the
same nightly run. An attached binary is untested at runtime, unsigned, and unsupported.

## 🧾 Release artifacts

The GitHub release carries:

- the Linux native build, tested and supported;
- the Python wheel, installed with `pipx`, for the macOS and Windows browser path;
- any qualifying experimental macOS or Windows native binary, labeled untested, unsigned, and
  unsupported.

Artifacts are attached by hand for `1.0.0`; there is no automatic publish pipeline. Every artifact is
unsigned. There is no PyPI publication and no code signing, notarization, or auto-update.

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

## 🌙 Nightly advisory builds

A scheduled GitHub Actions workflow runs `hatch check` and `hatch test` on macOS and Windows and
attempts a native build for each. The workflow is advisory: it is not a required check and never
blocks a merge, a release, or `1.0.0`. Its artifacts are short-lived workflow artifacts, not release
assets. A green run is the only source for an experimental release binary, and that binary is attached
manually.

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
