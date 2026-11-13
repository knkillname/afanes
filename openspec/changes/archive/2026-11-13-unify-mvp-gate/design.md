# Design

## Context

See `proposal.md` - Why. The repository has one release definition
(`RELEASE.md`), one interface standard with migration waves
(`docs/develop/interface-standard.md`), and an OpenSpec workflow that requires
an approved change before behavior work. The maintainer has one Linux machine;
macOS and Windows manual checks cannot be produced. The project has no CI and
no GitHub release publishing today.

This change is release planning and documentation only. It records decisions
that later capability changes must honor; it does not implement them. The
design therefore focuses on the gate's shape, the platform and artifact
policy, the sequence, and the boundaries between this change and the later
ones.

## Goals / Non-Goals

**Goals:**

- Replace the two-layer "1.0 gate plus candidate themes" model with one gate.
- Make the supported platform and evidence boundary explicit and honest.
- Preserve every product decision from the roadmap discussion so later changes
  do not re-litigate them.
- Keep `RELEASE.md` as the single release record and the interface standard as
  the owner of HIG detail.
- Record the release-artifact and advisory-CI policy without adding runtime
  code.

**Non-Goals:**

- Implementing HIG waves, i18n, reminders, packaging, or CI.
- Creating the capability specs for those themes.
- Designing the reminder YAML shape, the i18n catalog mechanism, or the app
  icon.
- Publishing anything, tagging a release, or changing the version.
- Promising macOS or Windows native support.

## Decisions

### D1. Keep one release record and remove the candidate layer

`RELEASE.md` remains the single home. Its `1.0.0` definition becomes the union
of the existing six checklist rows and three new rows. The "Candidate themes
after the 1.0 gate" section is deleted, and the open-decisions section shrinks
to the decisions that are still genuinely deferred.

Alternatives considered:

- a separate `ROADMAP.md`: creates a second source of truth;
- keep the candidate section and add a second gate: preserves the ambiguity
  this change exists to remove;
- record the union only in OpenSpec: the release record would not show it.

### D2. Linux native is the only 1.0 gate; macOS and Windows are documented paths

Linux keeps the full manual checklist. macOS and Windows are documented as a
wheel plus `afanes --web`, not as release-gated native platforms. The code
stays cross-platform; only the evidence promise changes. This is the honest
boundary while the maintainer has no Mac or Windows machine.

Alternatives considered:

- keep all three platforms as gates: impossible to satisfy with the available
  hardware;
- drop macOS and Windows entirely: loses a usable path through the browser;
- make the wheel a gate too: no one can run its manual checks either.

### D3. Use the GitHub release as the artifact shelf; no PyPI

The app is the product, not a library. The GitHub release carries the Linux
build, the wheel, and any qualifying experimental native binaries. The wheel
is an installable artifact for the web-mode path, not a library publication.
PyPI stays out.

Alternatives considered:

- PyPI: library framing, publishing credentials, and a pipeline the project
  does not need;
- source-only: requires every macOS/Windows user to install Hatch and a
  checkout;
- native-only: blocked by the missing build machines.

### D4. Nightly CI is advisory and may attempt native builds

A scheduled GitHub Actions workflow runs `hatch check` and `hatch test` on
Windows and macOS, and attempts `flet build` for each. Failures are reported
but are not required checks and never block merges, releases, or 1.0. A
platform's native binary is attached to the release only when that platform's
nightly tests and build both pass. The binaries are untested at runtime,
unsigned, and unsupported.

Alternatives considered:

- no CI: no cross-platform signal at all;
- gating CI: the unavailable platforms would block the release;
- tests only: misses build-toolchain failures that the experiment is meant to
  find.

### D5. HIG completion means the whole standard

Waves 3, 4, 5, and 7 are required, and the residual wave 6 per-view polish is
folded into wave 7. The conformance baseline must be empty, only the five
declared Flet differences remain, and Linux gets a visual and keyboard review.
The app icon is a required SVG asset; it can be produced by its own small
change and blocks wave 7.

Alternatives considered:

- measured gate only: leaves manual visual and keyboard debt;
- defer wave 6 polish: does not meet strict conformance;
- placeholder icon: contradicts the identity requirement.

The font and icon limits are recorded as follows:

- fonts are the platform font, not a bounded difference; the resolved family
  is verified on Linux, and a non-native resolution becomes an explicit
  difference only through a standard change;
- in-app icons remain the existing Material outlined difference;
- the app icon is a separate SVG deliverable, not a toolkit difference.

### D6. i18n covers the interface, CLI, and starter content

English and Spanish are required. The catalog covers UI copy, validation and
error messages, dates and numbers, CLI copy, and the bundled guide and starter
templates. Documentation stays English. The system locale is the default, an
in-app override applies on restart, and missing strings fall back to English.

Alternatives considered:

- UI only: leaves the CLI and starter content half-translated;
- translate the docs too: a separate large effort;
- immediate switching: more state and re-render work for a setting most users
  touch once;
- OS locale only: no override for bilingual users.

### D7. Reminders are one whole-note schedule, stored in frontmatter

