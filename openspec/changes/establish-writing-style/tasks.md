# Tasks

## 1. Prepare the tests and the action inventory

- [x] 1.1 Replace every test assertion that compares rendered text with a hardcoded copy phrase by the matching `afanes.ui.strings` or `afanes.cli.strings` constant; verify `grep -rn 'Empty creates a reference\|No description\.\|could not be read and will be skipped' tests` returns no literal assertions and `hatch test tests/ui` passes before any copy changes.
- [x] 1.2 Audit each control label in `src/afanes/ui/views`, `src/afanes/ui/components`, and `src/afanes/ui/app.py` against its handler and record the initiating actions that open a dialog, form, confirmation, or native picker; verify the audit names every initiating control and distinguishes it from the affirmative control inside that surface.
- [x] 1.3 Classify every existing constant and mapping in `src/afanes/ui/strings.py` and `src/afanes/cli/strings.py` as header-case or sentence-case, and record the two name sets as the initial classification for the gate; verify every module-level string constant and mapping name appears exactly once across the sets.

## 2. Migrate the interface catalog

- [x] 2.1 Rewrite headings, view and destination titles, section labels, tooltips, and control labels in `src/afanes/ui/strings.py` to header capitalization, including mapping values such as the workspace sections, processing outcomes and statuses, review kinds, project groups, and page types; verify a diff review shows no field label or prose converted to header case.
- [x] 2.2 Rewrite field labels, hints, dialog bodies, banners, status messages, validation and error messages, and helper-built text to sentence capitalization with no final period, and replace every first- or second-person pronoun with neutral phrasing; verify no string in the catalog ends with a period and the four former pronoun strings read neutrally.
- [x] 2.3 Replace each remaining straight apostrophe with U+2019 and each three-dot ellipsis with U+2026; verify `grep -n "Today's\|page's" src/afanes/ui/strings.py` returns no output and a scan of the catalog finds only the single-character ellipsis.
- [x] 2.4 Add an ellipsis to every audited initiating action, including the actions that open the new-vault, change-vault, new-reference, rename, trash, plan-date, owner, asked-by, due-date, processing, review, and log-entry surfaces, and remove the ellipsis from the search placeholder; verify every string ending in `…` is an action in the audited set and no affirmative in-dialog control carries one.
- [x] 2.5 Rewrite `src/afanes/cli/strings.py` to the same rules, keeping command names and metavariables lowercase and command examples literal; verify `afanes vault --help` renders capitalized prose descriptions without final periods and `hatch test tests/cli` passes.

## 3. Add the copy gate

- [x] 3.1 Create `tests/ui/test_copy.py` with a catalog reader that collects module-level string constants and mapping values from both copy modules, plus the `HEADER_CASE` and `SENTENCE_CASE` classification sets from task 1.3; verify a completeness test asserts the sets are disjoint and cover every collected name.
- [x] 3.2 Add the mechanical checks to `tests/ui/test_copy.py` for straight apostrophes, three-dot ellipses, trailing periods, and first- or second-person pronouns as whole words; verify one focused test per rule fails on a fixture string that breaks it and passes on a conforming string.
- [x] 3.3 Add the header-capitalization check: flag a lowercase first or last word, a lowercase word of four or more letters outside the short-word list, a lowercase hyphen part, and an uppercase short word in the middle; verify focused tests cover each violation and that field labels and prose are not measured by this rule.
- [x] 3.4 Add the sentence-capitalization check: every sentence-case constant starts uppercase unless it starts with a placeholder or is a literal command name or value; verify a focused test fails on a lowercase sentence-case string and passes on the real catalog.
- [x] 3.5 Add the ellipsis check and the `ELLIPSIS_ACTIONS` set from task 1.2: every `…` string is in the set, every set member ends with `…`, and no member is a sentence-case field label; verify focused tests cover both directions and that the gate reports the offending constant by name.
- [x] 3.6 Verify `tests/ui/test_copy.py` passes on both catalogs with no baseline and that `hatch test tests/ui/test_copy.py` reports the expected number of checks; confirm the test module is the only new gate and the visual conformance gate is unchanged.

## 4. Update the durable documents

- [ ] 4.1 Replace the sentence-case transition note in `AGENTS.md` section 4.6 with the final rule: header capitalization for headings and short control labels, sentence capitalization for field labels and prose, no final period, ellipses only for further input, neutral tone, typographic apostrophes and ellipsis, and the copy gate; verify the section no longer mentions a future writing-style wave.
- [ ] 4.2 Add a writing-style section to `docs/develop/interface-standard.md` with the capitalization rules, the period, ellipsis, tone, and typography rules, the copy-gate description, and its manual-review limit; add writing style to the conformance levels and mark wave 3 landed in the migration list; verify the page states that the copy gate has no baseline.
- [ ] 4.3 Sweep `docs/` for quoted UI labels changed by this work, including the guide pages for first vault, capture and review, inbox, log, pages and editing, browser mode, and the interface standard; verify each quoted label matches the catalog and `hatch run docs:build` passes with no warnings.
- [ ] 4.4 Add one `Unreleased` entry under `Changed` naming the `establish-writing-style` change, the writing-style rules, the copy gate, the visible label changes, and the screenshot deferral to wave 7; include `README: no change required` and `Docs: updated`; verify no version bump.

## 5. Integration checks

- [ ] 5.1 Run `hatch check` and `hatch test --cover`; verify the type and style gates pass and coverage stays at or above 85%.
- [ ] 5.2 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass.
- [ ] 5.3 Run both vocabulary compliance greps from `AGENTS.md` section 6.1; verify both exit 1 with no output.
- [ ] 5.4 Run `git diff --check` and `git status --short`; verify the diff contains only the two copy catalogs, the new copy gate, test updates, `AGENTS.md`, `docs/develop/interface-standard.md`, the swept guide pages, `CHANGELOG.md`, and this change's artifacts, with no theme, token, view-layout, dependency, vault, or schema change.
- [ ] 5.5 Review the final catalogs against the spec: header case on every heading and short control label, sentence case on every field label and prose line, no final periods, no first- or second-person pronouns, typographic apostrophes, one-character ellipses, and ellipses only on further-input actions.
- [ ] 5.6 Review the final `docs/develop/interface-standard.md` against the gate: the writing-style rules match the implemented checks, the copy gate is separate from the visual baseline, and wave 3 reads landed.

## Workflow follow-up

- Archive the change after the maintainer approves and every task is complete.
- Run the post-archive release workflow; keep the changelog entry under `Unreleased` unless a coherent milestone completes.
- Do not start wave 4, internationalization, or the app icon without a new approved change.
