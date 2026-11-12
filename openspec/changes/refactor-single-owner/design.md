# Design

## Context

See `proposal.md` for motivation. Two repeated operations have several implementations:

| Operation | Current writers |
| --- | --- |
| Editable frontmatter labels | `NormalDraft._write_labels`, `VaultPages.set_status`, `VaultNaming.apply_category_move`, `VaultNaming._write_conversion`, `ProcessingPlan.processed_text`, plus the date insertions in `Vault.new_note_document`, `VaultPages.create_page`, and `TemplateCatalog` |
| Template card options | `ProcessingView._template_options`, `_Shell._reference_template_options`, and the two dialog forms in `ui/app.py` |

The five label writers all use `NoteDocument.with_metadata` for validation, but each decides which
keys exist. Four of them re-encode the type-dependent rules already expressed by
`PageLabels.with_type`. The template pickers duplicate option keys, duplicate-title handling, Empty
ordering, descriptions, and warnings.

Constraints that shape the approach:

- `models <- core <- ui`; `core` never imports Flet or `ui`.
- `PageLabels` already imports `NoteDocument`, so the dependency direction is fixed.
- Views are presentational and must not define module-level helpers or read files.
- Strict NumPy-style docstrings apply to every public member.
- No new dependency, linter, or test runner.
- `core/` modules have a 900-line ceiling. `core/vault/service.py` is at 868 lines and
  `core/templates.py` at 849, so routed code must stay compact.
- The unarchived `vault-schema` change adds `afanes.yaml` acceptance to opening and creation. This
  change writes notes only inside an already-open vault and does not touch vault acceptance,
  adoption, or the schema file.

## Goals / Non-Goals

**Goals:**

- One function owns the label-to-frontmatter mapping.
- One component owns the template card picker mechanics.
- Remove the retired `InboxView` after proving it has no live in-repository call path.
- Preserve parsed note behavior, file format, public view controls, dialog keys, and user workflow.
- Correct the log picker's Empty wording.
- Add objective tripwires so a second implementation cannot quietly return.

**Non-Goals:**

- Canonicalizing guarded state-write transactions.
- Canonicalizing the vault write primitives (`write_page`, `set_status`, `_write_processing`, moves).
- Unifying "today" sources.
- Changing frontmatter keys, note identity, link resolution, processing outcomes, template card
  format, or dialog layout.

## Decisions

### D1: `PageLabels.apply_to(document)` is the label owner

`PageLabels` owns the editable label values and their type rules. Add:

```text
PageLabels.apply_to(document: NoteDocument) -> NoteDocument
```

It copies `document.raw`, sets or removes `type`, `category`, `status`, `due_date`, `asked_by`, and
`date` according to the current note type, and returns `document.with_metadata(raw)`. Validation and
serialization stay in `NoteDocument`.

Why this owner:

- `PageLabels.from_document` already owns the read direction; `apply_to` completes the pair.
- `with_type`, `with_category`, `with_status`, and the date helpers already encode most rules.
- `NoteDocument.with_labels` would require `frontmatter.py` to know `PageLabels`, creating a cycle.

Alternatives considered:

- **Keep the writers and add conformance tests only.** Rejected: the second way remains, and tests
  only catch the divergences someone thought to cover.
- **Move label policy into `NoteDocument`.** Rejected: it mixes parsing with editor policy and
  creates an import cycle.
- **Expose a raw `dict` mutator.** Rejected: callers would continue to decide key presence.

### D2: Preserve existing key positions; append new keys in documented order

`apply_to` starts from the parsed document's raw mapping. Assigning an existing key keeps its
position. Removing a key leaves the remaining order untouched. New keys append in the order
documented by `docs/reference/frontmatter.md`: `type`, `date`, `category`, `status`, `due_date`,
`asked_by`.

Unknown keys keep their positions. The writer does not normalize unknown values. CRLF and body text
are preserved by `NoteDocument`.

The log date identity guard stays in `NormalDraft`: it depends on the filename identity and must
reject a date change through the draft. `apply_to` remains a general label writer for conversions and
processing.

