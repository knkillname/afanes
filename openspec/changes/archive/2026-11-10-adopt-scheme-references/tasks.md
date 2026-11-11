# Tasks

## 1. Foundation

- [x] 1.1 Add `markdown-it-py` and `PyYAML` to `pyproject.toml` as exact runtime pins and re-sync the Hatch environment; verify `hatch run python -c "import markdown_it, yaml"` succeeds and `hatch check` still passes.
- [x] 1.2 Create `src/afanes/core/errors.py` with `AfanesError`, `VaultError`, `VaultPathError`, `NoteParseError`, `InvalidReferenceError`, `NameCollisionError`, and `ReferenceRewriteError`, each with a NumPy-style docstring; verify a test asserts the hierarchy and that no built-in exception name is reused.
- [x] 1.3 Create `src/afanes/models/note.py` with the `NoteType` enum and `src/afanes/models/link.py` with `ReferenceScheme` and the frozen `NoteReference` value object; verify tests cover construction, equality, and that both modules import only the standard library.
- [x] 1.4 Add `tests/core/test_architecture.py` that parses imports with `ast` and rejects `models/` importing `core/`, `ui/`, or `cli/`, and `core/` importing `ui/` or `cli/`; verify the test passes on the current tree.

## 2. Names

- [x] 2.1 Implement `normalize_name` in `src/afanes/core/names.py` with NFC normalization, case folding, trimming, whitespace collapse, and one optional trailing `.md`; verify Hypothesis tests cover idempotence, case variants, Unicode forms, and whitespace runs.
- [x] 2.2 Implement `safe_filename` with the ordered rules in design decision 9; verify tests cover forbidden characters, reserved device names, trailing dots and spaces, leading dots, the 200-byte limit, and the `Untitled` fallback.
- [x] 2.3 Implement `unique_name(name, taken)` with deterministic integer suffixing; verify tests cover no collision, one collision, and gaps in the suffix sequence.
- [x] 2.4 Verify `core/names.py` imports only the standard library and is not imported by `models/`; extend the architecture test.

## 3. Reference parsing and extraction

- [x] 3.1 Implement `parse_reference(destination)` in `src/afanes/core/links.py` for `scheme:name`, including case-insensitive schemes, angle-bracket stripping, empty names, and unknown schemes; verify tests cover each outcome and that invalid values raise `InvalidReferenceError`.
- [x] 3.2 Implement `extract_references(markdown)` over the parser's link tokens; verify tests cover plain links, angle-bracket destinations, reference-style links, nested brackets, escaped brackets, fenced code, indented code, inline code, HTML comments, and images.
- [x] 3.3 Implement `classify_destination(destination)` returning internal, external, attachment, anchor, or unsafe; verify tests cover `person:`, `project:`, `note:`, `https:`, `mailto:`, `javascript:`, relative paths, and `#heading`.
- [x] 3.4 Add the Hypothesis property test that wrapping input in a fenced code block yields no extracted references; verify it passes.

## 4. Frontmatter

- [x] 4.1 Implement the fence parser and safe YAML loading in `src/afanes/core/frontmatter.py`; verify tests cover absent frontmatter, malformed YAML, a body beginning with `---`, CRLF preservation, and unknown keys.
- [x] 4.2 Parse `people` and `project` into references, raising `InvalidReferenceError` for non-reference values; verify tests cover valid lists, bare names, wrong schemes, and a non-list `people` value.
- [x] 4.3 Preserve the raw frontmatter mapping and original newline style on the parsed metadata object; verify tests assert preservation of unknown keys and line endings.

## 5. Catalog and resolution

