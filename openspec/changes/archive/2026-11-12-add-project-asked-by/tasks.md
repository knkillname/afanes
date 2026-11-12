# Tasks

## 1. Frontmatter contract

- [x] 1.1 Add `asked_by` to `core/frontmatter.NoteDocument` parsing and `with_metadata` validation: one trimmed non-empty string, valid only for `project` notes. Verify `hatch test tests/core/test_frontmatter.py` covers project acceptance, reference and capture rejection, blank rejection, and non-string rejection.
- [x] 1.2 Add round-trip and preservation tests for `asked_by` alongside unknown frontmatter keys and both newline styles. Verify the focused frontmatter tests pass and the unknown keys remain byte-for-byte in the rewritten frontmatter.
- [x] 1.3 Update `docs/reference/frontmatter.md` and `docs/reference/vault-format.md` with the fifth key, its project-only scope, and the plain-label behavior. Verify `hatch run docs:build` and `hatch test tests/docs/test_style.py` pass.

## 2. Page labels and serialization

- [x] 2.1 Add `asked_by_text` to `core/editing.PageLabels`, populate it from the parsed document, add `with_asked_by_text`, and clear it in `with_type` when the type leaves `project`. Verify `hatch test tests/core/test_editing.py` covers load, set, clear, and type-change clearing.
- [x] 2.2 Write a trimmed non-blank `asked_by` from `NormalDraft.to_text` and remove the key for a blank value or a non-project type. Verify the draft serialization tests show the key present when set, absent when cleared, and every other byte preserved.

## 3. Page editing interface

- [x] 3.1 Add one `PageDialogState` command that updates the draft's `asked_by_text` without changing the scheme. Verify `hatch test tests/ui/test_state.py` shows the draft becomes dirty and the command stays within the existing controller command limit.
- [x] 3.2 Add the `Asked by` text field to the edit form in `ui/views/page.py`, visible only for projects, with copy in `ui/strings.py`. Verify `hatch test tests/ui/test_page_view.py` covers visibility for a project and absence for a reference and a capture.
- [x] 3.3 Add the `Asked by <name>` label to the project meta row in read mode, omitting it when the key is absent and leaving other page types unchanged. Verify `hatch test tests/ui/test_page_view.py` covers display, omission, and non-project pages.
- [x] 3.4 Update `docs/guide/projects-and-steps.md` with the fixed header field, the edit-form location, and the plain-label limitation. Verify `hatch run docs:build` and `hatch test tests/docs/test_style.py` pass.

## 4. Integration and verification

- [x] 4.1 Add an integration test that opens a project, sets a requester through the page draft, saves, and clears it, asserting the body, unknown keys, and newline style are unchanged. Verify the focused integration test passes.
- [x] 4.2 Run `hatch check` and verify Ruff, formatting, and Pyrefly strict report no errors.
- [x] 4.3 Run `hatch test --cover` and verify all tests pass with coverage at or above 85%.
- [x] 4.4 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass.
- [x] 4.5 Run the vocabulary compliance commands from `AGENTS.md` section 6.1; verify both exit non-zero with no output.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Update `CHANGELOG.md` under `Unreleased` with the new project requester field, and review `README.md` and `docs/` during the release step.
