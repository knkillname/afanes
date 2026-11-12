# Release readiness

This file is the single definition of the first usable MVP and the evidence
required before version `1.0.0`. `AGENTS.md` section 5.3, `CHANGELOG.md`, and
`README.md` point here instead of restating the criteria.

## `1.0.0` definition

`1.0.0` ships when a fresh-machine user can open a vault, capture a thought,
clarify it, browse the vault, and review due work without hand-editing a
Markdown file. Every flow below must pass its automated evidence and, where the
evidence can only be produced on a target operating system, its manual check.

## Per-flow checklist

| Flow | Capability | Requirement | Automated evidence | Manual evidence |
| --- | --- | --- | --- | --- |
| Open a vault | `vault-selection` | Any existing directory is a vault; the chosen vault is remembered; opening is read-only | `tests/core/test_vault.py::TestVaultOpen`, `tests/ui/test_state.py::TestChooseVault` | Launch a packaged build, choose an empty directory, reopen it after restart |
| Capture | `inbox-capture` | Capture writes a note into the inbox; the filename comes from the first non-blank line | `tests/core/test_vault_pages.py::TestCaptureNote`, `tests/ui/test_inbox_view.py` | Type a thought in a packaged build and confirm the Markdown body matches the typed text byte for byte |
| Clarify | `processing` | Processing is explicit and confirmed; the outcome set is fixed; apply writes then moves atomically | `tests/core/test_processing.py`, `tests/core/test_vault_processing.py`, `tests/ui/test_processing_view.py` | Clarify one capture into a project and confirm the project body contains its step |
| Browse | `vault-browsing`, `project-overview` | The browser groups every parsed note; project rows report status, due date, open steps, and next step | `tests/core/test_search.py`, `tests/ui/test_workspace_view.py`, `tests/ui/test_projects_view.py` | Search a title and open the result from the browser |
| Review | `guided-review` | Review shows the pending count; a due step can be done, postponed, or delegated | `tests/core/test_search.py`, `tests/ui/test_review_view.py` | Open a due project, complete its next step, and confirm the review count drops |
| Edit safely | `note-editing`, `note-identity` | Autosave and commit preserve the draft; external edits stop the write; renames maintain references | `tests/core/test_vault_pages.py`, `tests/core/test_vault_naming.py`, `tests/ui/test_page_view.py` | Edit a page beside an external editor and confirm the conflict banner appears |

## Platform matrix

Each artifact is built and checked on its own operating system. Run only the
command for the machine that produces the artifact.

| Platform | Build | Offline start | Capture and compare | External-edit refresh | Evidence |
| --- | --- | --- | --- | --- | --- |
| Linux | `hatch run flet build linux --build-version "$(hatch version)"` | Launch `build/linux/` with networking unavailable | Capture a note and compare its bytes with a source run | Edit the file externally and confirm the workspace refresh | Verified locally at `0.5.1` |
| macOS | `hatch run flet build macos --build-version "$(hatch version)"` | Launch `build/macos/` with networking unavailable | Capture a note and compare its bytes with a source run | Edit the file externally and confirm the workspace refresh | Maintainer check pending |
| Windows | `hatch run flet build windows --build-version "$(hatch version)"` | Launch `build/windows/` with networking unavailable | Capture a note and compare its bytes with a source run | Edit the file externally and confirm the workspace refresh | Maintainer check pending |

Record each manual result by replacing `pending` with the version, date, and
machine. A check that has not run stays pending; it never becomes a silent
assumption.

## Constraints (not gaps)

- Artifacts are unsigned local builds. Distribution is limited to local builds
  for now; package-index publication and GitHub release publishing are later
  decisions. Code signing, notarization, and auto-update remain out of scope.
- The first development desktop run may fetch the Flet client once as
  provisioning; a packaged build bundles the client and starts offline.
- There is no cloud sync, account, telemetry, or hidden network call.

## Version path

1. `0.6.0` is the checkpoint that groups the remaining work: the macOS and
   Windows manual checks above, the cross-reference updates in this change, and
   any documentation drift those checks expose. The maintainer confirms the
   checkpoint when its grouped work is merged and the automated gates pass.
2. `1.0.0` follows only when every checklist row and every platform cell is
   green. The maintainer confirms the transition after reviewing the recorded
   evidence in this file.
3. An archive that completes neither condition keeps its changelog entry under
   `Unreleased` and does not bump the version.
