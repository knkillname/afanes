# Release readiness

This file is the single definition of the `1.0.0` MVP gate, the platform
evidence required before that release, the artifact policy, the version path,
and the order in which the remaining work lands. `AGENTS.md` section 5.3,
`CHANGELOG.md`, `README.md`, and `docs/` point here instead of restating the
criteria.

## `1.0.0` definition

`1.0.0` ships when a fresh-machine user can open a vault, capture a thought,
clarify it, browse the vault, and review due work without hand-editing a
Markdown file, and when the interface meets the strict HIG standard, speaks
English and Spanish, and delivers note reminders. These are one gate, not a
first release plus later themes: every row below is required for `1.0.0`.

Each row must pass its automated evidence and its Linux manual check. A row
whose capability change has not landed yet records the evidence that change
must deliver; the row is not green until that evidence exists and the check has
run.

## Unified gate checklist

| Flow | Capability | Requirement | Automated evidence | Linux manual check |
| --- | --- | --- | --- | --- |
| Open a vault | `vault-selection`, `vault-schema` | A versioned directory with a valid `afanes.yaml` is a vault; an older folder with the five default folders can be adopted explicitly; the chosen vault is remembered; opening is read-only | `tests/core/vault/test_service.py::TestVaultOpen`, `tests/core/vault/test_schema.py`, `tests/ui/test_state.py::TestChooseVault`, `tests/ui/test_state.py::TestAdoption` | Launch a packaged build, choose an empty versioned directory, reopen it after restart; adopt an older folder and confirm only `afanes.yaml` was added |
| Capture | `inbox-capture` | Capture writes a note into the inbox; the filename comes from the first non-blank line | `tests/core/test_vault_pages.py::TestCaptureNote`, `tests/ui/test_inbox_view.py` | Type a thought in a packaged build and confirm the Markdown body matches the typed text byte for byte |
| Clarify | `processing` | Processing is explicit and confirmed; the outcome set is fixed; apply writes then moves atomically | `tests/core/test_processing.py`, `tests/core/test_vault_processing.py`, `tests/ui/test_processing_view.py` | Clarify one capture into a project and confirm the project body contains its step |
| Browse | `vault-browsing`, `project-overview` | The browser groups every parsed note; project rows report status, due date, open steps, and next step | `tests/core/test_search.py`, `tests/ui/test_workspace_view.py`, `tests/ui/test_projects_view.py` | Search a title and open the result from the browser |
| Review | `guided-review` | Review shows the pending count; a due step can be done, postponed, or delegated | `tests/core/test_search.py`, `tests/ui/test_review_view.py` | Open a due project, complete its next step, and confirm the review count drops |
| Edit safely | `note-editing`, `note-identity` | Autosave and commit preserve the draft; external edits stop the write; renames maintain references | `tests/core/test_vault_pages.py`, `tests/core/test_vault_naming.py`, `tests/ui/test_page_view.py` | Edit a page beside an external editor and confirm the conflict banner appears |
| HIG conformance | `interface-theme` waves 3, 4, 5, and 7 | Waves 3 (writing style and copy gate), 4 (feedback patterns), 5 (keyboard and accessibility), and 7 (identity, original SVG app icon, symbolic placeholder pages, platform high contrast, final palette) are complete; wave 5 covers the shortcut sheet, Log calendar keys, focusable Review and note rows, post-trash focus, accessible names, live regions, minimum-height text growth, and the rendered 100%/200% layout gate; the residual wave 6 per-view polish is folded into wave 7; empty browser destinations, empty search, empty Trash, and the no-page detail use a symbolic placeholder page; high contrast follows the platform accessibility flag at startup and on resume with 7:1 body text; the conformance baseline is empty; only the five bounded Flet differences listed in the interface standard remain; the app icon is an original SVG asset | Delivered by the wave changes: `tests/ui/test_conformance.py` with an empty baseline, `tests/ui/test_accessibility.py`, `tests/ui/test_large_text.py`, `tests/test_assets.py`, `tests/ui/test_placeholder.py`, and the `tests/render/` layout snapshot and comparator; the manual results are recorded below | Visual and keyboard review of every view in light and dark at the 1024x600 minimum and the 1100 px and 1024 px breakpoints; real Large Text pass at 1024x600 and 1100 px in light and dark; real High Contrast pass at 1024x600 and 1100 px in light and dark |
| Internationalization | `interface-localization` | English and Spanish cover interface copy, CLI copy, validation and error messages, dates and numbers, and the bundled guide and starter templates; documentation stays English; the system locale is the default, an in-app override applies on restart, and missing strings fall back to English | Delivered by the internationalization change: catalog completeness across both locales, locale resolution and fallback, date and number formatting, CLI output, and template rendering | Run the application and the CLI under both locales, switch the override, restart, and confirm copy, dates, and starter templates |
| Note reminders | `note-reminders` | One whole-note reminder per reference, project, or log entry, either one recurrence or one local one-shot, with a stored IANA time zone and one or more times. Six recurrence kinds: daily, selected weekdays, day of month, nth weekday, last day, and last weekday. Due reminders lead Review, most overdue first, with one catch-up entry per schedule; Dismiss writes only `handled` and never changes the body, status, or schedule. A reminder pauses on trash or a finished, cancelled, archived, or deferred status. The Review count refreshes within 15 seconds while the app is open, and the editor offers a searchable zone picker, deadline shortcuts, and removal with Undo. The schedule lives in an optional frontmatter key; the vault format is schema `2` | `tests/models/test_reminder.py` (six kinds, DST, month skips, property bounds), `tests/core/vault/test_reminders.py` (dismissal and conflict guard), `tests/core/test_search.py` (queue order, pause, count, digest), `tests/core/vault/test_schema.py` and `tests/ui/test_state.py` (schema `2`, upgrade, read-only compatibility), `tests/ui/test_review_view.py` and `tests/ui/test_reminder_editor.py` (card, editor, shortcuts), `tests/core/test_localization.py` (relative time and weekday names) | Create one recurrence and one one-shot, confirm the due cards and the single catch-up item, wait for the badge to update without a manual refresh, dismiss and confirm only `handled` changed, trash the note and confirm the reminder pauses, open a writable schema `1` vault and confirm the one-line upgrade, then open a read-only schema `1` vault and confirm browsing works with reminders off |

