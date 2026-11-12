# Design

## Context

See `proposal.md` for motivation. The current implementation assumes four note types and two levels of
work:

- `models/note.py` defines `NoteType` with `action` and `ReferenceCategory` with `person`.
- `models/link.py` defines three schemes and maps a reference's category to the `person` scheme.
- `core/frontmatter.py` parses `people` and `project` into references and validates a closed category.
- `core/processing.py` models five outcomes, one of which writes an action note.
- `core/search.py` derives the browser, project board, and review queue from a `VaultSnapshot`, and
  search reads only titles and identities.
- `core/vault.py` owns planning, atomic apply, action creation, and destination folders.

The vault is still the source of truth, the cache is disposable, and the scan is read-only. No SQLite
index exists yet; every view is computed from an in-memory snapshot.

## Goals / Non-Goals

**Goals:**

- One model of work: a project page whose body is a checklist.
- One reference namespace for everything that is not a project.
- Step metadata that survives hand editing and preserves unknown data.
- Views computed from the same snapshot, with no stored denormalized state.
- A hard, explicit break that never rewrites user text silently.

**Non-Goals:**

- A migration command, a compatibility layer, or automatic conversion.
- Per-step identity, links, backlinks, or per-step files.
- Project-level tags, templates, review-scope settings, or the SQLite index.
- Recurring steps, reminders outside the app, or OS notifications.

## Decisions

### 1. Steps are derived from the body, not stored separately

A new value object `ProjectStep` holds the text, checked state, owners, plan, actual, tags, the body
line index, and the parsed metadata mapping. `VaultNote` gains `steps: tuple[ProjectStep, ...]`,
computed during the existing scan for `type: project` only.

Alternatives: a `steps` frontmatter list (structured but turns the page into a database row and
breaks the document feel), or one file per step (the model being removed). Body derivation is the
only option that keeps the vault a document and still yields a queryable list.

### 2. Parse lines through markdown-it tokens, rewrite one line

`core/steps.py` adds a `StepDocument` class that owns a project body. It parses with the existing
`MarkdownIt("commonmark")` instance, walks `list_item_open` tokens, and uses each token's `map` to read
the item's first line. A task item is one whose inline content begins with `[ ]` or `[x]`. The trailing
`html_inline` child is the metadata comment.

Rewriting returns a new body with only the target line replaced, preserving newline style and every
other byte. The vault then writes the whole file atomically with the existing optimistic hash check.

