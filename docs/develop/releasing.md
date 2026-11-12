# 🚢 Releasing and packaging

A packaged desktop artifact bundles the interface client, so the application starts with no network
access. Each artifact is built on its own operating system; there is no cross-platform desktop build.

:::{admonition} tl;dr
:class: note

Build with `flet build <platform> --build-version "$(hatch version)"` on the host OS. Launch the
artifact with networking unavailable, open a vault, and confirm a captured note matches a source run
byte for byte.
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

Artifacts are unsigned local builds. Code signing, notarization, auto-update, and a publishing pipeline
are not part of this project yet.

## 🔌 Check the offline start

1. Launch the artifact with networking unavailable.
2. Open a vault.
3. Capture a note.
4. Compare the written Markdown with a source run byte for byte.
5. Confirm the artifact metadata reports the same version as `hatch version`.

The window must open without downloading a client. Linux is verified locally; the macOS and Windows
checks are tracked in `RELEASE.md` until they are run on those machines. The automated suite also
covers the workspace refresh behavior when a file changes outside the application.

## 🏷️ Versioning

The version lives in `src/afanes/__about__.py` and is read through `hatch version`. Never edit that file
by hand; use `hatch version patch`, `hatch version minor`, or `hatch version major` when a coherent
milestone completes.

`1.0.0` is reserved for the first usable MVP: open a vault, capture, clarify, browse, and review without
hand-editing files. Until then, incompatible changes to unreleased APIs are MINOR or PATCH bumps, never
MAJOR.

## 🧾 Release readiness

`RELEASE.md` is the single definition of the first usable MVP, the per-flow evidence, and the platform
matrix. `CHANGELOG.md` records observable outcomes under Keep a Changelog headings. The release workflow
also reviews `README.md` and `docs/` and records when neither changed.

## 🧭 See also

- [Install Afanes](../getting-started/install.md)
- [Browser mode](../guide/browser-mode.md)
- [Development setup](setup.md)
- [RELEASE.md](https://github.com/knkillname/afanes/blob/main/RELEASE.md)
