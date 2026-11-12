# 📦 Run Afanes

Afanes runs from a source checkout. Hatch creates the environment and starts either presentation; a
local packaged build is the only distributable artifact for now.

:::{admonition} tl;dr
:class: note

Run `hatch env create`, then `hatch run afanes` for the desktop window or `hatch run afanes --web` for
the browser presentation. Packaged desktop builds are local artifacts.
:::

## 🧰 Prerequisites

- Python 3.13 or newer.
- Git.
- [Hatch](https://hatch.pypa.io/) for the environment and every project command.
- The Flutter SDK and native build tools only when you build a packaged desktop artifact.

## 💻 Desktop application

```console
git clone https://github.com/knkillname/afanes.git
cd afanes
hatch env create
hatch run afanes
```

`hatch env create` installs the runtime dependencies in the checkout-owned environment. The first
development run downloads and caches the Flet client under `~/.flet/client/`. That download is
provisioning, not application behavior: the running app never fetches a package or calls a service.

A packaged desktop build bundles the client and starts with no network access. The release guide
covers that path.

## 🌐 Browser presentation

```console
hatch run afanes --web
```

The module form, `hatch run python -m afanes --web`, works the same. Every interface asset comes from
the local environment, so a session works with no network access after the environment is created.
The server binds loopback only, and one browser session can drive the workspace at a time. The desktop
window stays the default; `--web` is an explicit opt-in.

## 📦 Build a local desktop artifact

```console
hatch run flet build <platform> --build-version "$(hatch version)"
```

Run only the command for the host operating system: `linux`, `macos`, or `windows`. The artifact is
written under `build/<platform>/` and is an unsigned local build. Install the Flutter SDK and the
native build tools first; the [release guide](../develop/releasing.md) lists the per-platform
requirements and the offline-start check.

Distribution is limited to local builds for now. There is no publishing step in this repository.

## 📡 First-run provisioning

| Presentation | Client source | Network needed at start |
| --- | --- | --- |
| Desktop (source checkout) | Flet client cached on first run under `~/.flet/client/` | Once, for provisioning |
| Desktop (packaged build) | Bundled in the artifact | No |
| Browser | Included in the development environment | No |

:::{warning}
Create the environment with `hatch env create` before starting Afanes. Starting the app is not a
supported installation path, and a missing runtime is reported as a launch error instead of being
silently downloaded.
:::

## ✅ Check the run

```console
hatch run afanes --help
```

The command reports the launch options and the headless vault commands. With the environment ready,
`hatch run afanes` starts the interface; `hatch run afanes vault create DIR` creates a vault without
opening a window.

Afanes supports Flet 1.0.4 and later 1.x releases. `hatch test --all` runs the suite on every
supported interpreter and against the oldest supported dependency versions.
