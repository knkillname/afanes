# Tasks

## 1. Title derivation

- [x] 1.1 Add a derived `title` to `NoteDocument` that returns the plain text of the first non-blank level-1 heading, trimmed, and recomputes on `with_body`; add tests in `tests/core/test_frontmatter.py` for an ATX heading, a setext heading, a heading after introductory text, two headings, an empty heading, inline formatting, and a `#` inside a fenced code block; verify `hatch test tests/core/test_frontmatter.py` passes.
- [x] 1.2 Carry `title` on `VaultNote`, falling back to the scanned filename stem when the document has no title; add tests in `tests/core/test_vault.py` for a heading title, the identity fallback, and an invalid-title note that still fails as before; verify `hatch test tests/core/test_vault.py` passes.

## 2. Capture template

- [x] 2.1 Update `Vault.capture` to insert `# ` at the start of the first non-blank line unless it already begins with `#`, leaving all other text and the existing newline normalization unchanged; update the method docstring; add tests in `tests/core/test_vault.py` for a plain capture, an existing heading, leading blank lines, and a sanitized first line; verify `hatch test tests/core/test_vault.py` passes.
- [x] 2.2 Update `tests/core/test_integration.py` so the inbox capture and processing flows assert the templated body and the derived title; verify `hatch test tests/core/test_integration.py` passes.

## 3. Inbox display

- [x] 3.1 Make the Inbox list show `VaultNote.title` as the primary text and keep the vault-relative path as the subtitle; add tests in `tests/ui/test_inbox_view.py` for a heading title, the identity fallback, and two notes with the same title; verify the file passes.
- [x] 3.2 Make the Inbox preview header and the Processing Wizard capture panel show the display title instead of the filename stem; add or adjust tests in `tests/ui/test_inbox_view.py` and `tests/ui/test_processing_view.py`; verify both files pass.

## 4. Assignment suggestions

- [x] 4.1 Add `VaultSnapshot.assignment_candidates(scheme, query)` with normalized substring matching over identity and display title, ordered by title then identity; add tests in `tests/core/test_vault.py` for identity match, title match, case and repeated whitespace, duplicate titles, scheme filtering, and an empty query; verify the file passes.
- [x] 4.2 Retain the last scan snapshot in `AppState` and expose a command that returns assignment candidates for a scheme and query; add tests in `tests/ui/test_state.py`; verify the file passes.
- [x] 4.3 Add suggestion lists under the Processing Wizard people and project fields, showing the title and the identity when they differ, and replacing the active token with the page identity when a suggestion is chosen; keep free text possible; add tests in `tests/ui/test_processing_view.py`; verify the file passes.
- [x] 4.4 Confirm `Vault.plan_processing` still stores identities and leaves unmatched free text unresolved after the suggestion change; add or adjust tests in `tests/core/test_processing.py`; verify the file passes.

## 5. Documentation

- [x] 5.1 Update `AGENTS.md` sections 1.3, 1.4, and 4.7 to state that the filename is the identity, the first level-1 heading is the display title, and captures write the heading template; verify each changed section matches the implemented behavior and the delta specs.
- [x] 5.2 Update `README.md` vault format and capture documentation with the heading convention and the title fallback; verify the example matches the body produced by `Vault.capture` in `tests/core/test_vault.py`.

## 6. Integration checks

- [x] 6.1 Run `hatch check` and resolve every lint, format, and type finding.
- [x] 6.2 Run `hatch test --cover` and confirm the full suite passes with at least 85% coverage.
- [x] 6.3 Run `openspec validate --all --strict` and `openspec doctor`; resolve every finding.
- [x] 6.4 Run the neutral-vocabulary compliance check from `AGENTS.md` section 6.6 and confirm it is clean.

## Workflow follow-up

- Archive the change after review and sync the delta specs into `note-identity`, `inbox-capture`, and `processing`.
- Run the post-archive release workflow from `AGENTS.md` section 5.8; expected bump is MINOR because no vault file requires migration.
- The note editor, link-driven page creation, and the rename heading rule are the next change, built on this identity model.
