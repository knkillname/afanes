# 🌐 Browser mode

Machines that block the native Flet client can serve the same interface to a browser. The desktop
window stays the default; `--web` is the explicit opt-in, and Afanes never switches presentation on its
own.

:::{admonition} tl;dr
:class: note

Run `afanes --web` after installing `afanes[web]`. The server binds loopback only, serves local assets,
and allows one browser session at a time.
:::

## 🚀 Start the server

```console
pip install "afanes[web]"
afanes --web
```

The module form, `python -m afanes --web`, works the same. Every interface asset comes from the local
installation, so a session works with no network access after installation.

## ⚙️ Options

- `--vault DIR` opens that folder for this run without replacing the remembered vault.
- `--port N` chooses the listening port. The default asks the operating system for a free one.

A browser cannot return a folder path from a file dialog, so a browser session asks for an absolute
path instead of opening a picker. The **Change vault** action asks the same way.

## 👥 One session at a time

One browser session can drive the workspace at a time. A second tab shows a notice until the first one
closes. Closing a tab releases its session, so Afanes can be reopened in a new one.

If the desktop client cannot start, Afanes reports the failure and exits rather than switching
presentations silently.

:::{warning}
A tab that shows a spinner with "Working…" has lost its Python session, usually because the server
process exited. Start the server again and reload the tab. The page cannot recover the session by
itself.
:::

## 🗂️ First launch in a browser

On first launch, choose an existing folder or create a new vault. **New vault** opens a form with the
folder path, the starter-content choice, and a preview. It writes `reference/Getting started.md` plus
the notes of the chosen template, seeds `inbox/`, `trash/`, `reference/`, and `projects/`, and remembers
the result in the platform configuration directory. Afanes reopens that vault next time.

The same choice is available from **Change vault → Create a new vault** while a vault is open. Only the
create action seeds the default folders and writes starter content. Opening an existing empty folder
leaves it unseeded, and Afanes creates each folder only when a write needs it. Opening or scanning a
vault never creates a folder or a file.

**Change vault → Close vault** saves an open page draft, forgets the remembered vault, and returns to
the welcome screen. A pending page dialog or disk conflict keeps the vault open and explains what to
resolve.

## 🧭 See also

- [Install Afanes](../getting-started/install.md)
- [Create or open your first vault](../getting-started/first-vault.md)
- [Command line](command-line.md)
