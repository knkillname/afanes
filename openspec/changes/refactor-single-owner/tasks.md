# Tasks

## 1. Canonical label writer

- [x] 1.1 Add `PageLabels.apply_to(document)` with strict NumPy docstrings and a full matrix test in
  `tests/core/test_labels.py` covering every note type, category, status, due date, requester, date,
  unknown keys, and CRLF preservation; verify `hatch test tests/core/test_labels.py` passes.
- [x] 1.2 Add a Hypothesis round-trip test that
  `PageLabels.from_document(labels.apply_to(document))` reproduces the same valid labels; add a
  deterministic regression test for any minimized failure; verify
  `hatch test tests/core/test_labels.py` passes.
- [x] 1.3 Route `NormalDraft.to_text` through `PageLabels.apply_to`, keep the log date identity guard
  in `NormalDraft`, and remove `_write_labels`/`_write_date`; verify
  `hatch test tests/core/test_editing.py` passes.
- [x] 1.4 Route `VaultPages.set_status` and `VaultNaming.apply_category_move` through the label owner,
  preserving the current validation message and unknown-key/newline behavior; verify
  `hatch test tests/core/vault/test_pages.py tests/core/vault/test_naming.py` passes.
- [x] 1.5 Route `VaultNaming._write_conversion` and `ProcessingPlan.processed_text` through the label
  owner, preserving the target type/status/date rules for every processing outcome; verify
  `hatch test tests/core/vault/test_naming.py tests/core/test_processing.py` passes.
- [x] 1.6 Route `Vault.new_note_document`, the date insertion in `VaultPages.create_page`, and the
  date insertion in `TemplateCatalog` through the label owner; verify
  `hatch test tests/core/vault/test_service.py tests/core/vault/test_pages.py tests/core/test_templates.py`
  passes.
- [x] 1.7 Add the architecture tripwire that rejects label-key assignment or `pop` outside
  `core/labels.py` and `core/frontmatter.py`; verify
  `hatch test tests/core/test_architecture.py` passes.

## 2. Canonical template card picker

- [x] 2.1 Add `ui/components/template_cards.py` with `TemplateCardContext`, `TemplateCardPhrases`,
  and `TemplateCardPicker`, with strict docstrings and unit tests for option keys/order, Empty last,
  duplicate titles, selection fallback, descriptions, and invalid-card warnings; verify the new
  component tests pass.
- [x] 2.2 Route `ProcessingView` through the picker while keeping `template`,
  `template_description`, and `template_warning` as public aliases; add a view-level test that the
  picker options are populated after entering processing from review; verify
  `hatch test tests/ui/test_processing_view.py` passes.
- [x] 2.3 Route `show_new_reference_dialog` through the picker while preserving
  `new-reference-template` and `new-reference-template-warning`; verify
  `hatch test tests/ui/test_app.py` passes.
- [x] 2.4 Route `show_log_entry_dialog` through the log picker context, add `LOG_CARD_EMPTY`, and add
  a regression test that the log Empty option says no starter body and does not mention a reference
  category; verify `hatch test tests/ui/test_app.py` passes.
- [x] 2.5 Add the architecture tripwire that rejects `_template_options`, `_template_option_text`,
  `_reference_template_options`, or `_reference_template_text` outside the shared component; verify
  `hatch test tests/core/test_architecture.py` passes.
- [x] 2.6 Update `CHANGELOG.md` under `Unreleased` with the canonical-owner change and the log Empty
  wording fix; confirm whether any docs page describes the old wording and record
  `Docs: no change required` if none does; verify the entry names this change.

## 3. Retired InboxView removal

- [x] 3.1 Re-run the D8 reference proof before deleting anything: the AST count must show zero
  production references to `InboxView` outside `ui/views/inbox.py`, `WelcomeView` and `SessionNotice`
  must still have `ui/app.py` callers, and no entry point, packaging file, docs page, README, or main
  spec may reference `InboxView`; record the command output in the task commit.
- [x] 3.2 Remove `TestInboxView` and its exclusive helpers, constants, and imports from
  `tests/ui/test_inbox_view.py`, keeping the `WelcomeView` tests; verify
  `hatch test tests/ui/test_inbox_view.py` passes.
- [x] 3.3 Remove the `InboxView` class and its exclusive private methods and imports from
  `ui/views/inbox.py`, keeping `WelcomeView`, `SessionNotice`, and shared helpers such as `Banner`;
  verify `grep -rn "InboxView" src` returns nothing and
  `hatch test tests/ui/test_app.py tests/ui/test_inbox_view.py` passes.
- [x] 3.4 Remove `scan_warning_title` and `scan_warning` from `ui/strings.py`; verify
  `grep -rn "scan_warning" src tests docs` returns nothing and the targeted UI tests pass.
- [x] 3.5 Add the `Removed` entry to `CHANGELOG.md` with the `InboxView` migration note and the live
  `WorkspaceView` replacement; verify the entry names this change and records that no user-visible
  workflow changed.
- [x] 3.6 Re-run the reference proof and verify the module still exports only the live views; run
  `hatch test tests/ui/test_app.py tests/ui/test_inbox_view.py` and verify both pass.

## 4. Integration verification

- [x] 4.1 Run `hatch check` and verify lint, formatting, and Pyrefly strict pass.
- [x] 4.2 Run `hatch test --cover` and verify the full suite passes at 85% coverage or higher.
- [x] 4.3 Run `hatch run docs:build` and verify the Sphinx build passes with no warnings.
- [x] 4.4 Run `openspec validate --all --strict` and `openspec doctor`, and verify both pass.
- [x] 4.5 Run the two vocabulary/compliance grep commands from `AGENTS.md` section 6.1 and verify
  both exit 1 with no output.
- [x] 4.6 Review the final diff and verify it touches only the files listed in `proposal.md`, the
  change artifacts, and `CHANGELOG.md`, with no unrelated formatting churn.

## Workflow follow-up

- Archive the change after review and implementation are complete.
- Run the post-archive release workflow, record the version decision, README status, and Docs status,
  and report the commit hash.
