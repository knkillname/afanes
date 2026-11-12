# 🧭 Migrating from the four-type model

This release uses three note types: `note`, `reference`, and `project`. The older four-type model and
the `person:` link scheme are no longer valid. There is no automatic migration; affected notes open in
raw rescue mode and are never rewritten silently.

:::{admonition} tl;dr
:class: note

A single actionable unit is now a step inside a project. A person page is a reference with
`category: person`, reached through `note:`. Repair affected notes by hand in raw rescue mode.
:::

## 🚫 What is refused

- Notes declaring `type: action`.
- Links using `person:Name`.
- Notes carrying the retired `people` or `project` frontmatter keys.

These are validation errors. They appear under **Unreadable notes** and open in raw rescue mode without
being rewritten. A `category: person` reference remains valid and keeps working.

## 🛠️ How to repair

1. Create a one-step project for an action, or move its work into an existing project body as a step.
2. Rewrite `person:Name` links as `note:Name`.
3. Remove the retired `people` and `project` frontmatter keys.
4. Save in raw rescue mode; once the text parses, the normal editor returns.

A person is now an ordinary reference with `category: person`. The category groups it under the
`person` label in the browser and files it under `reference/person/`, but it does not create a
separate namespace.

## 🧭 See also

- [Frontmatter](frontmatter.md)
- [Names and links](names-and-links.md)
- [Vault format](vault-format.md)
