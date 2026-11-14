# 🧰 Vault templates

A new vault can start with one of three bundled templates: **Personal**, **Work**, or **Study**. Every
new vault also receives the getting-started guide, including a blank vault created without a
template. The guide, template notes, cards, labels, and descriptions follow the active language; a
Spanish vault receives Spanish content and an English vault receives English content.

:::{admonition} tl;dr
:class: note

Templates are starter content, not a schema. They write notes into a new vault, use dates relative to
creation, and never touch a vault that already exists.
:::

## 📚 Catalog

| Identifier | English label | Spanish label |
| --- | --- | --- |
| `personal` | Personal | Personal |
| `work` | Work | Trabajo |
| `study` | Study | Estudio |

Identifiers never change with the language; interface copy and `afanes vault templates` show the
localized label and description instead.

## 🌱 What every template includes

A new vault is seeded with `inbox/`, `trash/`, `reference/`, and `projects/`, plus eight editable
template cards under `templates/`. The guide is written to `reference/Getting started.md` in English
and `reference/Primeros pasos.md` in Spanish. A chosen template adds its own reference and project
notes, with localized filenames and text, on top of that guide.

The `templates/` folder is reserved for template cards, not notes. Its files are excluded from scans,
the browser, name uniqueness, and reference resolution. An existing vault that used `templates/` for
ordinary notes will stop showing those notes until they are moved elsewhere. See
[Template cards](template-cards.md) for the card format and the seeded cards.

The guide is an ordinary reference note. Rename it, edit it, or move it to `trash/` when you no longer
need it. The template cards are ordinary files too: edit them, add your own, or delete the ones you do
not use. Opening a vault never restores a deleted card.

## 🧭 Creating from a template

From the application, choose **New Vault…** and pick a starter-content option. The form shows a preview
before anything is written. The active language selects the content. A template without a Spanish tree
falls back to its English tree, so creation still succeeds.

From the command line:

```console
afanes vault create ~/Notes/Work --template work
afanes vault templates
```

`afanes vault templates` reports every identifier, label, and description without opening or writing a
vault. `vault create` refuses a non-empty folder, a path that names a file, and an unknown template.

## ⏱️ Relative dates

Template notes may contain `{{date:+Nd}}` or `{{date:-Nd}}` placeholders. They resolve against the
creation date, so examples stay current. An unknown brace expression is a typo and refuses the
creation instead of writing an unresolved placeholder.

## 🧭 See also

- [Create or open your first vault](../getting-started/first-vault.md)
- [Vault format](vault-format.md)