The HIG wave detail, the bounded Flet differences, and the baseline rule live in
`docs/develop/interface-standard.md`; that document remains the owner of HIG
conformance. The reminder row does not promise snooze, end dates, OS-level
notifications, or more than one schedule per note.

Application icon evidence for `align-app-icon-hig` at `0.14.0` on 2026-11-16
(`Linux tlacoyo x86_64`): `flet_platform_assets.load_source` read the 128x128
SVG at 2048x2048 and `render_icons` produced the Linux hicolor set from 16 to
512 px, the Windows ICO at 16, 32, 48, and 256 px, the macOS app-icon set from
16 to 1024 px, and the web icon set. The render used `derived=True`, matching
Flet's generic `icon.svg` path. Linux, Windows, and web reported no warnings;
macOS reported that the source already has a shaped, near-square tile and kept
it as-is instead of applying the icon grid again. The Linux 16, 32, 64, 128,
and 256 px icons were inspected on light (`#F6F5F4`) and dark (`#241F31`)
backgrounds: the page, fold, and check remain visible at 32 px, and the front
profile is visible at 128 and 256 px. This is an asset-only check: the native
Linux artifact was not built because `clang`, `cmake`, `ninja`, and
`pkg-config` are absent on this machine. The packaged icon remains unverified
until that toolchain produces an artifact.

## Platform matrix

Linux native is the only `1.0.0` release gate. The release workflow builds the
artifact and the maintainer checks it on a Linux desktop, so every manual check
above runs there.

| Platform | Path | Build | Evidence |
| --- | --- | --- | --- |
| Linux | Native desktop build | `.github/workflows/release.yml` on `ubuntu-24.04`; local fallback `hatch run package linux --build-version "$(hatch version)"` | Download the `afanes-release` dispatch artifact for the `1.0.0` commit before the tag, verify its SHA-256, and extract it. Record the run URL, commit, runner image, and checksum. Launch the bundle with networking unavailable; run every Linux manual check in the gate checklist; capture a note and compare its bytes with a source run; edit a file externally and confirm the workspace refresh. After the tag publishes, verify the release assets and their checksums. Re-verified for each release |
| macOS | GitHub Releases wheel, then `afanes --web` | Built by `.github/workflows/release.yml` | Documented path, not a release gate; no manual check is required |
| Windows | GitHub Releases wheel, then `afanes --web` | Built by `.github/workflows/release.yml` | Documented path, not a release gate; no manual check is required |

