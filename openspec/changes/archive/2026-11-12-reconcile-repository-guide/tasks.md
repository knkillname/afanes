# Tasks

## 1. Adopt and renumber the guide

- [x] 1.1 Renumber the surviving `AGENTS.md` headings contiguously to 1, 2, 2.1, 3, 3.1, 3.2, 4, 4.1-4.8, 5, 5.1-5.3, 6, 6.1; verify with `grep -nE '^#{2,3} ' AGENTS.md` that no number is skipped.
- [x] 1.2 Update the four live citations: `openspec/config.yaml` 4.2 to 4.1, `tests/core/test_architecture.py` 4.3 to 4.2, and the `AGENTS.md` self-references 5.8 to 5.3 and 6.6 to 6.1; verify `grep -rnoE 'section [0-9]+(\.[0-9]+)?'` over live files resolves.
- [x] 1.3 Restore the type-checking rules from design D4 as one short section; verify `hatch check types` passes and the section names annotations, generics, forward references, and Pyrefly strict.
- [x] 1.4 Restore the error and logging rules from design D4; verify the text names the domain exception module, cause preservation, per-module loggers, and the no-note-body rule.
- [x] 1.5 Restore the concurrency rules from design D4; verify the text names the synchronous core, the UI async boundary, `asyncio.to_thread`, one writer per vault, and the no-sleep rule.
- [x] 1.6 Replace the SQLite sentence in `openspec/config.yaml` with the in-memory snapshot design and the approved-change rule; verify the context no longer claims a SQLite index and still states the offline, vocabulary, docstring, and platform constraints.
- [x] 1.7 Record the destination of every removed heading as a short section map in the commit body; verify every heading removed by the rewrite appears exactly once.

## 2. Guard the numbering

- [x] 2.1 Add a citation test to `tests/core/test_architecture.py` that collects numbered headings from `AGENTS.md` and asserts every `section N(.N)` citation in `AGENTS.md`, `README.md`, `CHANGELOG.md`, `openspec/config.yaml`, `openspec/specs/`, `src/`, and `tests/` resolves, excluding `openspec/changes/`; verify it passes.
- [x] 2.2 Add a unit test that gives the citation parser a document citing a missing section and asserts it reports the failure; verify the passing and failing cases run with `hatch test tests/core/test_architecture.py`.
- [x] 2.3 Add the `Unreleased` changelog entry naming this change and the renumbering; verify the entry sits under `Unreleased` with no version bump.

## 3. Integration checks

- [x] 3.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the 6.6 compliance check; verify all pass before the change is reported complete.
