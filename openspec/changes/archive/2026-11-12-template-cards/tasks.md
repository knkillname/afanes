# Tasks

## 1. Template card catalog

- [x] 1.1 Add `TemplateCard`, `TemplateCardIssue`, and `TemplateCardCatalog` in `src/afanes/core/template_cards.py`; support a bundled root and a vault folder, valid cards, issues, and deterministic ordering; verify unit tests cover parsing, title fallback, optional description, empty body, refused level-1 heading, refused status/due date, malformed frontmatter, and ordering.
- [x] 1.2 Add the seven bundled card files under `src/afanes/template_cards/` using the metadata and starter bodies in `design.md`; verify `TemplateCardCatalog.bundled()` returns exactly seven valid cards with the expected titles and categories.
- [x] 1.3 Add the template-card domain errors to `src/afanes/core/errors.py` and use them for invalid bundled content and card write failures; verify tests assert the failure messages and that one invalid user card does not raise.
- [x] 1.4 Add strict NumPy-style docstrings to every new public module, class, method, and property; verify `hatch check` passes for the new module and `tests/core/test_architecture.py` still passes.
- [x] 1.5 Add `docs/reference/template-cards.md` covering the `templates/` folder, the card format, `title`/`description` fallbacks, Empty, invalid-card warnings, and the seven seeded cards; add it to the docs toctree and verify `hatch run docs:build` passes.

## 2. Vault layout and seeding

- [x] 2.1 Add `TEMPLATES_DIRECTORY` to `src/afanes/core/vault/snapshot.py` and skip it in `Vault._note_paths` case-insensitively; verify tests show a card is not scanned, a `Templates/` case variant is excluded, a card name can belong to a note, and a reference to a card name is unresolved.
- [x] 2.2 Add `Vault.templates_directory()` using the existing case-insensitive directory lookup without creating the folder; verify tests cover a missing folder, a canonical folder, and an existing case variant.
- [x] 2.3 Add `written_cards` to `VaultCreation` and write the seven bundled cards during `Vault.create_directory` after the guide and starter notes, using atomic writes; verify creation tests cover the seven files, blank-vault creation, edited cards, deleted cards not restored, and a partial card failure that names the failing card and the cards already written.
- [x] 2.4 Update `docs/reference/vault-format.md` and `docs/reference/templates.md` for the reserved `templates/` folder, the seven seeded cards, the note exclusion, and the breaking change for an existing `templates/` folder with ordinary notes; verify `hatch run docs:build` passes.
- [x] 2.5 Update the guide note at `src/afanes/templates/_guide/en/reference/Getting started.md` with a short reference-template section; verify the guide and creation tests pass and the guide remains a single uncategorized reference.

## 3. Processing core

- [x] 3.1 Add `category` and `scaffold` to `ProcessingPlan`, validate them against the outcome, and update `processed_text` to set the category and append the scaffold with the document's newline style; verify unit tests cover reference and Later plans, Empty plans, capture-text preservation, unknown-key preservation, and invalid combinations.
- [x] 3.2 Update `VaultProcessing.plan_processing` to accept an optional `TemplateCard`, use `general` for Empty, choose the category folder, keep the existing collision checks, and compute the processed hash; verify vault-processing tests cover a card category, Empty/general, an empty card body, a project rejecting a card, a missing card, and an unchanged capture.
- [x] 3.3 Update `ProcessingState.begin` to load the catalog in a worker thread and retain the valid cards and issues, and update `build_plan` to pass the selected card; verify state tests cover a valid catalog, a missing folder, invalid-card issues, card selection, and Empty.
- [x] 3.4 Update the existing processing tests that assert uncategorized Reference and Later outcomes; verify the full processing test suite passes.
- [x] 3.5 Verify `hatch check` passes for the changed core modules and that no `AppState` field was added; run the architecture gate.

## 4. Processing wizard

- [x] 4.1 Add the Template dropdown and description/summary to `ProcessingView`, visible for Reference and Later, populated with the valid cards plus Empty; verify view tests cover visibility, selection, Empty, invalid-card warning, and the category/starter-body preview.
- [x] 4.2 Add the processing template strings to `src/afanes/ui/strings.py`; verify `hatch check` passes and no copy is hard-coded in the view.
- [x] 4.3 Verify applying a plan leaves the success panel visible, does not open the page editor, and does not change the open page; add a view or state test for the success state and the unchanged page.
- [x] 4.4 Update `docs/guide/processing.md` for the template picker, Empty/general, starter-body append, invalid-card warning, and the no-edit-mode finish; verify `hatch run docs:build` passes.
- [x] 4.5 Update or replace the Processing screenshot so it shows the Template field; verify the rebuilt page displays the new image.

## 5. Browser creation

- [x] 5.1 Add `VaultSession.template_cards()` to read the vault catalog in a worker thread and return valid cards plus issues; verify state tests cover a missing folder, valid cards, and invalid-card issues.
- [x] 5.2 Add `PageEditorState.load(path, *, editing=False)` and `PageNavigator.create_reference(name, category, scaffold)` with the commit guard, atomic write, scan, query clearing, edit-mode load, and history push; verify navigation tests cover a card create, Empty/general, edit mode, blank name, collision, scan failure, and a dirty current page.
- [x] 5.3 Add the New action to the References section in `WorkspaceView` and the `on_new_reference` callback; verify view tests cover visibility only in References, disabled state while busy, and callback invocation.
- [x] 5.4 Add `AfanesApp.show_new_reference_dialog` with the name field, template dropdown, description, invalid-card warning, and inline errors, and wire it to the shell; verify app tests cover a valid create, Empty, blank name, collision, invalid cards, edit-mode opening, and cleared search.
- [x] 5.5 Add the browser dialog and button strings to `src/afanes/ui/strings.py`; verify `hatch check` passes and no copy is hard-coded in the view or shell.
- [x] 5.6 Update `docs/guide/references-and-categories.md` and `docs/guide/workspace.md` for the New action, the dialog, Empty/general, immediate creation, and edit mode; verify `hatch run docs:build` passes.

## 6. Integration and gates

- [x] 6.1 Run `hatch check` and fix every lint, format, and Pyrefly issue.
- [x] 6.2 Run `hatch test --cover` and confirm coverage is at least 85% and the template-card and processing modules are at least 90%.
- [x] 6.3 Run `hatch run docs:build` and confirm it passes with warnings as errors.
- [x] 6.4 Run `openspec validate --all --strict` and `openspec doctor`; confirm both pass.
- [x] 6.5 Run the two compliance greps from `AGENTS.md` section 6.1 and confirm both exit with no output.
- [x] 6.6 Run the architecture gate in `tests/core/test_architecture.py` and confirm it passes.
- [x] 6.7 Smoke-test the feature: create a vault and confirm the seven cards; add a custom card; process a capture with a card and with Empty; create a reference from the browser with a card and with Empty; confirm processing stays on the success panel, the new browser note opens in edit mode, invalid cards are named, and no card appears in the browser.
- [x] 6.8 Confirm an existing `templates/` folder with ordinary notes is excluded from the browser and that the exclusion is documented as a breaking change.

## Workflow follow-up

- Archive the change after the implementation and review requirements are satisfied.
- Run the post-archive release step: update `CHANGELOG.md`, decide the version bump, update `README.md` and `docs/`, rerun the gates, and commit the archive, synced specs, and release artifacts together.
