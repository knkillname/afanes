# Design

## Context

See `proposal.md` - Why. Two facts shape the approach:

- The compressed guide keeps six numbered sections but only 21 of the original
  headings. The numbers that survive are 1, 2, 2.2, 3, 3.1, 3.3, 4, 4.2, 4.3,
  4.4, 4.6, 4.9, 4.11, 4.13, 4.14, 5, 5.1, 5.5, 5.8, 6, 6.6.
- Four live citations exist: `openspec/config.yaml` cites 4.2,
  `tests/core/test_architecture.py` cites 4.3, and `AGENTS.md` cites 5.8 and
  6.6. Archived change artifacts cite 1.3, 1.4, 2.7, 4.3, 4.7, 4.9, 4.10,
  5.8, and 6.6.

`AGENTS.md` is loaded into every agent session, so length is a real cost. The
old 1049-line edition repeats material that Ruff, Pyrefly, and `pyproject.toml`
already enforce.

## Goals / Non-Goals

**Goals:**

- One authoritative edition of the guide with contiguous section numbers.
- No rule silently lost: every removed section is folded, restored, or
  recorded as intentionally dropped.
- `openspec/config.yaml` describes the architecture the code actually has.
- A test that fails when a live citation points at a missing section.

**Non-Goals:**

- Documenting every implementation detail. The guide stays a rulebook, not a
  tutorial.
- Rewriting archived change artifacts. They are historical records.
- Creating a SQLite cache. This change only stops claiming one exists.

## Decisions

### D1. Keep the compressed shape

Preserve the 209-line structure and add back only what tooling cannot enforce.
The alternative - restoring the full 1049 lines - was rejected because it
duplicates Pyrefly strict, Ruff's rule set, and `pyproject.toml`, and it makes
every agent session pay for repetition. The mitigation for lost nuance is the
section map in D2: nothing disappears without a recorded destination.

### D2. Renumber contiguously and rewrite live citations

Renumber the surviving headings 1, 2, 2.1, 3, 3.1, 3.2, 4, 4.1-4.8, 5,
5.1-5.3, 6, 6.1, then update the four live citations plus the architecture test
docstring and `AGENTS.md` self-references. Archived artifacts keep their
numbers. The alternative - leaving gaps and adding "reserved" placeholders -
was rejected because it preserves ambiguity and does not survive the next edit.

### D3. Reconcile the index statement in `openspec/config.yaml`

Replace "the SQLite index is a disposable cache" with a statement of the
current design: each vault is scanned into an in-memory snapshot and no
persistent index exists; adding one requires an approved change. This keeps the
project context truthful without forbidding the option. The alternative -
deleting the cache rules from `AGENTS.md` and letting the config stand - was
rejected because it contradicts the guide the config is meant to support.

### D4. Restore three rule groups, drop the rest deliberately

- **Type checking**: annotate every signature; no `Optional`, `List`, `Dict`,
  `Union`, or quoted forward references; no `from __future__ import
  annotations`; Pyrefly strict is the gate. Pyrefly catches some of this, but
  not the annotation style the project requires.
- **Errors and logging**: domain exceptions live in `core/errors.py`; no bare
  `except`; preserve causes; one logger per module; never log note bodies or
  absolute paths above DEBUG.
- **Concurrency**: `core/` and `models/` stay synchronous; async only at the UI
  boundary and the CLI's top-level orchestration; blocking I/O goes through
  `asyncio.to_thread`; one writer per vault; no `time.sleep` in UI code.

Dropped without replacement, because a live authority already covers them: the
import matrix (section 3.2 states the rule and Ruff's isort enforces order), the
file-layout table (section 3.1), the SQLite cache rules (no cache exists), and
the pre-flight checklist (replaced by the Definition of Done, section 4.8,
formerly 4.14).

### D5. Add a documentation citation test

Extend `tests/core/test_architecture.py` with a test that scans `AGENTS.md`,
`README.md`, `CHANGELOG.md`, `openspec/config.yaml`, `openspec/specs/`, and
Python sources under `src/` and `tests/` for `section N(.N)?` / `Section
N(.N)?`, collects the numbered headings from `AGENTS.md`, and asserts every
citation resolves. Exclude `openspec/changes/` so in-flight and archived
artifacts do not fail the gate on numbers that were correct when written.

The alternative - a convention with no test - was rejected because the rewrite
itself is evidence that conventions do not survive.

## Risks / Trade-offs

- [Archived citations become historically "wrong" against the live guide] ->
  Documented in D2 and excluded from the test; the archive is not rewritten.
- [Compression loses a rule a future reviewer relied on] -> D4 requires a
  recorded destination for every removed heading; the section map lands in the
  change summary.
- [The citation test is brittle around prose such as "this section"] -> Match
  only `section` followed by a number, and keep the allowlist of scanned files
  explicit.
- [Renumbering churns blame history] -> One dedicated commit for the renumber,
  separate from the restored rules, so `git blame` still explains each rule.

## Migration Plan

1. Land the numbering and citation updates in one commit.
2. Land the restored rule groups and the config reconciliation in a second
   commit.
3. Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`,
   and the 6.6 compliance check.

No runtime migration; the guide is not shipped with the package.

## Section map

Removed headings and their destinations in the reconciled guide:

| Removed heading | Destination |
| --- | --- |
| 1.1-1.5 | Section 1, project snapshot |
| 2.1-2.7 | Sections 2 and 2.1, commands and dependencies |
| 3.1-3.4 | Sections 3.1 and 3.2, layout and import rules |
| 4.1 | Sections 4.2 and 4.3, ownership and style |
| 4.2 | Section 4.1, vocabulary |
| 4.3 | Section 4.2, object ownership |
| 4.4-4.5 | Section 4.3, style and type checking |
| 4.6 | Section 4.4, docstrings |
| 4.7 | Sections 1 and 4.3, note model and style |
| 4.8 | Section 4.3, errors and logging |
| 4.9 | Section 4.5, vault writes |
| 4.10 | Dropped; no cache exists |
| 4.11-4.12 | Section 4.6, Flet UI and concurrency |
| 4.13 | Section 4.7, testing |
| 4.14 | Section 4.8, definition of done |
| 5.1-5.4 | Sections 5.1 and 5.2, gate and apply |
| 5.5 | Section 5.2, apply |
| 5.6-5.7 | Sections 5.2 and 5.3, validation and release |
| 5.8 | Section 5.3, post-archive release |
| 6.1-6.5 | Section 2, environment and commands |
| 6.6 | Section 6.1, compliance check |
| 6.7 | Section 2, build and release |
| Appendix A | Section 4.8, definition of done |

## Open Questions

None. The maintainer confirmed the compressed shape, so D1 stands and the
restore list in D4 is the full scope.
