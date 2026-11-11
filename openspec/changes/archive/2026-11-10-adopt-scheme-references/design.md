# Design

## Context

The repository is a scaffold: `src/afanes/` contains only the package initializer and version module, no main specs exist, and `AGENTS.md` currently documents `[[Target]]` links and vault-relative path identity. This change establishes the reference model before any vault code exists, so there is no user data to migrate.

Constraints that shape the approach:

- Markdown files are authoritative; the SQLite index is disposable and rebuildable.
- The vault must remain readable and editable without Afanes, on macOS, Linux, and Windows.
- `models/` imports only the standard library; `core/` may import `models/`; `ui/` and `cli/` sit above both.
- No runtime network access, accounts, telemetry, or cloud storage.

## Goals / Non-Goals

**Goals:**

- Name-based references that survive directory moves.
- Reference syntax that is valid Markdown and readable outside the application.
- One identity per note, visible in the vault, with no hidden database-only key.
- Deterministic resolution with explicit failure states instead of guessing.
- Safe, confirmed rename that keeps the graph intact.

**Non-Goals:**

- Auto-linking bare words or CamelCase identifiers.
- Export or publish tooling that rewrites references to paths. The model makes it possible later; it is not built here.
- Heading anchors, block references, transclusion, or embeds.
- Writing backlinks into note bodies.
- Namespace-qualified references. Directories are classification, not identity.
- A stored `id` field.
- Link rendering in the UI, CLI command wiring, and the persistent SQLite cache. This change builds the core engine; those capabilities consume it later.

## Module Map

```text
models/note.py        NoteType
models/link.py        ReferenceScheme, NoteReference
core/errors.py        domain exception hierarchy
core/names.py         normalize_name, safe_filename, unique_name
core/links.py         parse, extract, classify, NameCatalog, rewrite body
core/frontmatter.py   NoteDocument: fence parsing, safe YAML, references
core/vault.py         containment, read-only scan, atomic writes, create, move, rename
```

`names.py` is a leaf module: it imports only the standard library so both `links.py` and `vault.py` can use it without creating a cycle. `links.py` and `vault.py` import `names.py`; `frontmatter.py` imports `links.py` for reference validation. No module in `core/` imports `ui/` or `cli/`.

## Decisions

### 1. Standard Markdown links with typed schemes

Internal references use `[Label](scheme:Name)`, with angle-bracketed destinations when the name cannot appear bare:

```markdown
Call [Ada Lovelace](<person:Ada Lovelace>) about the crown, then update
[Turing Machine](project:TuringMachine).
```

**Why:** the body stays valid CommonMark, labels render everywhere, and the parser handles escapes, code spans, and nested brackets instead of us.

**Alternatives considered:**

- `[[Target]]`: not Markdown, renders as literal brackets outside Afanes, requires a custom scanner that must reimplement code-span and escape rules.
- Path links: portable and navigable elsewhere, but store location in the reference, so a move changes meaning and requires rewriting every inbound and outbound link.
- A single namespaced scheme such as `afanes:person/Ada`: one scheme is easier to reserve, but it adds noise to every reference and hides the type inside a path. Rejected in favor of three short, readable schemes.

**Cost accepted:** `person:Ada` is a dead destination outside Afanes. The file remains readable and the label renders; only navigation is lost. An export step can resolve names to paths later because the names are in the files.

### 2. Three schemes, not one per type

```
person:X    -> type person
project:X   -> type project
note:X      -> type note, action, or reference
```

`note` covers the document family so that the Processing Wizard can change an inbox note into an action or reference without invalidating a single reference. `person` and `project` are stable entity types and get their own namespaces.

**Alternatives considered:**

- Five schemes mirroring every type: any type change breaks references.
- One global scheme: the scheme stops carrying meaning, and the namespace no longer guarantees a target type.
- Namespace-qualified references: directories would become identity, contradicting the classification rule.

**Consequence:** per-scheme namespaces allow a person and a project to share a name, which is useful and unambiguous.

### 3. The filename stem is name, title, and identity

No `title` key, no `id` field. The name is case-preserving for display and case-insensitive for identity.

**Alternatives considered:**

- Stored `id:`: renames become free, but the format grows a second name that can drift from the filename and the title, and the user must maintain it.
- Vault-relative path: directory moves break references.
- First `# Heading` as title: heading edits are frequent and would silently break the graph.

**Consequence:** renaming is a reference-maintaining operation, which is why the application, not the file manager, owns structural changes.

### 4. Directories classify; they do not identify

Moving a note never changes a reference. This is the reason the reference excludes the path.

Because the filesystem only enforces uniqueness within a directory, the application enforces a stronger invariant: one name per scheme across the whole vault. External duplicates are an unsupported state that the diagnostics surface reports and resolution refuses to guess about.

### 5. One normalization function, used everywhere

`core/names.py` owns three pure functions:

```text
normalize_name(text)    NFC -> casefold -> trim -> collapse internal whitespace
                        -> strip one trailing ".md"
safe_filename(title)    cross-platform sanitization and determinism
unique_name(name, taken) deterministic integer suffixing
```