Record each manual result with the version, date, and machine. A check that has
not run stays pending; it never becomes a silent assumption.

Manual MVP flow evidence at `0.14.0` on 2026-11-16 (`Linux tlacoyo x86_64`):
the packaged dispatch artifact from run `43930562650` opened the versioned gate
vault and remembered it after a restart, captured a thought with a byte-identical
Markdown body, clarified one capture into a project whose body contains its step,
completed a due step and postponed another in Review while the pending count
dropped, and stopped an external edit with the conflict banner while the reload
kept the external line. The fixed artifact from run `44015988044` opened a
browser search result, adopted a legacy folder with the five default folders by
adding only `afanes.yaml` (`schema_version: 2`) and opening it, and remembered
the adopted folder; the same build applied an English interface override only
after restart, returned to the system Spanish locale when the override was
cleared, and rendered the command-line help in both Spanish and English. The
`0.9.0` localization review above remains the evidence for Spanish starter
content, the `0.10.0` reminder record above remains the reminder evidence, and
the HIG row remains backed by the `0.12.0` Large Text, `0.13.0` high-contrast,
and `0.14.0` icon records above with the empty conformance baseline. The complete
gate is re-run on the `1.0.0` artifact before the tag.

Packaging evidence at `0.10.0` on 2026-11-14 (`Linux tlacoyo x86_64`): the
wheel metadata declares `tzdata>=2026.6,<2027` and `tzlocal>=5.4.5,<6`, and an
offline reminder calculation resolves `America/Mexico_City` from the packaged
model. The Flet build staging directory contains `tzdata 2026.6` with the
`America/Mexico_City` zone file and `tzlocal 5.4.5`. The native Linux link step
was not run because `clang`, `cmake`, `ninja`, and `pkg-config` are absent on
this machine; the Flet build stops after staging and before producing an
artifact.

Manual reminder evidence at `0.10.0` on 2026-11-14 (`Linux tlacoyo x86_64`):
the source desktop session passed the recurrence, one-shot, single catch-up,
dismissal preserving body and status, live Review count, pause and restore,
writable schema `1` upgrade, read-only schema `1` browsing with reminders off,
and removal with Undo checks.

Manual date-entry evidence at `0.11.0` on 2026-11-15 (`Linux tlacoyo x86_64`):
the source desktop session passed the English and Spanish labels, the
Monday-first calendar, the Page Date Day, Month, and Year modes with
day-of-month clamping, the read-mode note date action, Log month and year
navigation and headings, the Page Due date, step plan, Processing date, Review
postpone, and reminder one-shot date with the typed time preserved, keyboard
navigation, Cancel, Esc, and outside click, the 1024x600 window, large text,
the full date range, and the no-operating-system-notification check. The
three-click retest passed: the accent contour moves with the clicked day, and
today uses accent text and a bold weight instead of the contour. The `0.12.0`
release carries the same application code; only release metadata,
documentation, and OpenSpec artifacts changed after this check.

Manual accessibility evidence at `0.12.0` on 2026-11-15 (`Linux tlacoyo x86_64`):
the source desktop session passed the real GNOME Large Text setting at a `2.0`
text-scaling factor in four passes: 1024x600 and 1100 px wide, each in light and
dark. The passes covered Inbox, Projects, References, Log, Needs Attention,
Trash, Review, page read and edit, the shortcut sheet, and the day, month, and
year date-picker modes. No clipped text, overlap, or unreachable action was
observed. The rendered 100%/200% snapshot remains the automated check; the
system setting is release evidence and is not simulated by the application. The
`0.13.0` release carries the same application code; only release metadata,
documentation, and OpenSpec artifacts changed after this check.

