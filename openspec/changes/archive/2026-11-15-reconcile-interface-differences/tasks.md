# Tasks

## 1. Reconcile the documents

- [x] 1.1 Replace the two numeric difference counts in `RELEASE.md` with references to the interface
  standard's table; verify `grep -n "five declared Flet differences\|five bounded Flet differences"
  RELEASE.md` returns no matches.
- [x] 1.2 Replace the numeric count in `AGENTS.md` with a reference to the interface standard's table,
  and add the rule that the table is the single list and no other document restates the count; verify
  `grep -n "five Flet toolkit limits" AGENTS.md` returns no match and the new rule is present.
- [x] 1.3 Review the `interface-theme` delta against the main requirement: the header matches exactly,
  every existing scenario is retained, and the text points to the standard's table; verify
  `openspec validate --all --strict` passes.

## 2. Verification

- [x] 2.1 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass with no
  warnings or failures.
- [x] 2.2 Run `hatch check` and `hatch test --cover`; verify both pass. No documentation build is
  required because no file under `docs/` changes.
- [x] 2.3 Run the vocabulary greps, `git diff --check`, and the tracked-`.mo` check; verify no
  prohibited matches, a clean diff, and no tracked compiled catalogs.

## Workflow follow-up

- Archive the change after review; the archive syncs the `interface-theme` delta into the main spec.
- Post-archive release: no version bump, no changelog entry, README and docs no change required; record
  the correction in the release report.
