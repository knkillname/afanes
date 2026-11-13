# 📦 Run Afanes

Afanes runs from a source checkout with Hatch, from the Linux native build on the releases page, or
from the released Python wheel on macOS and Windows. The desktop window is the default; `afanes --web`
serves the same interface to a browser.

:::{admonition} tl;dr
:class: note

On Linux, run `hatch env create`, then `hatch run afanes` for the desktop window, or install the
release build. On macOS and Windows, install the released wheel with `pipx` and run `afanes --web`.
:::

## 🧰 Prerequisites

- Python 3.13 or newer.
- Git and [Hatch](https://hatch.pypa.io/) for a source checkout.
- The Flutter SDK and native build tools only when you build a packaged desktop artifact.
- [pipx](https://pipx.pypa.io/) for the released wheel on macOS and Windows.

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

A packaged desktop build bundles the client and starts with no network access. Linux builds are
supported and tested; download one from the
[releases page](https://github.com/knkillname/afanes/releases) instead of building your own. The
release guide covers the build path.

## 🖥️ macOS and Windows: wheel and browser

macOS and Windows use the released wheel and the browser presentation:

```console
pipx install "/path/to/afanes-<version>-py3-none-any.whl[web]"
afanes --web
```

Download the wheel from the [releases page](https://github.com/knkillname/afanes/releases) and pass
its path. The `[web]` extra installs the browser runtime. The server binds loopback only, serves local
assets, and allows one browser session at a time.

Native macOS and Windows binaries may also appear on the releases page. They are experimental,
untested at runtime, unsigned, and unsupported; Gatekeeper or SmartScreen may block them. The wheel is
the supported path.

## 🌐 Browser presentation from a checkout

```console
hatch run afanes --web
```

The module form, `hatch run python -m afanes --web`, works the same. Every interface asset comes from
the local environment, so a session works with no network access after the environment is created.
The desktop window stays the default; `--web` is an explicit opt-in.

## 📦 Build a desktop artifact

```console
hatch run flet build <platform> --build-version "$(hatch version)"
```

Run only the command for the host operating system: `linux`, `macos`, or `windows`. The artifact is
written under `build/<platform>/` and is an unsigned build. Install the Flutter SDK and the native
build tools first; the [release guide](../develop/releasing.md) lists the per-platform requirements
and the offline-start check.

Linux is the only release gate. The macOS and Windows builds are experiments from the nightly
workflow; a binary reaches the release page only when that platform's tests and build both pass, and
it stays untested and unsupported.

## 📡 First-run provisioning

| Presentation | Client source | Network needed at start |
| --- | --- | --- |
| Desktop (source checkout) | Flet client cached on first run under `~/.flet/client/` | Once, for provisioning |
| Desktop (packaged build) | Bundled in the artifact | No |
| Browser (source checkout) | Included in the development environment | No |
| Browser (installed wheel) | Installed with the `[web]` extra | No |

:::{warning}
Create the environment with `hatch env create` before starting Afanes from a checkout. Starting the
app that way is not a supported installation path, and a missing runtime is reported as a launch
error instead of being silently downloaded.
:::

## ✅ Check the run

```console
hatch run afanes --help
```

The command reports the launch options and the headless vault commands. With the environment ready,
`hatch run afanes` starts the interface; `hatch run afanes vault create DIR` creates a vault without
opening a window. An installed wheel exposes the same commands as `afanes` and `afanes vault create`.

Afanes supports Flet 1.0.4 and later 1.x releases. `hatch test --all` runs the suite on every
supported interpreter and against the oldest supported dependency versions.
