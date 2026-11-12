# Proposal

## Why

`AGENTS.md` is the operating manual every agent reads before touching the
repository, and the working tree currently contains an unapproved rewrite that
shrinks it from 1049 to 209 lines. The surviving headings skip 1.1-1.5,
2.1-2.7, 3.2, 3.4, 4.1, 4.5, 4.7, 4.8, 4.10, 4.12, 5.2-5.4, 5.6-5.7,
6.1-6.7, and Appendix A, so a reader cannot tell a deliberate omission from a
section lost in the edit. Archived change artifacts still cite numbers such as
1.3, 2.7, 4.7, and 4.10 that no longer exist, and the four live citations that
survive (`openspec/config.yaml` 4.2, `tests/core/test_architecture.py` 4.3,
`AGENTS.md` 5.8 and 6.6) resolve only by luck of which numbers were kept.

Separately, `openspec/config.yaml` states that "the SQLite index is a
disposable cache" while `AGENTS.md` states that no index exists and that adding
one requires an approved change. The project's own precedence rule says to stop
and ask when authoritative sources conflict, so the manual cannot be trusted
until the conflict is resolved.

The rewrite also dropped rules that nothing replaced: the annotation and
type-checking rules, the error and logging rules, and the async and concurrency
constraints. Some of that detail is genuinely redundant with Ruff, Pyrefly, and
`pyproject.toml`; the rest constrains behavior those tools cannot see.

## What Changes

- Adopt a single, numbered edition of `AGENTS.md` and record why each removed
  section was either folded into a surviving rule or dropped as unenforceable.
- Renumber the surviving sections contiguously and update every live
  cross-reference (`openspec/config.yaml` 4.2, `tests/core/test_architecture.py`
  4.3, `AGENTS.md` 5.8 and 6.6). Archived change artifacts keep their original
  numbers as historical records; they are not rewritten.
- Reconcile the index statement: `openspec/config.yaml` stops describing a
  SQLite cache that the application does not have, and `AGENTS.md` keeps the
  "no index without an approved change" rule.
- Restore the type-checking, error/logging, and concurrency rules that are not
  covered by tooling, or state explicitly where the tool is the only rule.
- Add a repository test that fails when a document references a numbered
  section that does not exist, so the next rewrite cannot silently break
  cross-references.

**BREAKING** for maintainers only: the section numbers in review comments and
agent prompts change. No product behavior changes.

## Capabilities

None. This change alters repository guidance, engineering standards, and one
architecture test, not application behavior. `skip_specs: true` is declared in
`.openspec.yaml`.

### New Capabilities

- None.

### Modified Capabilities

- None.

## Impact

- `AGENTS.md`: numbering, restored rules, removed-section rationale.
- `openspec/config.yaml`: `context` no longer claims a SQLite index exists.
- `tests/core/test_architecture.py`: docstring reference and the new
  cross-reference test.
- Possibly `README.md` and `CHANGELOG.md` if either cites a section number.
- No source module, dependency, or runtime behavior is touched.

## Open Questions

None. The maintainer confirmed the compressed 209-line shape and the
restore-only-what-tooling-cannot-enforce rule, so D1 stands.
