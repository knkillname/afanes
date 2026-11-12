# 🗂️ Create or open your first vault

A vault is a folder of Markdown files. Afanes never hides your notes in a database: opening a vault
points the application at that folder, and every note remains readable and portable without Afanes.

:::{admonition} tl;dr
:class: note

Open an existing folder or create a new vault. Creation seeds the default folders and the `Getting
started` guide; opening an existing folder never writes anything.
:::

## 🚪 Open an existing folder

On first launch, choose an existing folder or create a new vault. Use **Open another vault** from
**Change vault** to switch while Afanes is running.

Opening an existing folder is read-only. Afanes scans the folder, groups the notes it can parse, and
opens the **Inbox** group. It does not seed folders, repair notes, or modify files just because the
vault was opened. Folders are created only when a write needs them.

## ✨ Create a new vault

Choose **New vault** from the welcome screen, or **Change vault → Create a new vault** while a vault is
open. The form asks for:

- the folder path;
- a starter-content choice;
- a preview of the notes that will be written.

On desktop, **Choose folder** opens a folder picker. In the browser presentation, type an absolute path
because a browser cannot return a folder path from a native dialog.

Creation writes the `Getting started` guide, writes the chosen template's notes, seeds the default
folders, and remembers the vault for the next launch.

:::{tip}
You can create a second vault without closing the application. **Change vault → Create a new vault**
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
writes nothing. Only **Create a new vault** seeds content; **Open another vault** leaves an existing
empty folder unseeded.
:::

## 🔒 Opening and closing

Opening or scanning a vault never creates a file or folder. **Change vault → Close vault** saves an
open page draft, forgets the remembered vault, and returns to the welcome screen, so the next launch
starts there. A pending page dialog or a disk conflict keeps the vault open until you resolve it.

## 🧭 Next steps

- [Understand the vault format](../reference/vault-format.md)
- [Explore the bundled templates](../reference/templates.md)
