# Release readiness

This file is the single definition of the first usable MVP, the platform
evidence required before version `1.0.0`, the version path, and the candidate
themes after the 1.0 gate. `AGENTS.md` section 5.3, `CHANGELOG.md`, and
`README.md` point here instead of restating the criteria.

## `1.0.0` definition

`1.0.0` ships when a fresh-machine user can open a vault, capture a thought,
clarify it, browse the vault, and review due work without hand-editing a
Markdown file. Every flow below must pass its automated evidence and, where the
evidence can only be produced on a target operating system, its manual check.

## Per-flow checklist

| Flow | Capability | Requirement | Automated evidence | Manual evidence |
| --- | --- | --- | --- | --- |
| Open a vault | `vault-selection`, `vault-schema` | A versioned directory with a valid `afanes.yaml` is a vault; an older folder with the five default folders can be adopted explicitly; the chosen vault is remembered; opening is read-only | `tests/core/vault/test_service.py::TestVaultOpen`, `tests/core/vault/test_schema.py`, `tests/ui/test_state.py::TestChooseVault`, `tests/ui/test_state.py::TestAdoption` | Launch a packaged build, choose an empty versioned directory, reopen it after restart; adopt an older folder and confirm only `afanes.yaml` was added |
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

`0.7.0` is the current version. The next bump follows the existing milestone
rule: an archive that completes no milestone keeps its entry under `Unreleased`
and does not bump the version, and a completed milestone that includes the
queued breaking UI changes is a MINOR release. `1.0.0` follows only when every
checklist row and every platform cell is green. The maintainer confirms the
transition after reviewing the recorded evidence in this file.

## Candidate themes after the 1.0 gate

These themes are candidates, not commitments, and they are not ordered. None is
part of the `1.0.0` checklist today; moving one into `1.0.0` requires a change
to this file. Each theme becomes work only through its own approved OpenSpec
change.

### HIG conformance completion

The remaining migration waves are 3 (writing style and a copy gate), 4
(feedback: undo, toasts, banners, overlays), 5 (keyboard and accessibility), and
7 (app identity, placeholder pages, final palette, and an empty conformance
baseline). The wave detail, the five bounded Flet differences, and the baseline
rule live in `docs/develop/interface-standard.md`; that document remains the
owner of HIG conformance.

### Interface internationalization

Locale-aware copy, date and number formatting, and bundled template content.
The target languages, catalog mechanism, runtime language switch, and the
treatment of the command-line copy remain open.

### Note reminders

Recurring schedules for notes, including daily, weekly, monthly, and
nth-weekday patterns; the in-app or native delivery channel; where the schedule
lives; how missed occurrences are caught up; and whether the reminder key
changes the vault schema.

## Open decisions

- Whether any candidate theme moves into `1.0.0`, or all remain after the gate.
- Which languages interface internationalization targets.
- Whether reminders fire only while the application is running or also need
  native notifications or OS-level scheduling.
- Whether a reminder key changes the vault schema, and if so whether it lands
  before or after `1.0.0`.

## Not planned

**Non-goals.** Code signing, notarization, auto-update, and package-index or
GitHub release publishing remain outside the project.

**Deferred.** Docs-site deployment, versioned documentation, the export
capability, and a persistent reference cache are deferred; none has a scheduled
change.

**Reversed.** The SQLite index, `afanes index`, and `afanes doctor` are not
planned. `AGENTS.md` requires an approved change before any of them is added.
