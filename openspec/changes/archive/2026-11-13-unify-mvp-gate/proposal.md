# Proposal

## Why

`RELEASE.md` currently separates the `1.0.0` gate from three candidate themes.
The maintainer has decided the project MVP and `1.0.0` are the same thing:
HIG conformance, internationalization, and note reminders are required for
1.0, not later candidates.

The current gate also assumes macOS and Windows manual evidence that the
maintainer cannot produce. At the same time, the release path assumes local
builds only, with no CI, no GitHub release artifacts, and no cross-platform
distribution. Without one written union, contributors and agents cannot tell
what 1.0 means, which platform is actually supported, or what evidence a
release requires.

This change records the unified gate before the capability work starts. It does
not implement HIG, i18n, or reminders; each remains its own approved change.

## What Changes

- **Unify the gate.** `RELEASE.md` defines `1.0.0` as the existing six
  checklist rows plus three required rows: HIG conformance,
  internationalization, and note reminders. The post-1.0 candidate section is
  removed. Moving any of the three out of 1.0 now requires a change to
  `RELEASE.md`.
- **HIG conformance.** Waves 3, 4, 5, and 7 complete, with wave 6 residual
  per-view polish folded into wave 7; the conformance baseline empty; only the
  five declared Flet differences remaining; Linux visual and keyboard review.
  The app icon is a required SVG asset and may be its own small change.
- **Internationalization.** English and Spanish; UI copy, validation and error
  messages, dates and numbers, CLI copy, and bundled guide and starter
  templates. Documentation stays English. The system locale is the default, an
  in-app override applies on restart, and missing strings fall back to English.
- **Note reminders.** One whole-note reminder per note, either one recurrence
  or one one-shot. Recurrences support daily, selected weekdays, day of month,
  and nth weekday, with one or more times. Due reminders appear in Review with
  one catch-up entry per schedule; dismiss or acknowledge never changes the
  note. The schedule lives in an optional frontmatter key, the vault schema
  becomes `2`, and older vaults receive a courtesy one-line upgrade.
- **Platform policy.** Linux native is the only 1.0 release gate. macOS and
  Windows use a wheel attached to the GitHub release, installed with `pipx`,
  then `afanes --web`. Nightly GitHub Actions on Windows and macOS run the
  checks and native builds; they are advisory and never block. Native binaries
  are attached to the release only when that platform's nightly tests and
  build both pass. They are untested at runtime, unsigned, and unsupported.
- **Release artifacts.** The GitHub release carries the Linux build, the
  wheel, and any qualifying experimental native binaries. There is no PyPI
  publication. Artifacts are attached manually for 1.0.
- **Sequence and version path.** HIG wave 3, HIG wave 4, i18n, reminders, HIG
  wave 5, HIG wave 7, then packaging and Linux evidence. Intermediate `0.x`
  releases group completed work; no future checkpoint is named, and `1.0.0`
  follows only when the whole union is green.
- **Policy updates.** Nightly advisory CI becomes part of the project, so the
  "there is no CI" rule changes when the workflow lands. GitHub release
  publishing moves into 1.0. Code signing, notarization, auto-update, PyPI,
  translated documentation, and OS-level reminder notifications remain out.

## Capabilities

### New Capabilities

None in this change. The behavior specifications land with their own changes:
`interface-localization` for i18n, `note-reminders` for reminders, and deltas
to `interface-theme`, `note-model`, `vault-schema`, and `guided-review` for the
HIG and reminder work. This change is release planning and documentation only,
so it sets `skip_specs: true`.

### Modified Capabilities

None.

## Impact

- `RELEASE.md`: the unified gate, platform matrix, release artifacts, version
  path, sequence, and non-goals.
- `README.md`: the platform support statement and the source, wheel, and
  experimental native paths.
- `docs/develop/releasing.md`, `docs/getting-started/install.md`, and
  `docs/guide/browser-mode.md`: GitHub Releases, the wheel and web path,
  nightly advisory builds, and the Linux-only release gate.
- `CHANGELOG.md`: one `Unreleased` entry under `Changed`.
- `AGENTS.md`: the CI rule changes when the nightly workflow is added; this
  change records the policy and leaves the workflow to its own change.
- No source, test, dependency, runtime behavior, or vault-format change in this
  change. The wheel must later prove that `afanes --web` starts offline; that
  verification belongs to the packaging change.
