# Proposal

## Why

Two repeated operations currently have more than one implementation, and each duplicate is a second
place where a bug fix can miss. Frontmatter labels are written by five separate paths: the page draft,
the status command, category moves, log/type conversions, and processing plans. Four of those paths
re-encode the same type-dependent key rules that `PageLabels.with_type` already owns. A new
frontmatter key or note type can therefore be handled correctly in one writer and forgotten in
another.

The template card picker has the same problem. The processing wizard and the browser/log dialogs build
their own option lists, duplicate-title handling, and descriptions. The log dialog reuses the reference
picker, so its Empty option currently says "Empty - general category, no starter body" for a log entry
that has no category. The recent review-entry bug followed the same shape: two ways into the wizard,
one of which forgot to load the card catalog.

A third duplicate is pure dead weight: `InboxView` was retired when the workspace browser replaced it,
but the class and its tests remain. No production module references it, and the archived
`add-review-workspace` design records the retirement. Keeping it gives tests a second implementation
to protect and gives a future fix a wrong place to land.

This is the right moment to collapse both families onto one owner and remove the retired path before
more commands and pickers are added. The work is behavior-preserving except for correcting the log
picker's Empty wording.

## What Changes

- Add `PageLabels.apply_to(document)` as the single writer for editable frontmatter labels. It owns
  type, category, status, due date, requester, and note date, preserves unknown keys and newline
  style, and validates through `NoteDocument.with_metadata`.
- Route every label writer through it: `NormalDraft.to_text`, `VaultPages.set_status`,
  `VaultNaming.apply_category_move`, `VaultNaming._write_conversion`,
  `ProcessingPlan.processed_text`, `Vault.new_note_document`, and the date insertion in
  `VaultPages.create_page` and bundled template rendering.
- Add `ui/components/template_cards.py` with `TemplateCardContext`, `TemplateCardPhrases`, and
  `TemplateCardPicker`. The picker owns option keys and order, Empty last, duplicate-title paths,
  selection fallback, descriptions, and invalid-card warnings.
- Route `ProcessingView`, `show_new_reference_dialog`, and `show_log_entry_dialog` through the picker
  while keeping the existing public controls and dialog keys stable.
- Add `LOG_CARD_EMPTY` and fix the log entry picker to describe Empty as a log entry with no starter
  body. Add a regression test for that wording.
- Remove the retired `InboxView`, its exclusive private helpers, `scan_warning`/`scan_warning_title`,
  and `TestInboxView`, after re-running the reference proof. Keep `WelcomeView` and `SessionNotice`,
  which `ui/app.py` still uses.
- Add architecture tripwires: no label-key mutation outside `core/labels.py` and
  `core/frontmatter.py`, and no template-card option helper outside the shared component.
- Delete the duplicated private helpers. No compatibility shims.

## Capabilities

### New Capabilities

None. This is a behavior-preserving refactor. `skip_specs: true` is declared in `.openspec.yaml`.

### Modified Capabilities

None. `note-log` already requires the log picker to list Empty and create a bare entry; the wording
correction makes the label match that existing requirement. `template-cards` already requires valid
cards plus Empty in every picker. No requirement text or scenario changes.

## Impact

- Core: `core/labels.py`, `core/editing.py`, `core/processing.py`, `core/templates.py`,
  `core/vault/pages.py`, `core/vault/naming.py`, and `core/vault/service.py`.
- UI: new `ui/components/template_cards.py`; `ui/views/processing.py`, `ui/views/inbox.py`,
  `ui/app.py`, and `ui/strings.py`.
- Tests: a new `tests/core/test_labels.py`, picker tests, updates to the existing editing,
  processing, pages, naming, processing-view, inbox-view, and app tests, plus
  `tests/core/test_architecture.py`.
- Public API: additive `PageLabels.apply_to` and `TemplateCardPicker`; **BREAKING** remove the
  unused `InboxView` class. `WelcomeView` and `SessionNotice` remain. No user-visible behavior
  changes from that removal.
- Release classification: this is a pre-1.0 Python API removal. Record a changelog migration note and
  choose the version at archive per `AGENTS.md` section 5.3.
- User-visible behavior: the log picker's Empty wording is corrected. All other behavior is
  unchanged.
- No dependencies, vault-format, settings, schema, or CLI changes. Offline and cross-platform
  behavior stay unchanged.
