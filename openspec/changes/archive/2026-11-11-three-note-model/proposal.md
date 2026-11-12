# Proposal

## Why

Afanes currently gives a single action its own note type. That one decision brings a fourth type, a
`project:` back-reference on every action, a `people` list, a person-only link scheme, and per-action
scheduling. It is also the part of the model that makes the vault behave like a task database, which
the product explicitly is not.

The workflow still needs a next step, a waiting state, deadlines, and a record of what was done. All
of those can live on a project page whose body is a checklist. Reducing the model to three note types
— unclarified note, reference, project — keeps the vault a document, removes an entire reference
namespace, and makes the step the unit of execution without making it a file.

## What Changes

- **BREAKING** Reduce note types to `note`, `reference`, and `project`. Remove `action`; a single
  action becomes a one-step project.
- **BREAKING** Remove the `person` link scheme. References resolve through `note:`; projects through
  `project:`. A person is a reference with a free-form category, not a namespace.
- **BREAKING** Make `category` a free-form label on references. Remove the fixed category list and
  the `people` and `project` frontmatter keys.
- **BREAKING** Move steps into project bodies as Markdown checkbox list items. Step metadata lives in
  a trailing single-line HTML comment holding a flow-style YAML object with `owners`, `plan`,
  `actual`, and `tags`.
- Add step semantics: an owner means the step is waiting on someone; no owner means it is yours.
  `plan` is the day it was supposed to happen, `actual` the day it did. Ticking sets `actual`;
  unticking removes it. Tags filter steps.
- Change clarification outcomes to trash, reference (or later), a new project, appending a step to an
  existing project, or doing it immediately (a one-step project, ticked and closed).
- Change the Projects workspace to present projects with their open steps. The next step is the first
  unticked step in document order.
- Change the guided review to visit due steps and waiting steps, with cards for do it now, postpone,
  delegate, open project, and skip, plus a launch digest of due work.
- Make browser search full text across prose and steps.
- File categorized references under `reference/<category>/`. Remove `actions/` and the seeded
  `reference/people/`.
- **BREAKING** Treat old `action` notes, `person:` links, and `people`/`project` keys as unreadable.
  There is no automatic migration; affected notes are repaired by hand in raw rescue mode.
- Release as 4.0.0.

## Capabilities

### New Capabilities

- `note-model`: the three note types, the frontmatter contract they share, the status vocabulary, and
  the retired keys that are now rejected.
- `project-steps`: the checkbox syntax, the trailing metadata object, completion and plan dates,
  owner-based waiting, tags, and the rules for rewriting a step without losing data.

### Modified Capabilities

- `inbox-capture`: `type: note` means "not clarified yet" and nothing else.
- `note-identity`: three note types, two reference schemes, and steps that have no identity.
- `note-references`: the scheme set shrinks, frontmatter references disappear, and step owners resolve
  through the same catalog.
- `reference-categories`: categories become free-form labels that select a folder, not a scheme.
- `processing`: the outcome set changes, clarification can append a step to another note, and a
  capture can become a closed one-step project.
- `project-overview`: projects present steps instead of actions; next step and open counts come from
  the body.
- `guided-review`: due and waiting steps join the queue, step cards replace action cards, and the
  launch digest opens the session.
- `vault-browsing`: the browser sections change and search becomes full text.
- `note-editing`: page drafts lose the person scheme, the editor gains step rendering, and a category
  change moves the file.
- `vault-layout`: `actions/` leaves the layout, categorized references use `reference/<category>/`, and
  vault creation seeds the smaller set. The command-line contract already reports whichever folders are
  seeded, so it needs no requirement change.

## Impact

- **Data format**: breaking. `type: action`, `person:` destinations, and the `people`/`project` keys
  become validation errors. Existing vaults need hand repair.
- **Code**: `models/note.py`, `models/link.py`, `core/frontmatter.py`, `core/links.py`,
  `core/processing.py`, `core/vault.py`, `core/search.py`, `core/editing.py`, `ui/state.py`,
  `ui/views/*`, `ui/strings.py`, `cli/vault.py`, `cli/strings.py`.
- **Documentation**: `README.md`, `CHANGELOG.md`, and `AGENTS.md` sections 1.3, 1.4, 1.5, and 4.7.
- **Dependencies**: none. YAML parsing and Markdown parsing use existing dependencies.
- **Platforms**: the category folder uses the existing cross-platform filename policy; no new
  platform-specific behavior.
- **Deferred**: review-scope settings, reference templates, the SQLite/FTS index, project-level tags,
  and any migration helper.