Alternatives: a hand-rolled line scanner (forbidden by the project's Markdown rule), a regex over the
body (fragile with code blocks and fenced examples), or direct partial file writes (breaks atomicity).

### 3. Metadata is a flow-style YAML mapping in a trailing HTML comment

`<!-- {owners: [Ada Lovelace], plan: 2026-11-20, actual: 2026-11-14, tags: [admin]} -->`

- The comment must be the last content on the item's first line; anything after `-->` makes it prose.
- Only the last comment on the line is considered.
- Parsing uses `yaml.safe_load`; serialization uses `safe_dump(default_flow_style=True,
  allow_unicode=True, sort_keys=False)` and strips the trailing newline.
- `plan` and `actual` are read as `datetime.date` or ISO strings and normalized to `datetime.date`.
- Unknown keys are kept in the parsed mapping and re-emitted on every rewrite.
- A malformed mapping or a bad value drops only the invalid key, keeps the note readable, and records
  a warning tied to the file and line.

Alternatives: sigils (`@`, `#`, bare dates) were rejected because they collide with prose and need a
right-to-left scan; a visible `{...}` block was rejected as noisier in source; real frontmatter per
step is impossible without making steps files.

### 4. The model types shrink at the boundary

- `NoteType`: `note`, `reference`, `project`.
- `ReferenceScheme`: `project`, `note`; `for_note` no longer takes a category.
- `CategoryLabel`: a frozen value object validating a non-empty single segment, preserving case,
  comparing case-insensitively. It replaces `ReferenceCategory`.
- `NoteDocument`: drops `people` and `project`; `category` becomes `CategoryLabel | None`.
- `VaultNote`: drops `frontmatter_references`; adds `steps` and `search_text`.
- `ProcessingOutcome`: `trash`, `later`, `reference`, `project`, `append_step`, `done_now`.
- `ProcessingPlan` keeps the single-note outcomes; a new `AppendStepPlan` holds the capture, the
  target project, the step text, the indented detail, and both hashes.

Alternatives: keep `action` as a deprecated readable type (two models, rejected), or keep `person` as
an alias for `note` (silent namespace, rejected by the hard break).

### 5. Append is ordered, not atomic across files

A cross-file transaction is not available. `Append step` writes the target project first, then trashes
the capture. If the project write fails, the capture is untouched. If the trash fails after the project
write, the capture stays in the inbox with a clear warning and the step is already present; re-running
the plan must detect the existing step and refuse to duplicate it.

Alternatives: write the capture first (loses the step on failure), or copy the capture into trash
first (a stale trash entry). Ordered writes with a retryable failure are the only safe option on a
plain filesystem.

### 6. Waiting and due lists come from the same steps

- Own step: `owners` is empty or absent.
- Waiting step: `owners` is non-empty; owners resolve through `NameCatalog` and may be unresolved.
- Due step: own, unchecked, and `plan <= today`.
- Next step: the first unchecked step in document order, regardless of owner; the row marks it waiting
  when owned.
- Tags filter the step list; no stored tag index.

### 7. Search reads the snapshot's search text

`VaultNote.search_text` is the body with metadata comments removed. `Browser.filter` matches display
title, identity, or `search_text`, using the existing normalized substring comparison. Step text is
part of the body, so it matches; metadata comments are removed, so owner names and dates are not
searched as text.

Alternatives: index bodies in SQLite now (premature; the index is a separate capability), or read
files during search (blocks the UI and violates the snapshot model).

### 8. Category folders are destinations, not identity

`Vault` derives `reference/<label>/` from `CategoryLabel` through `afanes.core.names.safe_filename`.
Folder matching is case-insensitive and reuses an existing variant. A category change plans a move;
the editor previews the destination, writes the new frontmatter atomically, then moves the file. If
the move fails, the note keeps the new category in the old folder; the view groups by label, so the
drift is invisible and retryable.

### 9. The hard break is enforced by the parser

`type: action`, `person:` destinations, and the `people`/`project` keys become validation errors. The
note lands in the existing failures section and opens in raw rescue mode. Nothing is rewritten. The
release is 4.0.0, and the README documents the new format so a vault is readable without the app.

One edge case follows from `type: note` meaning "unclarified": a `type: note` outside `inbox/` is
reported as misplaced and is not processed. The Inbox stays folder-based, so an external move does not
silently requeue a file; the recorded assumption is that a misplaced note is repaired by moving it back
or clarifying it by hand.

## Risks / Trade-offs

- **Hidden metadata in other viewers** → accepted; the README documents the schema and the app renders
  it as labels. A file browser still shows the raw comment.
- **`--` is illegal inside an HTML comment** → validate on write; an owner or tag containing `--`
  produces an actionable warning rather than an invalid comment.
- **Full-text scan memory** → bodies are already read for links; storing text costs memory proportional
  to the vault. The index is the deferred answer for large vaults.
- **Hard break leaves old vaults unreadable** → deliberate; failures are listed and repairable in raw
  rescue mode, and the release notes state the break.
- **Step rewrite races with an external edit** → the existing content-hash guard aborts the write and
  offers reload or overwrite.
- **Category folder drift** → grouping uses the label, not the folder; a later move can repair the path.
- **YAML flow style quirks** → dates and names are normalized before writing; a property test covers
  parse/serialize round-trips.
- **One large change** → the specs and design are the contract; tasks are ordered so the model lands
  before the views that depend on it.

## Migration Plan

1. Land the model and parser behind the new tests; old notes become unreadable by design.
2. Land scanning, the project board, and the browser against the new model.
3. Land the editor, step rendering, category moves, and processing outcomes.
4. Land review, the digest, and full-text search.
5. Update `README.md`, `CHANGELOG.md` (4.0.0), and the `AGENTS.md` vocabulary and frontmatter contract.
6. Publish no converter. The rollback is the previous release; the vault is unchanged by the upgrade
   until the user edits a note.

## Open Questions

None that change the specs or the task breakdown. Review-scope settings, reference templates, and the
SQLite/FTS index remain deferred to later changes.
