# Tasks

## 1. Rewrite the release gate

- [x] 1.1 Update the `RELEASE.md` introduction and `1.0.0` definition to say the file holds the unified MVP gate, the platform evidence, the version path, the artifact policy, and the sequence; verify the section no longer describes a first MVP plus separate candidate themes.
- [x] 1.2 Replace the per-flow checklist with the existing six rows plus HIG conformance, internationalization, and note reminders. Each new row must name its future capability, its requirement, the automated evidence its capability change will deliver, and its Linux manual check; verify every row has all five columns and no new row claims evidence that does not yet exist.
- [x] 1.3 Add the HIG row: waves 3, 4, 5, and 7, wave 6 residual folded into wave 7, empty conformance baseline, only the five declared Flet differences, Linux visual and keyboard review, and the SVG app icon dependency; verify the row points to `docs/develop/interface-standard.md` for wave detail.
- [x] 1.4 Add the internationalization row: English and Spanish, UI and CLI copy, validation and error messages, dates and numbers, bundled templates, English documentation, system locale by default, restart-applied override, English fallback; verify the row matches proposal.md and design.md D6.
- [x] 1.5 Add the reminders row: one whole-note reminder per note, recurrence or one-shot, daily/weekday/day-of-month/nth-weekday rhythms, one or more times, Review surface, one catch-up entry per schedule, dismiss/acknowledge, pause rules, optional frontmatter key, schema `2`, courtesy upgrade; verify the row matches design.md D7 and does not promise snooze, end dates, OS notifications, or a playlist.
- [x] 1.6 Replace the platform matrix with Linux as the only 1.0 gate. Add the macOS/Windows documented path (GitHub Releases wheel, `pipx`, `afanes --web`) and the nightly advisory tests and native builds. Native binaries are attached only when that platform's nightly tests and build both pass, are untested at runtime, unsigned, and unsupported; verify no macOS/Windows row claims a 1.0 manual gate.
- [x] 1.7 Add the release-artifacts policy: Linux build, wheel, and qualifying experimental native binaries on the GitHub release; manual attachment for 1.0; no PyPI; unsigned artifacts; verify the policy does not promise code signing, notarization, auto-update, or native support.
- [x] 1.8 Replace the version path with `0.7.0` as current, intermediate `0.x` releases for completed groups, no named future checkpoint, and `1.0.0` only when the whole union is green; verify `grep -n '0.6.0' RELEASE.md` returns no output and no future version is named as a checkpoint.
- [x] 1.9 Add the work sequence: HIG wave 3, HIG wave 4, i18n, reminders, HIG wave 5, HIG wave 7, packaging and Linux evidence; nightly CI starts early and stays advisory; verify the sequence matches design.md D8.
- [x] 1.10 Update the not-planned section: add OS-level reminder notifications, native macOS/Windows support guarantees, PyPI publication, translated documentation, and reminder snooze/end dates; keep the existing non-goals, deferred items, and reversed plans; verify the three categories remain distinct and no item is presented as scheduled.
- [x] 1.11 Verify the existing six rows and their automated evidence are unchanged by comparing `git diff RELEASE.md`; only their manual platform scope may change.

## 2. Update the support documents

- [x] 2.1 Update `README.md` with the platform support statement: Linux native is supported and tested; macOS/Windows use the GitHub Releases wheel and `afanes --web`; experimental native binaries are untested, unsigned, and unsupported; verify the README no longer says a publishing pipeline is absent, while keeping code signing, notarization, and auto-update as non-goals.
- [x] 2.2 Update `docs/develop/releasing.md` with the GitHub release artifact set, the wheel and web path, manual artifact attachment, the nightly advisory workflow, and the Linux-only 1.0 gate; verify the page no longer says GitHub release publishing is not part of the project.
- [x] 2.3 Update `docs/getting-started/install.md` with the source, Linux build, and wheel/web installation paths, the Python prerequisite for the wheel path, and the support boundary; verify the documented commands match the wheel and `afanes --web` behavior.
- [x] 2.4 Update `docs/guide/browser-mode.md` with the wheel installation path for macOS/Windows, the `afanes --web` command, the loopback and single-session rules, and the offline web-client caveat; verify the page does not present Hatch as the only way to start browser mode.
- [x] 2.5 Verify no other `docs/` page still says distribution is limited to local builds, GitHub release publishing is out of scope, or macOS/Windows are required 1.0 gates; describe 1.0-only paths as planned until their changes ship, and record any page that intentionally keeps a historical statement.
- [x] 2.6 Run `hatch run docs:build` and fix every warning; verify the built documentation includes the new platform and artifact statements.

## 3. Record the change

- [x] 3.1 Add one `Unreleased` entry under `Changed` naming the `unify-mvp-gate` change, the unified gate, the Linux-only release evidence, the wheel and GitHub Releases policy, and the advisory nightly builds; include `README: updated` and `Docs: updated`; verify `git diff CHANGELOG.md` shows exactly one new bullet and no version bump.
- [x] 3.2 Verify `hatch version` still reports `0.7.0` and `src/afanes/__about__.py` is unchanged.

## 4. Integration checks

- [x] 4.1 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass with this change present.
- [x] 4.2 Run `hatch check` and `hatch test --cover`; verify the type and style gates pass and total coverage stays at or above 85%.
- [x] 4.3 Run the two vocabulary compliance greps from `AGENTS.md` section 6.1; verify both exit 1 with no output.
- [x] 4.4 Run `git diff --check` and `git status --short`; verify the diff contains only `RELEASE.md`, `README.md`, the three updated docs pages, `CHANGELOG.md`, and this change's artifacts, with no `src/`, `tests/`, dependency, `AGENTS.md`, or `docs/develop/interface-standard.md` changes.
- [x] 4.5 Review the final `RELEASE.md` against proposal.md and design.md: one union gate, no candidate section, Linux-only evidence, the wheel and experimental artifacts, the advisory CI policy, the sequence, and no stale checkpoint.
- [x] 4.6 Review the final README and docs against the gate: the supported platform, the wheel and web path, the experimental binary labels, the offline caveat, and no claim that macOS/Windows are release-gated.

## Workflow follow-up

- Archive the change after the maintainer approves and every task is complete.
- Run the post-archive release workflow. Keep the changelog entry under `Unreleased` unless a coherent milestone completes, and record the README and docs status.
- Do not start HIG wave 3, i18n, reminders, packaging, or CI without a new approved change. The next capability change in the sequence is HIG wave 3.