`VaultPages.set_status` builds labels with the requested status directly rather than through
`with_status`, so the existing `with_metadata` validation message is preserved. `ProcessingPlan`
uses `with_type` first and then applies the target status, category, due date, and date, matching the
current outcome rules.

### D3: Route every current label writer, including creation and template dates

The following call sites use `PageLabels.apply_to`:

- `NormalDraft.to_text` (after its log identity guard)
- `VaultPages.set_status`
- `VaultNaming.apply_category_move`
- `VaultNaming._write_conversion`
- `ProcessingPlan.processed_text`
- `Vault.new_note_document`
- `VaultPages.create_page` when supplied text has no date
- `TemplateCatalog` when a bundled note has no date

The last three close the creation paths, so the architecture tripwire can allow only
`core/labels.py` and `core/frontmatter.py`. `frontmatter.py` keeps parsing and validation;
`labels.py` keeps the editing policy.

### D4: One `TemplateCardPicker`, context-specific phrases

Add `ui/components/template_cards.py`:

```text
TemplateCardContext    REFERENCE | PROCESSING | LOG
TemplateCardPhrases    label, empty, description, warning, option formats
TemplateCardPicker     dropdown, description, warning, refresh, selected_card
```

The picker owns:

- option keys (`card:<relative-path>`)
- deterministic card order and Empty last
- duplicate-title path suffixes
- selection normalization when the catalog changes or a card disappears
- description and no-description text
- invalid-card warning visibility and text
- control keys derived from a prefix

Contexts keep copy differences explicit. `REFERENCE` and `PROCESSING` may keep their existing
constants even where the text is currently equal; `LOG` uses log-specific Empty and description
strings.

Alternatives considered:

- **One generic dialog for reference and log creation.** Rejected: the surrounding forms, submit
  actions, and labels differ. Share the picker, not the whole dialog.
- **A global option registry.** Rejected: more indirection than the three real contexts need.
- **Keep the view helpers and share only the text formatter.** Rejected: the duplication is the
  option assembly and refresh behavior, not just the string.

### D5: Preserve view and dialog surfaces

`ProcessingView` keeps public `template`, `template_description`, and `template_warning` attributes as
aliases to the picker controls. Existing tests and the view layout continue to work. The picker
accepts an `on_change` callback so the view can repaint without the component knowing Flet page
state.

The reference and log dialogs keep their existing control keys by passing a prefix such as
`new-reference` or `new-log`. The outer dialog layout and submit actions stay in `ui/app.py`.

The log context adds `LOG_CARD_EMPTY = "Empty - no starter body"` and uses it for the Empty option.
A regression test opens the log creation dialog and asserts the option does not mention a reference
category.

### D6: Architecture tripwires

Extend `tests/core/test_architecture.py`:

1. **Label keys have one writer.** An AST check rejects assignment or `pop` of `type`, `category`,
   `status`, `due_date`, `asked_by`, or `date` on a mapping subscript outside `core/labels.py` and
   `core/frontmatter.py`. This is intentionally blunt; `frontmatter.py` is the parser/normalizer.
2. **Template option helpers have one owner.** No module defines `_template_options`,
   `_template_option_text`, `_reference_template_options`, or `_reference_template_text` outside
   `ui/components/template_cards.py`.

Keep the existing review-entry and inbox-entry processing tests; add a view-level assertion that the
picker options are populated after entering processing from review if coverage is missing.

### D7: Sequence and commit strategy

The two workstreams touch disjoint files. Implement and commit them separately inside the same
change:

1. label characterization tests
2. `PageLabels.apply_to` and the label writer routes
3. label architecture tripwire
4. template picker component and unit tests
5. processing view and dialog routes, including the log wording fix
6. template helper tripwire
7. retired `InboxView` reference proof and removal, with its changelog migration note
8. integration gates

Each task must be green before the next. Do not add compatibility delegators for the removed private
helpers.

### D8: Remove retired `InboxView` after a repository-reference proof

Before deleting anything, prove the class has no live in-repository call path:

