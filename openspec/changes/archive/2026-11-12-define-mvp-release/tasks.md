# Tasks

## 1. Inventory the milestone

- [x] 1.1 Map each flow in the `1.0.0` definition - open, capture, clarify, browse, review - to its capability, requirement, and covering test; verify every flow has at least one requirement and one automated test named.
- [x] 1.2 List every gap between that map and a fresh-machine walkthrough, with the blocking reason and who can clear it; verify each gap names what it blocks.
- [x] 1.3 Confirm the scope answer that `README.md` already gives - unsigned local builds, no notarization, auto-update, or publishing pipeline - and record it as a constraint rather than a gap; verify the checklist does not silently add them.

## 2. Write the readiness record

- [x] 2.1 Add `RELEASE.md` with the `1.0.0` definition, the per-flow checklist, and the evidence column; verify every checklist line cites a spec and a test or command.
- [x] 2.2 Add the platform matrix with the exact macOS, Linux, and Windows build, offline-start, capture, and refresh checks, naming the machine each runs on; verify the commands match the build section of `README.md`.
- [x] 2.3 Add the explicitly excluded items and the version path: `0.6.0` is the checkpoint for the remaining work, and `1.0.0` follows only when the checklist is green; verify the rule matches `AGENTS.md` 5.8 (new numbering) without restating it.
- [x] 2.4 Record what the `0.6.0` checkpoint groups, what must be true for `1.0.0` after it, and who confirms each step; verify both conditions are stated with evidence.

## 3. Cross-reference and record

- [x] 3.1 Link `RELEASE.md` from the `README.md` build and changelog areas; verify the link resolves and the surrounding text no longer implies platform verification is complete.
- [x] 3.2 Point `AGENTS.md` 5.3 (formerly 5.8) and the `CHANGELOG.md` release policy at the one definition; verify the citation test from `reconcile-repository-guide` resolves every added reference.
- [x] 3.3 Add the `Unreleased` changelog entry naming this change and the readiness record; verify the entry describes the outcome, not the file inventory.

## 4. Integration checks

- [x] 4.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the 6.6 compliance check; verify all pass.