- [x] 5.1 Implement `NameCatalog.from_entries(entries)` from `(path, NoteType)` pairs using `normalize_name`; verify tests cover scheme membership, cross-scheme reuse, duplicate names, and case and Unicode equivalence.
- [x] 5.2 Implement `NameCatalog.resolve(reference)` returning resolved, unresolved, or ambiguous; verify tests cover each outcome, that separate namespaces never resolve across schemes, and that ambiguous results list all candidates.
- [x] 5.3 Verify healing and dangling behavior: an unresolved reference resolves when the matching note is added, and a resolved reference becomes unresolved when the note is removed.
- [x] 5.4 Verify that names containing `/`, `\`, or `..` match nothing and that resolution performs no file I/O, using a patched `open` that fails if called.
- [x] 5.5 Implement a read-only `scan_vault(root)` in `src/afanes/core/vault.py` that enumerates Markdown files in a deterministic order, parses metadata, extracts references, records a content hash per note, and builds the catalog snapshot per design decision 17; verify tests cover nested directories, dot directories, symlink escape, malformed notes, and zero writes.

## 6. Vault writes

- [x] 6.1 Implement vault root resolution and path containment in `src/afanes/core/vault.py`; verify tests under `tmp_path` reject traversal, absolute paths, and symlinks that escape the root.
- [x] 6.2 Implement atomic write with a temporary file in the same directory, flush, `os.fsync`, `os.replace`, and cleanup on failure; verify tests cover success, cleanup after failure, and preservation of the existing newline style.
- [x] 6.3 Implement note creation with `safe_filename` and `unique_name`; verify tests cover sanitized titles, suffix collisions, reserved names, and that the sanitized stem becomes the title.
- [x] 6.4 Implement directory moves that change no reference and rewrite no file; verify tests assert the file moves and every inbound reference still resolves.

## 7. Rename and deletion

- [x] 7.1 Implement rename planning that collects only references resolving to the target note and returns a preview with reference and note counts; verify tests cover zero, one, and many affected notes and exclude references that resolve elsewhere.
- [x] 7.2 Implement body reference rewriting, updating destinations that normalize to the old reference and only those labels that equal the old name, while preserving bracket style; verify tests cover custom-label preservation, case variants, angle-bracket destinations, and exact destination replacement.
- [x] 7.3 Implement frontmatter reference rewriting for `people` and `project`, preserving unknown keys and their order; verify tests assert updated values and untouched keys.
- [x] 7.4 Add rejection of an explicit rename to a name already used in the same scheme; verify the note keeps its current name and the error is actionable.
- [x] 7.5 Implement the content-hash guard that skips a referring note changed since planning; verify tests cover skip, report, and no overwrite.
- [x] 7.6 Implement the partial-failure report and re-run behavior; verify tests assert the updated, skipped, and failed sets and that a second run completes without duplicating changes.
- [x] 7.7 Implement deletion reporting: count inbound references, require confirmation, leave references unresolved, and modify no referring note; verify tests cover the count and the unchanged files.

## 8. Documentation and compliance

- [x] 8.1 Update `AGENTS.md` sections 1.3, 2.4, 3.1, and 4.7 with the new reference syntax, filename identity, module map, and dependency list; verify the canonical format section contains no bracket-link example and matches the spec.
- [x] 8.2 Add a short vault-format example to `README.md` showing `person:` and `project:` references; verify the example matches the spec scenarios.
- [x] 8.3 Run the compliance check from AGENTS.md section 6.6 (or an equivalent grep pattern where `rg` is unavailable) and verify it exits clean.

## 9. Integration and gates

- [x] 9.1 Add an end-to-end test that creates two notes, links them, verifies resolution, moves one between directories, verifies resolution survives, renames it, and verifies the reference is rewritten.
- [x] 9.2 Run `hatch check` and verify Ruff and Pyrefly pass.
- [x] 9.3 Run `hatch test --cover` and verify coverage is at least 85%.
- [x] 9.4 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass.

## Workflow follow-up

- Archive the change after review and approval.
- Run the post-archive release workflow in AGENTS.md section 5.8: version bump, changelog entry, README review, gates, and release commit.
