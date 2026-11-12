# 📦 Install Afanes

Afanes is a Python application with a desktop window and an optional browser presentation. Install the
package, choose the interface runtime you want, and start the app.

:::{admonition} tl;dr
:class: note

Install `afanes[desktop]` for the native window or `afanes[web]` for the browser presentation. The
first desktop run downloads the Flet client once; the application itself makes no network requests.
:::

## 💻 Desktop application

```console
pip install "afanes[desktop]"
afanes
```

The desktop extra installs the Flet desktop runtime. The first development run downloads and caches
the Flet client under `~/.flet/client/`. That download is provisioning, not application behavior: the
running app never fetches a package or calls a service.

A packaged desktop build bundles the client and starts with no network access. The release and build
pages cover that path.

## 🌐 Browser presentation

```console
pip install "afanes[web]"
afanes --web
```

The web extra ships its browser client inside the wheel, so no separate download is needed. The server
binds loopback only, and one browser session can drive the workspace at a time. The desktop window
stays the default; `--web` is an explicit opt-in.

## 🛠️ From a source checkout

Afanes runs from a checkout with Hatch:

```console
hatch env create
hatch run afanes
```

`hatch run afanes` opens the desktop window. The module form, `hatch run python -m afanes`, is
equivalent. Use `hatch run afanes --web` to start the browser presentation from the same checkout.

:::{tip}
The development environment installs both interface runtimes, so the desktop and browser forms work
from a clean checkout.
:::

## 📡 First-run provisioning

The package manager installs every runtime. Afanes never installs packages while starting.

| Presentation | Client source | Network needed at start |
| --- | --- | --- |
| Desktop (development) | Flet client cached on first run under `~/.flet/client/` | Once, for provisioning |
| Desktop (packaged build) | Bundled in the artifact | No |
| Browser | Included in the `afanes[web]` wheel | No |

:::{warning}
Install the runtime with the package manager before starting Afanes. Starting the app is not a
supported installation path, and a missing runtime is reported as a launch error instead of being
silently downloaded.
:::

## ✅ Check the installation

```console
afanes --help
```

The command reports the launch options and the headless vault commands. With a runtime installed,
`afanes` starts the interface; `afanes vault create DIR` creates a vault without opening a window.

Afanes supports Flet 1.0.4 and later 1.x releases. `hatch test --all` runs the suite on every
supported interpreter and against the oldest supported dependency versions.
