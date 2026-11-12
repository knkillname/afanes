# Design

## Context

See `proposal.md` — Why. The relevant current state:

- `Vault.create_directory(path)` is the single creation path shared by the interface and the command
  line. It validates the target, creates missing parents, then calls `_seed_layout()`, which creates
  `inbox/`, `trash/`, `reference/`, and `projects/` through `Vault.directory_for(...)`.
- Note writes already have one discipline: `Vault.contained(path)` proves containment and
  `afanes.core.atomic.write_text_atomic` performs the write. Nothing else writes vault files.
- `VaultCreation` reports the created vault, the intermediate directories made for it, and the seeded
  folders. Both adapters report those three facts.
- The interface translates `VaultError` subclasses into user-facing copy; the command line maps the
  same errors to exit code `1`. Documents that fail to parse are already a domain error, not a crash.
- `src/afanes/` is the installed package, so non-Python files inside it ship in the wheel and are
  readable through the package itself.
- The note format is strict: `type` is an enum, `category` is a single path segment, identity is the
  stem, and reference targets are stems.

## Goals / Non-Goals

**Goals:**

- One creation path that writes folders, optional starter content, and the guide, with the same
  containment and atomic-write discipline used for every other note.
- Bundled content that is itself a valid vault fragment, verified by the same parser the product
  uses, so a template cannot be "valid at authoring time, broken in a user's vault".
- A layout that accepts a second locale without moving files or changing identifiers.
- A picker, CLI option, and listing that all read one catalog, so the three adapters cannot drift.

**Non-Goals:**

- Detecting the operating-system locale, localizing the interface, or translating content.
- Applying templates to an existing vault, or exporting a vault as a template.
- Recording which notes came from a template.
- A template engine, arbitrary expressions, or any new dependency.
- Any change to frontmatter keys, the reference syntax, or the index schema.

## Decisions

### Bundled content lives in the package as a real, partial vault

`src/afanes/templates/<template-id>/<locale>/...` mirrors the paths written into the vault: a file at
`personal/en/projects/Home projects.md` becomes `projects/Home projects.md`. Reading uses
`importlib.resources.files("afanes") / "templates"`, so the same code works from a source checkout
and from an unpacked wheel, with no source-path assumption and no new dependency.

*Alternatives:* template bodies as Python string constants (unreadable, unlintable, and the format
would stop being dogfooded); a single packed data file (opaque, untranslatable, and needs its own
reader).

### The guide is a fixture, not a template

`templates/_guide/<locale>/reference/Getting started.md` is resolved and written by every creation,
outside the catalog. The leading underscore keeps it out of the identifier space and signals that it
is not selectable. Blank therefore still means "no starter content", and the picker stays honest.

*Alternative:* making blank a catalog entry containing the guide — fewer code paths but forces
renaming the option and privileges starter content over no starter content.

### Locale is a path segment with a base fallback, and nothing else yet

Resolution tries `<template-id>/<locale>/` then `<template-id>/en/`. Creation passes the base locale
because the interface has no localization; the parameter exists so a later localization change adds
content, not structure.

*Alternatives:* detecting the system locale now (would produce Spanish notes inside an English
interface, and cross-platform locale reporting is inconsistent); locale-neutral message keys with
translation at creation (a translation catalog and workflow before any template exists).

### The catalog is core data, not interface copy

`core/templates.py` owns a frozen `VaultTemplate` value object (identifier, label, description) and a
`TemplateCatalog` that resolves and validates bundled trees. The interface and the command line both
render that metadata; neither owns it. This is the same reasoning that keeps name and path policy in
`core/names.py`: one rule, two adapters.

*Alternative:* labels in `ui/strings.py` and again in `cli/strings.py` — the interface cannot import
the command line, so the copy would be duplicated and drift.

### Dates come from a two-token placeholder syntax, not a template engine

Bundled notes write `{{ date:+14d }}` or `{{ date:-2d }}` where a calendar date belongs. Creation
renders every match with `datetime.timedelta` before the note is parsed, so the written file contains
a concrete ISO date and nothing else. Any brace expression left after rendering is a content error,
which catches a typo before it reaches a user's vault. The syntax is deliberately limited to a sign
and a day count; it is not an expression language.

