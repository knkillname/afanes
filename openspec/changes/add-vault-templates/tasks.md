# Tasks

## 1. Template catalog in core

- [x] 1.1 Add `src/afanes/core/templates.py` with a frozen `VaultTemplate` value object (identifier, label, description) and a `TemplateCatalog` that reads bundled content through `importlib.resources`, with `BASE_LOCALE` as a public constant; verify a unit test reports `personal`, `work`, `study` in that order
- [x] 1.2 Implement locale resolution (requested locale, then base locale) and an unknown-identifier refusal that names the valid identifiers; verify tests cover a present locale, a missing locale, and an unknown identifier
- [x] 1.3 Add template errors to `src/afanes/core/errors.py` for an unknown template, an invalid bundled tree, and a failed note write; verify tests assert each error type and that its message names the offending template or note
- [x] 1.4 Add a catalog summary (identifier, label, description, note count) that the picker and the command line both read; verify a test reports a non-zero note count for every entry and that no summary call writes a file

## 2. Bundled-tree validation

- [x] 2.1 Implement validation that every bundled note parses, stems are unique across the template and the guide, stems pass the cross-platform filename policy, every internal reference resolves inside the tree, and folder placement matches note type and category; verify one synthetic fixture per rule is refused with a message naming the offending note
- [x] 2.2 Refuse trees containing a note under `inbox/` or `trash/`, and a template that declares the reserved guide stem; verify synthetic fixtures for both
- [x] 2.3 Compare locale trees of one template for identical shape (projects, references, and step counts) and refuse a mismatch; verify a synthetic fixture with a missing project and one with a missing step are both refused

## 3. Bundled content

- [x] 3.1 Write `src/afanes/templates/_guide/en/reference/Getting started.md` explaining the vault, the three note types, category labels, and how a capture becomes a project; verify it parses with `type: reference`, carries no category or status, and contains no prohibited vocabulary
- [x] 3.2 Author the `personal` template (life-administration projects, `person` and `place` reference labels, one realistic open project per area) and verify the validation suite accepts it
- [x] 3.3 Author the `work` template (shared outcomes, `team` and `process` labels, fewer projects with more detailed steps) and verify the validation suite accepts it and that its label set differs from `personal`
- [x] 3.4 Author the `study` template (course and research projects, `topic` and `source` labels) and verify the validation suite accepts it and that its project shape differs from the other two
- [x] 3.5 Add one parametrized suite over every `(template, locale)` pair asserting the inert-content rules: no due dates, no plan or actual dates, no step owners, no captures, and every open project has at least one unchecked step; verify it fails when a date or owner is added to a copy of a tree
- [x] 3.6 Give each template's main project a short intro about that specific example only, without restating the model the guide already explains; verify by review that no template intro repeats guide content

## 4. Creation applies the content

- [x] 4.1 Extend `Vault.create_directory` with an optional template identifier and locale, writing the guide note plus the template's notes after seeding, and extend `VaultCreation` with `written_notes` and `template`; verify core creation tests report the notes in creation order and the template used
- [x] 4.2 Order creation so the bundled tree is validated before any directory is created, and verify that an invalid tree leaves the target path absent or unchanged
- [x] 4.3 Write each note through `contained()` and `write_text_atomic`, creating parent folders on demand; verify a test asserts written files stay inside the vault and that a note in a nested category folder lands at `reference/<category>/`
- [x] 4.4 Report a mid-write failure by naming the failing note and the notes already written, leaving written notes in place and not remembering the vault; verify the test asserts the raised error message, the surviving files, and unchanged preferences
- [x] 4.5 Update the creation tests that currently assert a created vault has no files, and assert instead that it holds the guide note only; verify `tests/core/test_vault.py` and `tests/core/test_integration.py` pass
- [x] 4.6 Verify end to end that a vault created from each template scans cleanly and reports a zero review count through the review planner

## 5. Interface

- [x] 5.1 Add centralized copy for the template picker, its descriptions, the extended preview, and the template failure messages to `src/afanes/ui/strings.py`; verify no copy is added inline in a view or the app shell
- [x] 5.2 Pass the selected template through the controller's creation command to core, reading the catalog summary through `asyncio.to_thread`; verify controller tests cover a blank creation, a templated creation, and a catalog read failure
- [x] 5.3 Add the template selector to the new-vault dialog with no template preselected, and extend the preview to name the folders and the number of notes; verify app tests cover the default selection, a template selection, and that cancelling writes nothing
- [x] 5.4 Make a failed catalog read degrade to no-template creation with an inline explanation instead of a blocked or broken dialog; verify the corresponding app test
- [x] 5.5 Verify the same dialog serves the welcome state and the change-vault action, and that a templated second vault leaves the first unmodified

## 6. Command line

- [x] 6.1 Add `--template ID` to `afanes vault create`, report the template used and the notes written, and verify success output and exit code `0` in `tests/cli/test_main.py`
- [x] 6.2 Refuse an unknown identifier by naming the valid ones, writing nothing, leaving preferences unchanged, and exiting `1`; verify the command test
- [x] 6.3 Add the `afanes vault templates` action rendering the catalog summary; verify it exits `0`, requires no vault, opens no interface, and writes nothing

## 7. Integration checks

- [x] 7.1 Confirm the architecture gate still passes: no new module-level functions outside the allowlisted modules, `core/` free of interface imports, and an acyclic import graph; verify with `hatch check`
- [x] 7.2 Verify the bundled trees ship in the wheel and resolve through `importlib.resources`; verify by building the wheel and asserting every catalog entry resolves with at least one note
- [x] 7.3 Run the full gate set and record the exact commands: `hatch check`, `hatch test --cover` with at least 85% coverage, `openspec validate --all --strict`, and the prohibited-vocabulary check

## Workflow follow-up

- Archive the change once review requirements are satisfied.
- Update `CHANGELOG.md` during the release workflow, naming the templates and the guide note as user-facing outcomes.
- Revisit the documentation deferral recorded in the proposal: README and screenshots were intentionally left unchanged, so decide at release whether the new capability is documented before or after it is used in practice.
