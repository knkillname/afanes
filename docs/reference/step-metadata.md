# 🧩 Step metadata

A step is a Markdown task-list item in a project body. It may end with one metadata comment made of a
flow-style YAML object. The comment carries the step's owners, planned date, completion date, and tags.

:::{admonition} tl;dr
:class: note

The metadata comment is optional, must be the last content on the line, and must end with `-->`.
Unknown keys survive a rewrite; a malformed value drops only that key and reports the line.
:::

## 📝 The comment

```markdown
- [ ] Call the plumber <!-- {owners: [Ada], plan: 2026-11-20, actual: 2026-11-14, tags: [phone]} -->
```

The comment must be the last content on the line and the line must end with `-->`. Text after the
comment makes it prose. Every key is optional, and a comment without a mapping is prose.

## 🔑 Keys

| Key | Meaning |
| --- | --- |
| `owners` | People the step waits on. No owner means the step is yours. |
| `plan` | Day the step was supposed to happen, as `YYYY-MM-DD` |
| `actual` | Day it was completed, as `YYYY-MM-DD`; written by ticking |
| `tags` | Free-form labels used only to filter steps |

Step owners resolve through the same catalog as `note:` references. Owners are step-level; a project
does not gain an owners field.

## ✅ Ticking a step

Ticking a step writes `[x]` and adds `actual: <today>`. Unticking removes `actual` and keeps `plan`.
The calendar action sets or clears `plan`; the person action manages the full owner list.

Ticking, unticking, planning, or reassigning a step rewrites only that line atomically and leaves every
other byte of the file unchanged.

## 🧪 Parsing rules and warnings

- A malformed comment or an invalid value drops only that key, keeps the note readable, and reports the
  line.
- Unknown keys are preserved when the step is rewritten.
- A value containing `--` cannot appear inside an HTML comment, so the app reports it instead of
  writing invalid metadata.
- A checkbox inside a fenced or indented code block is not a step.

## 🧭 See also

- [Projects and steps](../guide/projects-and-steps.md)
- [Vault format](vault-format.md)
- [Frontmatter](frontmatter.md)
