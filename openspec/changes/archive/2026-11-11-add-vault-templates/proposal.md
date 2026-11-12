# Proposal

## Why

Creating a vault currently seeds four empty folders and nothing else, so a new user's first screen
after creation is three sections reading "No notes in this section." The interface explains the
model once, on the welcome screen, and then stops explaining it the moment the vault exists. A user
who has never seen an Afanes vault has to invent projects, references, steps, and category folders
from nothing, which is the hardest possible first five minutes.

The note format is the whole product, and it is invisible in an empty vault. Bundled starter content
is the cheapest way to show the format on page one, without adding a tutorial mode, a wizard, or any
network access.

## What Changes

- Add a **template catalog** of bundled Markdown trees shipped inside the package. Each template is
  a partial vault — folders and notes only — copied into a newly created vault.
- Ship three substantial templates, each with 8-12 notes. **Personal** covers life administration
  with `person` and `place` labels: insurance, car service, taxes, a hallway repaint, a monthly
  budget, the weekly shop, and household chores. **Work** covers shared outcomes with `team` and
  `process` labels: quarterly planning, hiring, incident follow-up, and a runbook. **Study** covers
  course and research work with `topic` and `source` labels: reading, a research essay, exam prep,
  and a seminar talk. Each differs by reference labels, project count, and step granularity, so no
  two are interchangeable.
- Store each template as `templates/<template-id>/<locale>/` and resolve a locale with a fallback to
  the base language. Ship `en/` only; adding a translation is content work, not a redesign.
- Add a **guide note** written into every created vault, from `templates/_guide/<locale>/`, so the
  model is explained even when no template is chosen. The guide is a fixture outside the template
  choice, so "Blank" keeps meaning "no starter content".
- Add a **template choice** to vault creation in both presentations, with **Blank preselected**
  always. The creation dialog keeps its preview line and extends it to name what will be written.
- Add `--template ID` to `afanes vault create` and a `afanes vault templates` command that lists the
  catalog, so a templated vault is reproducible without a dialog.
- Make dates relative to creation. Bundled notes MAY write `{{ date:+14d }}` or `{{ date:-2d }}`
  where a calendar date belongs; creation renders each placeholder into a concrete ISO date, so the
  content never goes stale. Due and plan dates are always after the creation date, actual dates
  appear only on completed steps, and no step owners or inbox captures are seeded. Every open
  project carries at least one unchecked step, so a freshly created vault still reports zero
  pending review work.
- Resolve dates with the standard library. The placeholder syntax is deliberately two tokens, not a
  template engine, so this change adds no runtime dependency and no expression language.
- Keep starter notes ordinary notes. No provenance is recorded, no marker key is added, and no
  special removal action exists: the notes are renamed, edited, and trashed with the actions that
  already exist.

Non-goals: applying a template to an existing vault, "use this folder as a template", "save this
vault as a template", user-authored template storage, translated template content beyond the layout
that accepts it, localization of the interface, a template engine or new dependency, arbitrary
expressions in bundled content, README or screenshot updates, and any change to the note format
itself.

## Capabilities

### New Capabilities

- `vault-templates`: the bundled template catalog, the locale-scoped folder layout and its fallback,
  the guide note fixture, how a template is applied at creation time, and the validity rules every
  bundled tree must satisfy.

### Modified Capabilities

- `vault-selection`: creation gains a template choice with Blank preselected, in both presentations,
  and the creation preview names the notes that will be written in addition to the folders.
- `vault-layout`: a created vault is no longer described as folder-only; it always contains the guide
  note, and a templated creation writes exactly the notes its template declares and nothing else.
- `command-line`: `afanes vault create` accepts a template, rejects an unknown identifier by naming
  the valid ones, and a new listing action reports the catalog.

## Impact

- **Core**: a new bundled-content module owning the catalog, locale resolution, template validation,
  and the creation-time copy; `Vault.create_directory` grows an explicit template parameter that
  defaults to blank, and `VaultCreation` reports the notes it wrote alongside the folders it seeded.
- **Packaging**: template trees are non-Python package data under `src/afanes/`; the wheel must carry
  them and the installed application must read them through the package, not through a source path.
- **Command line**: a new create option and a new listing action, with the existing exit codes and
  stream conventions; unknown identifiers are expected failures, not usage errors.
- **Interface**: a template selector in the new-vault dialog of the welcome state and of the
  change-vault action, a preview line that names both folders and notes, and new centralized copy.
- **Tests**: one parametrized validity suite over `(template, locale)` pairs, rendering cases for
  both date offsets and malformed placeholders, future/past date rules, creation cases for blank and
  templated vaults, locale fallback, partial-write reporting, command exit codes, and the
  package-data check.
- **Compatibility**: no note-format change, no new dependency, no network access, and existing
  vaults are never touched. Vault creation without a template keeps its current meaning apart from
  the guide note.
- **Documentation**: a changelog entry. README and screenshots are deliberately out of scope.
