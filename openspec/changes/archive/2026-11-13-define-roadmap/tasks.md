# Tasks

## 1. Update the release record

- [x] 1.1 Update the `RELEASE.md` introduction to say the file holds the `1.0.0` definition, the platform evidence, the version path, and the candidate themes; verify the paragraph still points to `AGENTS.md` section 5.3, `CHANGELOG.md`, and `README.md`.
- [x] 1.2 Replace the version path with the current state and the durable rule: `0.7.0` is current, the `0.6.0` checkpoint is retired, a completed milestone that includes the queued breaking UI changes is a MINOR release, an archive that completes no milestone stays under `Unreleased`, and `1.0.0` still requires every checklist row and platform cell to be green; verify `grep -n '0.6.0' RELEASE.md` returns no output and the section names `0.7.0`, the milestone rule, and the `1.0.0` gate.
- [x] 1.3 Add the candidate-themes section: HIG waves 3, 4, 5, and 7 plus an empty conformance baseline; interface internationalization; and note reminders. State that none is in the `1.0.0` checklist, that each needs an approved change, and that the section is not ordered or dated. Link to `docs/develop/interface-standard.md` for the HIG wave detail and the five Flet bounded differences instead of copying them; verify the section contains no dates, priorities, or future version numbers and that the link target exists.
- [x] 1.4 Add the open-decisions subsection: whether any candidate theme moves into `1.0.0`; which languages i18n targets; whether reminders need native notifications or OS-level scheduling; and whether a reminder key changes the vault schema. Verify all four are listed as open, not decided.
- [x] 1.5 Add the not-planned subsection: signing, notarization, auto-update, and publishing as non-goals; docs-site deployment, versioned docs, the export capability, and a persistent reference cache as deferred; and the SQLite index, `afanes index`, and `afanes doctor` as reversed plans, citing the `AGENTS.md` rule that adding them requires an approved change. Verify the three categories are distinct and no item is presented as scheduled.
- [x] 1.6 Verify the `1.0.0` definition, the per-flow checklist, and the platform matrix are unchanged by comparing `git diff RELEASE.md`; confirm no checklist row and no platform row changed.

## 2. Record the change

- [x] 2.1 Add one `Unreleased` entry under `Changed` that names the `define-roadmap` change, the roadmap record, and `README: no change required` / `Docs: no change required`; verify `git diff CHANGELOG.md` shows exactly one new bullet in that section and no other changelog edit.

## 3. Integration checks

- [x] 3.1 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass with the new change present.
- [x] 3.2 Run `hatch check` and `hatch test --cover`; verify the type and style gates pass and total coverage stays at or above 85%.
- [x] 3.3 Run the two vocabulary compliance greps from `AGENTS.md` section 6.1; verify both exit 1 with no output.
- [x] 3.4 Confirm the diff is documentation-only: `git status --short` and `git diff --name-only` list the change artifacts, `RELEASE.md`, and `CHANGELOG.md`, with no `src/`, `tests/`, dependency, or `docs/` changes. If a `docs/` file did change, run `hatch run docs:build` and fix any warnings before continuing.
- [x] 3.5 Review the final `RELEASE.md` against the proposal and design: the `1.0.0` gate is untouched, the themes are candidates rather than commitments, the HIG detail points to its owner, and the version rule matches the release workflow.

## Workflow follow-up

- Archive the change after the maintainer approves and the tasks are complete.
- Run the post-archive release workflow. Keep the changelog entry under `Unreleased` unless a coherent milestone completes, and record the README and docs status.
- Do not start any candidate theme without a new approved change.
