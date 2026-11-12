# README reconciliation

`README.md` is now a landing page. This note records where each old section went and what was checked
before the change was reported ready.

| Old README section | New home | Status |
| --- | --- | --- |
| Table of Contents | Removed; the docs index toctrees and README links replace it | No content lost |
| Development | `docs/develop/setup.md`; README keeps the install commands | Moved |
| Build a desktop app | `docs/develop/releasing.md` | Moved |
| Check the offline start | `docs/develop/releasing.md` | Moved |
| Command line | `docs/guide/command-line.md` | Moved |
| Running in a browser | `docs/guide/browser-mode.md` | Moved |
| Vault format | `docs/reference/vault-format.md`, `frontmatter.md`, `step-metadata.md` | Moved and split |
| Step metadata | `docs/reference/step-metadata.md`; example in `docs/guide/projects-and-steps.md` | Moved |
| Schemes and categories | `docs/reference/names-and-links.md`; `docs/guide/references-and-categories.md` | Moved |
| Upgrading from the four-type model | `docs/reference/migration.md` | Moved |
| Workspace browser | `docs/guide/workspace.md` | Moved |
| Inbox | `docs/guide/inbox.md` | Moved |
| Projects | `docs/guide/projects-and-steps.md` | Moved |
| Pages and editing | `docs/guide/pages-and-editing.md` | Moved |
| Processing | `docs/guide/processing.md` | Moved |
| Review | `docs/guide/review.md` | Moved |
| Changelog | README links to `CHANGELOG.md` | Linked |
| License | README keeps the AGPL-3.0-or-later statement | Retained |

## What was checked

- Every old section has a destination above; no behavior, build, or CLI prose was dropped.
- The install section still covers desktop, web, source checkout, the one-time Flet client
  provisioning, and the Flet version support statement.
- The CLI page still covers `vault create`, `vault templates`, template selection, `--no-remember`,
  refusal cases, exit codes, and output streams.
- The browser page still covers loopback binding, one session at a time, `--vault`, `--port`, the
  absolute-path prompt, the lost-session message, and the no-silent-switch rule.
- The vault pages still cover the three note types, recognized frontmatter keys, unknown-key
  preservation, default layout, category folders, trash exclusion, identity, schemes, matching,
  retired values, and step metadata.
- The guide pages still cover the browser groups, search, capture field, Inbox ordering, project
  groups and next-step rules, page reading, labels, conflicts, raw rescue, rename and trash, every
  processing outcome, and every review card action.
- `TestDocumentedExamples` now reads the project example from `docs/reference/vault-format.md`, the
  capture example from `docs/getting-started/capture-clarify-review.md`, and the step-metadata example
  from `docs/guide/projects-and-steps.md`.
- The README has one screenshot hosted from the repository's raw GitHub URL; its documentation links
  use absolute GitHub URLs so the PyPI long description keeps working before a published site exists.
- `docs/develop/documentation.md` records the per-change documentation review rule, and `AGENTS.md`
  and `openspec/config.yaml` are updated in the policy tasks.