Both the reference resolver and the vault writer import this module. It is a leaf that imports only the standard library, so it introduces no cycle. Without a shared function, `links.py` and `vault.py` would drift and a link would stop matching the file it names.

**Why casefold rather than lower:** it is the conservative fold, so any collision the operating system might consider equal is already equal in the catalog. The vault can flag `Straße` and `Strasse` as duplicates instead of failing later on one platform.

### 6. Lazy resolution: edges store the name, not the target

The `NameCatalog` value object owns the `(scheme, name_key) -> tuple[note_path, ...]` mapping. `from_entries` normalizes names and keeps every candidate, `candidates` exposes the matches for one scheme and name, and `resolve` applies the resolution outcome. Duplicate names are visible as multiple candidates rather than silently overwriting. When the persistent cache arrives, edges are stored as `(source_path, scheme, name_key, label, origin)`. In this change the catalog lives in memory and is rebuilt per scan. Resolution happens at query time.

**Why:** creating a note heals every existing reference that mentions it. Deleting a note leaves inbound references dangling without cascades or cleanup. There is no re-resolution pass after incremental indexing, and the cache can be dropped and rebuilt without loss.

**Alternative considered:** eager resolution with foreign keys. It requires cascading updates on create, delete, and rename, and it cannot heal a reference that was unresolved at index time.

### 7. Resolution never touches the filesystem

A reference name is looked up in the catalog. It is never joined to a path and never opened. Names containing `/`, `\`, or `..` therefore cannot traverse anywhere; they simply match nothing.

This also guarantees identical resolution on all three platforms, because the catalog is built from vault-relative paths under our own normalization rather than from platform path semantics.

### 8. Explicit links only

No bare-word or CamelCase auto-linking. Ordinary prose contains `JavaScript`, `PowerPoint`, and `YouTube`, which would silently become links the moment a matching note existed. A bare word also cannot express which scheme it means.

CamelCase remains a useful naming style when the user chooses it, but it is never link syntax.

### 9. Cross-platform names are deterministic

`safe_filename` applies, in order:

1. NFC normalization.
2. Forbidden characters replaced with a space; control characters removed.
3. Runs of whitespace collapsed; leading and trailing whitespace trimmed.
4. Reserved Windows device names suffixed with `-note`.
5. Trailing dots and spaces removed.
6. Leading dots removed.
7. Truncation to 200 UTF-8 bytes on a character boundary.
8. Fallback to `Untitled` when empty.

Creation appends the smallest available integer suffix (` 2`, ` 3`) when the name exists in its scheme or in the target directory. An explicit rename to an occupied name is rejected rather than silently suffixed.

**Why 200 bytes:** below every supported platform's component limit even for multi-byte names, and short enough to keep links readable.

### 10. Rename protocol

```text
plan      references in the index whose scheme and name resolve to this note
preview   count of references and affected notes
confirm   explicit user action
rename    one atomic file operation
rewrite   one atomic write per referring note, guarded by the content hash
verify    re-parse each rewritten note
report    updated / skipped / failed, with paths
```

Only destinations that resolved to the renamed note are rewritten, so an ambiguous duplicate name never causes collateral edits. A label is updated only when it equals the old name; a custom label is preserved. A file that changed since the plan is skipped and reported instead of overwritten. The operation is re-runnable and idempotent.

**Alternative considered:** a journaled multi-file transaction. It buys atomicity across files at a large complexity cost. The worst outcome here is a visible unresolved reference, never lost text, because each file write is atomic and the user is told exactly what happened.

### 11. External structural changes are detected, not adopted

Content edits are supported and reindexed. Moves, renames, and deletions outside the application are reported; references are never rewritten to follow them silently. A future repair may detect a delete plus a create with the same content hash and offer to re-point the graph, but the offer requires confirmation.

This keeps startup read-only and respects the rule that identities are never rewritten silently.

### 12. A CommonMark parser is a runtime dependency

Hand-rolled extraction cannot reliably handle reference links, nested brackets, escapes, code spans, HTML blocks, autolinks, and images. The design uses a CommonMark-compliant parser (`markdown-it-py`, pure Python, MIT) and reads link and image tokens from its AST.

**Alternatives considered:**

- Regular expressions: fail on code spans and nested brackets; produce false references in code.
- Python-Markdown: not CommonMark-compliant, so "valid Markdown" would mean something different from what other tools render.

**Dependency obligations:** pinned exact version, license and offline behavior recorded in the change, no network use at runtime.

Rewriting needs to locate destinations, not just detect them. The implementation will verify whether the chosen parser exposes usable source positions; the fallback is to re-parse the affected note and replace the matching destination tokens, then re-parse to confirm. The index stores names rather than offsets, so this choice does not affect the data model.

### 13. Frontmatter uses the same reference form

```yaml
people:
  - "person:Ada Lovelace"
