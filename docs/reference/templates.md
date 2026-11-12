# 🧰 Vault templates

A new vault can start with one of three bundled templates: **Personal**, **Work**, or **Study**. Every
new vault also receives the `Getting started` guide, including a blank vault created without a
template.

:::{admonition} tl;dr
:class: note

Templates are starter content, not a schema. They write notes into a new vault, use dates relative to
creation, and never touch a vault that already exists.
:::

## 📚 Catalog

| Identifier | Label | Description |
| --- | --- | --- |
| `personal` | Personal | Life administration for the home, the car, and the paperwork that arrives each year. |
| `work` | Work | Shared outcomes, the groups that own them, and the processes that carry them. |
| `study` | Study | Course and research work, with the topics and sources kept beside it. |

## 🌱 What every template includes

A new vault is seeded with `inbox/`, `trash/`, `reference/`, and `projects/`. The `Getting started`
guide is written to `reference/Getting started.md`. A chosen template adds its own reference and
project notes on top of that guide.

The guide is an ordinary reference note. Rename it, edit it, or move it to `trash/` when you no longer
need it.

## 🧭 Creating from a template

From the application, choose **New vault** and pick a starter-content option. The form shows a preview
before anything is written.

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