Manual high-contrast evidence during wave 7 development at `0.13.0` on
2026-11-15 (`Linux tlacoyo x86_64`): the source desktop session passed the real
GNOME High Contrast setting in four passes: 1024x600 and 1100 px wide, each in
light and dark. The passes covered Inbox, Projects, References, Log, Needs
Attention, Trash, Review, page read and edit, the shortcut sheet, and the day,
month, and year date-picker modes. No unreadable text, invisible boundary, or
lost focus was observed. Flet reported `high_contrast=True`; the dark passes
also reported `brightness=DARK`. The system returned to normal contrast and the
light appearance after the check. The `0.14.0` release carries the same
application code; only release metadata, documentation, and OpenSpec artifacts
changed after this check.

## Release artifacts

A `v<major>.<minor>.<patch>` tag push publishes the GitHub release; the workflow
attaches every asset. The release carries:

- the Linux native build, which is the tested and supported `1.0.0` artifact;
- the Python wheel, installed with `pipx`, for the macOS and Windows browser
  path;
- `afanes-<version>-checksums.txt`, a SHA-256 entry for each artifact, also
  reproduced in the release notes.

Native macOS and Windows binaries are not release artifacts. Publication runs
only after the preflight check, the automated gates, and the artifact checksum
verification pass, and the pipeline deletes an unpublished draft when a step
fails. A published release is immutable: a re-run for the same tag fails and
names the existing release. Rollback for a bad release deletes the release,
keeps the tag, and ships a patch version. There is no PyPI publication and no
code signing, notarization, or auto-update. The wheel must prove that
`afanes --web` starts with networking unavailable before the tag; if the Flet
web client is fetched at startup, the packaging work bundles it or records the
limitation in the release notes.

## Constraints (not gaps)

- Artifacts are unsigned. There is no code signing, notarization, or
  auto-update; macOS and Windows use the wheel and `afanes --web`.
- The first development desktop run may fetch the Flet client once as
  provisioning; a packaged build bundles the client and starts offline.
- There is no cloud sync, account, telemetry, or hidden network call.
- `0.14.0` is the current version. Archived changes stay under `Unreleased`;
  versions move only when a release is cut deliberately.

## Version path

`0.14.0` is the current version. Archiving a change does not bump the version or
create a tag; its entry stays under `Unreleased`. A release is a deliberate act:
bump with `hatch version patch|minor|major`, move the `Unreleased` entries under
the released heading, and push the tag, which publishes it. `1.0.0` follows only
when every row in the unified gate is green. The maintainer confirms the
transition after reviewing the recorded evidence in this file.

## Work sequence

The remaining work lands in dependency order, one approved OpenSpec change at a
time:

1. HIG wave 3: writing style and a copy gate. Landed in `0.8.0`.
2. HIG wave 4: feedback patterns. Landed in `0.8.0`.
3. Internationalization: English and Spanish.
4. Note reminders: schema `2`, recurring and one-shot schedules.
5. HIG wave 5: keyboard and accessibility, covering the localized and reminder
   interface. Landed in `0.13.0`.
6. HIG wave 7: identity, the SVG app icon, the final palette, an empty
   conformance baseline, and the residual wave 6 polish. Landed in `0.14.0`.
7. Linux release workflow: the pinned GitHub Actions build, the checksummed
   artifact, and the downloaded-artifact evidence path. Landed in `0.14.0`.
8. Automated release publishing and the `1.0.0` release: the tag-triggered
   pipeline, the wheel release asset, the packaged Linux evidence, and the first
   published release. Delivered by this change.

## Not planned

**Non-goals.** Code signing, notarization, auto-update, PyPI publication, and
native macOS or Windows support guarantees remain outside the project. Native
macOS and Windows binaries are not release artifacts. OS-level reminder
notifications, snooze, and reminder end dates are outside `1.0.0`. Translated
documentation is out of scope; the documentation stays English.

**Deferred.** Docs-site deployment, versioned documentation, the export
capability, a persistent reference cache, and the macOS and Windows nightly
workflow with its native binaries are deferred; none has a scheduled change.

**Reversed.** The SQLite index, `afanes index`, and `afanes doctor` are not
planned. `AGENTS.md` requires an approved change before any of them is added.