project: "project:Turing Machine"
```

No angle brackets in YAML: those are Markdown destination quoting, not part of the name. Values that are not scheme references are validation errors and are never coerced. Using a scheme reference also avoids YAML's reserved leading `@`.

### 14. Backlinks are derived, never written

The reverse graph lives in the index and is rebuilt by scanning. Writing backlinks into note bodies would mutate prose, create write amplification, and make the files depend on application behavior.

### 15. Frontmatter is a `NoteDocument` value object

The frontmatter block is located by an explicit `---` fence parser, then loaded with `yaml.safe_load`. `python-frontmatter` is not used, because the write path needs precise control over block boundaries, newline preservation, and which keys are re-emitted.

Metadata and its operations form one frozen `NoteDocument` value object with `from_text`, `to_text`, `with_body`, and `rewrite_references`. Private class methods own fence splitting, YAML loading, type resolution, and reference validation. This keeps the invariants together: callers cannot parse metadata, replace a body, and serialize through three unrelated functions that must be sequenced correctly. Stateless transformations stay module-level functions; this class exists because the data and the behavior protect the same invariants.

**Consequences:** the frontmatter block is re-emitted with unknown keys and key order preserved, and only the `people` and `project` values change. YAML comments inside the block may be lost when it is rewritten; the design records that as a known limitation rather than promising comment preservation.

### 16. Validation raises from `core/errors.py`, models stay data

`NoteReference` and `NoteType` are plain immutable value objects. Reference validation happens in `core/links.py` and `core/frontmatter.py`, which raise domain exceptions from `core/errors.py`. This avoids the contradiction between "models import only the standard library" and "models raise domain exceptions" while keeping one exception hierarchy for callers.

### 17. Vault scan is read-only and deterministic

`scan_vault(root)` enumerates `.md` files, skips directories whose names begin with a dot, and skips symlinks that resolve outside the root. It parses metadata, extracts references, and builds the catalog into an in-memory snapshot. It never writes. A malformed note becomes a reported failure and does not abort the scan.

## Risks / Trade-offs

- **Dead destinations outside Afanes.** `person:Ada` renders as a non-navigable link in other tools. Mitigation: the label always renders, the body stays valid, and export can resolve names to paths later.
- **Lossy title sanitization.** `Q1: Planning?` becomes `Q1 Planning`. Mitigation: show the derived name before creation and let the user edit it; the sanitized form is honest because it *is* the title.
- **Partial rename rewrites.** A failure midway leaves some references unresolved. Mitigation: per-file atomic writes, hash-guarded skips, a report, and a re-runnable operation.
- **Name reuse after deletion.** Deleting `person:Ada` and later creating a new `person:Ada` would silently retarget old references. Mitigation: report inbound reference counts before deletion; a name-reuse warning is a candidate follow-up requirement.
- **Case-fold collisions.** `Straße` and `Strasse` normalize together. Mitigation: surface them as duplicates rather than merging silently.
- **Name uniqueness is stronger than the filesystem.** External tools can create duplicates. Mitigation: the diagnostics surface reports them; resolution returns ambiguity instead of picking.
- **Label drift.** A custom label does not follow a rename. Mitigation: only default labels are updated; custom labels are intentional text.
- **Parser dependency.** Adds a runtime package. Mitigation: pure Python, pinned, justified by correctness; recorded in the proposal and design.
- **Unicode and case behavior across platforms.** macOS may return decomposed filenames; Windows and macOS are case-insensitive. Mitigation: NFC and casefold on both sides of every comparison, with property-based tests.

## Test Strategy

- Property-based tests (Hypothesis) for `normalize_name` and `safe_filename`: idempotence, round-trip of the sanitized name, no forbidden characters, no reserved names, bounded bytes, deterministic suffixing.
- Extraction tests: fenced code, inline code, HTML comments, images, reference-style links, escaped brackets, nested labels.
- Resolution tests: unique, unresolved, ambiguous, separate namespaces, traversal-looking names, healing after creation, dangling after deletion.
- Rename tests: preview counts, cancellation, custom label preservation, changed-file skip, partial failure reporting, re-run idempotence.
- Architecture tests: `models/` imports only the standard library; no `core/` to `ui/` or `cli/` edge; `names.py` stays a leaf.
- Cross-platform tests: reserved names, trailing dots, case-fold duplicates, NFC/NFD pairs.
- Public-contract tests only: no production-private member is imported, called, or monkeypatched. Private helpers in `NoteDocument`, `links.py`, and `vault.py` are exercised through their public entry points; behavior worth testing without a public path is promoted, not exposed to tests.
- No test touches a real vault, the network, or the user's home directory.

## Migration Plan

No vault exists, so there is no data migration. This change builds the catalog in memory per scan; the persistent SQLite cache arrives with a later capability and reuses the same `NameCatalog` and resolution rules. Implementation updates `AGENTS.md` sections 1.3, 2.4, 3.1, and 4.7 to remove the `[[...]]` format, the path identity rule, and the `python-frontmatter` requirement. Rollback is a revert of the change, with no user data at risk.

## Open Questions

- Whether the chosen parser exposes enough source-position information for destination replacement, or whether the targeted re-parse fallback is required. This is an implementation detail and does not change the specs.
- Whether export should resolve references to relative paths or to a static-site URL form. Deferred to the export capability.