- An AST reference count shows `InboxView` has zero production references outside
  `ui/views/inbox.py` and eleven references in `tests/ui/test_inbox_view.py`.
- `ui/app.py` uses only `WelcomeView` (two references) and `SessionNotice` (one reference) from the
  module. `_Shell.render` builds `WorkspaceView` whenever a vault is open and never constructs
  `InboxView`.
- No reference appears in `pyproject.toml`, `src/main.py`, `src/afanes/__main__.py`, `docs/`,
  `README.md`, or `openspec/specs/`.
- The archived `add-review-workspace` design says the old `InboxView` split was retired as a screen.

Removal scope:

- `InboxView` itself and its exclusive private methods.
- Imports used only by it: `Path`, `VaultFailure`, `VaultNote`, and `afanes.ui.views.page`.
- `scan_warning_title` and `scan_warning` in `ui/strings.py` after confirming the first has no
  remaining caller and the second already has none.
- `TestInboxView` and its exclusive test helpers, constants, and imports.
- Keep `WelcomeView`, `SessionNotice`, and shared imports such as `Banner`.

Why now: the tests currently protect a second implementation. Removing it shrinks the test surface to
live code and prevents a future fix from landing in the retired view.

Alternatives considered:

- **Keep it with a deprecation period.** Rejected: prior refactors remove dead APIs without shims, and
  no in-repository caller exists.
- **Delete all of `ui/views/inbox.py`.** Rejected: `WelcomeView` and `SessionNotice` are live.
- **Remove only the tests.** Rejected: the dead class would remain importable and misleading.

Proof boundary: this proves the class is dead in this repository, not that no external code imports
it. The project treats Python APIs as public, so the removal is **BREAKING** and needs a changelog
migration note. It does not change any user-visible workflow.

## Risks / Trade-offs

- **New key order for created notes.** Existing keys keep their positions, but new keys append in a
  documented order that may differ from one current creation path. Parsed values do not change.
  Mitigation: pin the order in `test_labels.py`, compare parsed documents in writer tests, and record
  the normalization in the changelog only if the release notes need it.
- **A label rule differs between writers.** The canonical rules must match reachable behavior.
  Mitigation: characterize the current matrix first, keep the existing editing/processing/pages/
  naming tests, and add a property-based round-trip for `PageLabels`.
- **Status error messages change.** `set_status` currently validates through `with_metadata`.
  Mitigation: build labels directly for that command and test the exception path.
- **Picker integration changes selection behavior.** Mitigation: the component tests cover refresh,
  removed cards, duplicate titles, and Empty last; existing processing-view tests remain.
- **Dialog keys move.** Mitigation: pass key prefixes so `new-reference-template`,
  `new-reference-template-warning`, and `new-log-template` stay stable.
- **Core line ceilings.** `service.py` and `templates.py` are close to 900 lines. Mitigation: keep the
  routed code compact, avoid new public methods on `Vault`/`TemplateCatalog`, and run the architecture
  gate after each route change. If a file crosses the ceiling, extract a small private helper in the
  same module rather than raising the budget.
- **Tripwire false positives.** The label-key check is textual by nature. Mitigation: allow only the
  parser and label owner, document why, and adjust only through this approved change.
- **Public API removal.** `InboxView` is removed even though it is dead in this repository; an
  external importer would break. Mitigation: record the removal and its replacement (the live
  `WorkspaceView` screen) in the changelog migration note and choose the pre-1.0 version at archive
  per `AGENTS.md` section 5.3.

## Migration Plan

No on-disk migration. Vault files, `afanes.yaml`, settings JSON, CLI flags, and note identity are
unchanged. `PageLabels.apply_to` and `TemplateCardPicker` are additive; private helpers are removed
without shims. The one Python API removal is the unused `ui.views.inbox.InboxView`; the changelog
records that the live replacement is the workspace browser. Rollback is per commit: revert the card
workstream, the label workstream, or the dead-code removal independently if a gate fails.

## Open Questions

None. The canonical rule matrix, key order, picker boundaries, and log wording are decided above.
