# 🗂️ Create or open your first vault

A vault is a folder of Markdown files with an `afanes.yaml` settings file at its root. Afanes never
hides your notes in a database: opening a vault points the application at that folder, and every note
remains readable and portable without Afanes.

:::{admonition} tl;dr
:class: note

Open an existing versioned folder or create a new vault. Creation seeds the settings file, the default
folders, and the `Getting started` guide; opening an existing vault never writes anything. A folder
from an older release can be adopted explicitly.
:::

## 🚪 Open an existing folder

On first launch, choose an existing folder or create a new vault. Use **Open Another Vault…** from
**Main Menu** to switch while Afanes is running.

A folder is a vault only when it contains a valid `afanes.yaml` settings file. Opening a versioned
folder is read-only: Afanes scans the notes it can parse and opens the **Inbox** group. It does not
seed folders, repair notes, or modify files just because the vault was opened. Folders are created
only when a write needs them.

If the folder has no settings file but contains all five default folders (`inbox/`, `trash/`,
`reference/`, `projects/`, and `log/`), Afanes offers to create `afanes.yaml`. Confirming writes only
that file; no note, folder, guide, or template card changes. A folder that cannot be adopted is
refused with a message, and nothing is written.

## ✨ Create a new vault

Choose **New Vault…** from the welcome screen, or **Main Menu → Create a New Vault…** while a vault is
open. The form asks for:

- the folder path;
- a starter-content choice;
- a preview of the notes that will be written.

On desktop, **Choose Folder…** opens a folder picker. In the browser presentation, type an absolute path
because a browser cannot return a folder path from a native dialog.

Creation writes `afanes.yaml` with the current schema, writes the `Getting started` guide, writes the
chosen template's notes, seeds the default folders, and remembers the vault for the next launch.

:::{tip}
You can create a second vault without closing the application. **Main Menu → Create a New Vault…**
keeps the current work open and adds the new vault to the remembered choice.
:::

## 🧰 Choose starter content

The built-in templates are **Personal**, **Work**, and **Study**. A blank vault is also available; it
still receives the `Getting started` guide. Template notes use dates relative to creation, so the
examples stay current.

The same choice is available headlessly:

```console
afanes vault create ~/Notes/Afanes --template work
afanes vault templates
```

`vault templates` lists the identifiers, labels, and descriptions without opening or writing a vault.
See the [vault templates reference](../reference/templates.md) for the full catalog.

## 🌱 What a new vault seeds

A new vault contains:

```text
vault/
  afanes.yaml     schema version
  inbox/          captures
  trash/          recoverable discards
  reference/      non-actionable notes
    <category>/   optional category folders
  projects/       project notes
```

It also contains `reference/Getting started.md` and the chosen template's notes. These folders are
conveniences, not requirements. Existing notes anywhere in the vault still resolve.

:::{warning}
Creation refuses a folder that is not empty and a path that names a file. It reports the problem and
writes nothing. Only **Create a New Vault…** seeds content; **Open Another Vault…** leaves an existing
empty folder unseeded.
:::

## 🧬 Adopt an older vault

A vault created before `afanes.yaml` existed can be adopted when it is writable and contains all five
default folders, matched case-insensitively. `templates/` is optional and extra folders are allowed.
The interface offers adoption in the welcome state or when changing vaults. From the command line:

```console
afanes vault adopt ~/Notes/Afanes
```

Adoption writes only `afanes.yaml`, remembers the vault unless `--no-remember` is supplied, and reports
the settings file and schema version. It never changes a note, folder, guide, or template card. A
folder that is missing a default folder or cannot be written is refused.

## 🔒 Opening and closing

Opening or scanning a vault never creates a file or folder. **Main Menu → Close Vault** saves an
open page draft, forgets the remembered vault, and returns to the welcome screen, so the next launch
starts there. A pending page dialog or a disk conflict keeps the vault open until you resolve it.

## 🧭 Next steps

- [Understand the vault format](../reference/vault-format.md)
- [Explore the bundled templates](../reference/templates.md)