*Alternatives:* Jinja2 (a new runtime dependency, a license and packaging review, and a full
expression language for what is date arithmetic); static dates written into the bundle (they age
badly and look stale a year later); a sidecar manifest with offsets (keeps placeholders out of the
note, but splits one note's metadata across two files and adds a second format to validate).

### Dates are validated against the creation date

`TemplateCatalog.today()` is the single time source. It returns the local calendar date and is the
only place tests patch to make creation deterministic. Rendering and validation receive the same
date. A project due date or an unchecked step plan date on or before that date is refused, and an
actual date is accepted only on a checked step and only when it is not after that date. The review
count therefore stays zero when the vault is created, while the starter content still shows real
dates.

*Alternative:* validating only in the test suite (a broken bundled tree would reach a user's vault
before the suite noticed); injecting a clock object (the project passes plain dates instead).

### Validation runs before anything is written

Creation order becomes: validate the target path → resolve, render, and validate the bundled tree
(template plus guide) → create missing parents → seed folders → write notes → report. Validation
covers parsing, unique stems across template and guide, the filename policy, reference resolution
inside the tree, folder/type/category agreement, absence of `inbox/` and `trash/` notes, unresolved
date placeholders, the future/past date rules, and identical shape across locale trees. Because it
runs before the first `mkdir`, a refused template leaves the filesystem exactly as it was.

### Notes are written through the vault, one atomic write each

Each bundled note is validated with `contained()` and written with `write_text_atomic` after its
parent folder is created. No `copytree`, no direct `open(..., "w")`, no bulk archive extraction.

*Alternative:* `shutil.copytree` — faster to write, but it bypasses containment, ignores the filename
policy, and gives no per-note failure point.

### Partial failure raises, mirroring the existing seeding precedent

If a note write fails, creation stops and raises a template error naming the failing note and the
notes already written. Written notes stay, the folder remains openable as an ordinary vault, and the
vault is not remembered. This is exactly how a failed `_seed_layout` is already reported, so both
adapters keep one failure convention instead of gaining a second.

*Alternative:* returning a partial `VaultCreation` and opening the vault anyway — friendlier, but it
would mean creation can "succeed" while having silently written an incomplete vault, and it needs a
second failure shape in both adapters.

### `VaultCreation` reports notes and the template used

`VaultCreation` gains `written_notes: tuple[Path, ...]` and `template: str | None`, in creation
order. Both adapters print them; the CLI adds `--template ID` and a `vault templates` action that
renders the same catalog. `template` defaults to `None`, so existing callers and tests keep their
behavior for folders while gaining the guide note.

### The picker prefills nothing and reads the catalog off the UI thread

The new-vault dialog gains a selector listing the catalog with labels and descriptions, with the
no-template option selected. Note counts for the preview come from a single catalog summary read
through `asyncio.to_thread` when the dialog opens; if the bundle cannot be read, the dialog reports
it and offers the no-template creation rather than failing to open.

## Risks / Trade-offs

- **Bundle content rots as the format evolves** → one parametrized suite over every `(template,
  locale)` tree runs in the normal test gate, so a format change breaks the build instead of a user's
  first launch.
- **Wheel omits non-Python data** → the catalog is read through `importlib.resources` in a test, and
  packaging is verified once against a built wheel; a missing tree fails the test rather than
  producing an empty vault.
- **Starter content mistaken for real obligations** → the inert-content rules (no dates in the
  past, no owners, no captures, every open project has a step) are enforced by tests and by creation
  validation, keeping the review count at zero.
- **Starter dates age** → every date is relative to creation, and validation refuses a plan or due
  date on or before the creation date, so content written today stays coherent whenever it is
  created.
- **A placeholder typo reaches a vault** → rendering runs before parsing, and any brace expression
  left afterwards refuses the tree before the first directory is created.
- **Midnight boundary** → offsets are at least one day, and the zero-pending guarantee is asserted
  at creation, not on later calendar days.
- **Translation drift across locales** → the shape rule requires each locale tree to match the base
  tree's projects, references, and step counts, so a half-finished translation is refused.
- **Every creation now writes a file, changing an existing guarantee** → the `vault-layout` delta
  states it explicitly, and creation tests that asserted "no files" are updated to assert "the guide
  and nothing else".
- **Picker I/O on the UI thread** → the catalog summary is awaited through `asyncio.to_thread`, and a
  read failure degrades to no-template creation rather than a blocked dialog.

## Migration Plan

No user data migrates and no cache schema changes. Existing vaults are never opened, scanned, or
rewritten by this change; the behavior change applies only to new vault creations. Rollback means
removing the template trees, the guide write, and the new CLI surface, and restoring the
`vault-layout` requirement — no vault already created is affected either way, because created notes
are ordinary notes.

## Open Questions

None. The decisions that remain — exact prose of the guide and the three templates — are content
authoring inside the validity rules, not design choices, and are captured as tasks.