A note may carry one reminder: either one recurrence or one one-shot. A
recurrence supports daily, selected weekdays, day of month, and nth weekday,
with one or more times. A one-shot has an independent date and time and offers
before-deadline shortcuts; `due_date` remains a separate project field. Due
reminders appear inside Review, with one catch-up entry per schedule showing
the latest missed occurrence. Dismiss or acknowledge clears the occurrence and
never changes the note's status. A reminder pauses when the note is trashed or
its status is finished, cancelled, archived, or deferred, and resumes if the
note returns.

The schedule lives in an optional frontmatter key. The vault schema becomes
`2`; a schema `1` vault gets a courtesy one-line `afanes.yaml` upgrade when
writable. There are no compatibility shims or mixed-schema support.

Alternatives considered:

- per-step reminders: requires a new step metadata syntax and parser work;
- a playlist of schedules per note: more UI and schema complexity than the
  stated need;
- an app-managed side file: breaks the vault as the single source of truth and
  drifts under renames;
- a hidden key inside schema `1`: hides a real contract change;
- no upgrade for older vaults: allowed before 1.0, but a poor first-run
  experience for existing users.

### D8. Sequence follows the dependencies

The order is HIG wave 3, HIG wave 4, i18n, reminders, HIG wave 5, HIG wave 7,
then packaging and Linux evidence. Wave 3 and wave 4 settle copy and feedback
before translation; i18n lands before reminders so reminder strings are born
bilingual; wave 5 covers the localized and reminder UI; wave 7 closes the
baseline and identity. Nightly CI starts with the first change and stays
advisory.

Alternatives considered:

- reminders before i18n: the feature lands sooner, but its copy is translated
  later and wave 4 may change it;
- parallel themes: faster in calendar time, with more coordination and rework;
- wave 7 before the features: the baseline would be reopened by later UI.

### D9. Keep the durable version rule; name no future checkpoint

`0.7.0` is current. Intermediate `0.x` releases group completed work.
`1.0.0` follows only when the whole union is green. No future version is named
as a checkpoint, so the stale `0.6.0` failure cannot repeat.

Alternatives considered:

- name `0.8.0` and `0.9.0`: creates checkpoints that may not match the work;
- keep `0.6.0`: already false;
- bump only at 1.0: hides completed milestones from the changelog.

### D10. Update the supporting documents, not just the gate

`README.md` gets the platform support statement. `docs/develop/releasing.md`,
`docs/getting-started/install.md`, and `docs/guide/browser-mode.md` describe
the GitHub release, the wheel and web path, the advisory nightly builds, and
the Linux-only release gate. `AGENTS.md`'s "there is no CI" rule changes when
the nightly workflow lands, not in this change. Release artifacts are attached
manually for 1.0.

Alternatives considered:

- update only `RELEASE.md`: users would still read the old support story;
- update `AGENTS.md` now: the workflow does not exist yet;
- automate publishing: more release machinery than 1.0 needs.

## Risks / Trade-offs

- [The expanded gate makes 1.0 much later] -> The gate is explicit and the
  work is split into separate changes; intermediate `0.x` releases show
  progress.
- [macOS/Windows native binaries are untested] -> Label them experimental,
  unsigned, and unsupported; attach only when nightly tests and build pass;
  never treat them as 1.0 evidence.
- [Nightly CI is slow or flaky, especially macOS] -> Keep it advisory, split
  jobs, upload artifacts with short retention, and never make it a required
  check.
- [Unsigned binaries are blocked by Gatekeeper or SmartScreen] -> Document the
  limitation; keep the wheel and web path as the usable alternative.
- [The wheel cannot start `afanes --web` offline] -> The packaging change must
  verify startup with networking unavailable and bundle the client if needed.
- [i18n or reminders exceed the `AppState` budget] -> Their changes must make
  an explicit architectural decision; this change adds no state.
- [Schema `2` breaks older vaults] -> The optional key and the one-line
  `afanes.yaml` upgrade keep existing vaults usable; no compatibility shims.
- [The app icon blocks wave 7] -> Give it its own small change and treat the
  SVG as a wave 7 dependency.
- [Documentation drifts from the gate] -> Keep `RELEASE.md` as the single
  source and link to it from README and docs instead of duplicating criteria.

## Migration Plan

1. Rewrite `RELEASE.md`: the union gate, platform matrix, artifact policy,
   sequence, version path, and non-goals.
2. Update `README.md` and the three docs pages named in D10.
3. Add one `Unreleased` changelog entry.
4. Run `openspec validate --all --strict`, `openspec doctor`, `hatch check`,
   `hatch test --cover`, the vocabulary greps, and `hatch run docs:build`.
5. Rollback is a documentation revert; no runtime or vault migration happens
   in this change.

The later changes run in the D8 order. The reminder change owns schema `2` and
the vault upgrade. The packaging change owns the wheel, the offline web-start
verification, and the GitHub release. The CI change owns the nightly workflow
and the `AGENTS.md` rule update.

## Open Questions

- The i18n catalog mechanism, locale storage, and any `AppState` change are
  deferred to the i18n change.
- The reminder YAML shape, editor UI, Review ordering, and acknowledgment
  storage are deferred to the reminder change.
- The app icon brief, SVG, and platform derivatives are deferred to the icon
  or wave 7 change.
- The offline web-client behavior and GitHub Actions cost are deferred to the
  packaging and CI changes.
