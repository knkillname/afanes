# Proposal

## Why

The repository keeps two durable plans: `RELEASE.md` defines the `1.0.0` gate,
and `docs/develop/interface-standard.md` defines the HIG migration waves.
Neither records the candidate themes discussed for the MVP, and the version path
in `RELEASE.md` is stale: it still names `0.6.0` as the checkpoint although
`0.7.0` is the current version and four completed changes sit under
`Unreleased`, while the macOS and Windows platform checks remain pending.

Without one record, contributors and agents cannot tell committed work,
deferred work, and conversation-only intentions apart. Internationalization and
note reminders exist only in discussion, HIG completion is spread across a
separate standard, and explicitly rejected plans are scattered across archived
changes. This change writes the missing record before new work starts.

## What Changes

- **Fix the version path in `RELEASE.md`.** Retire the `0.6.0` checkpoint that
  was never completed, record `0.7.0` as the current version, and state the
  durable rule: the next bump follows the existing milestone rule, the queued
  breaking UI changes make a completed milestone a MINOR release, and `1.0.0`
  still follows only when every checklist row and platform cell is green.
- **Record the candidate themes after the 1.0 gate.** Add a section that names
  the three themes as candidates, not commitments or an ordered backlog:
  - HIG conformance completion: waves 3 (writing style), 4 (feedback),
    5 (keyboard and accessibility), and 7 (identity and an empty conformance
    baseline), with `docs/develop/interface-standard.md` staying the owner of
    the wave detail and the five Flet bounded differences.
  - Interface internationalization: locale-aware copy, formatting, and bundled
    template content, with the target languages and mechanism still open.
  - Note reminders: recurring schedules, delivery, storage, and schema timing,
    with the delivery and schema decisions still open.
- **Record the open decisions.** Whether any candidate theme moves into `1.0.0`,
  which languages i18n targets, whether reminders need native notifications or
  OS-level scheduling, and whether a reminder key changes the vault schema.
- **Record what is not planned.** Keep signing, notarization, auto-update, and
  publishing as explicit non-goals; keep docs-site deployment, versioned docs,
  the export capability, and a persistent reference cache as deferred; and state
  that the SQLite index, `afanes index`, and `afanes doctor` are not planned,
  because `AGENTS.md` requires an approved change for them.
- **Add an `Unreleased` changelog entry** naming the roadmap record.

The change does not decide the MVP scope question, does not add a roadmap
capability to the product, and does not implement any of the themes. The `1.0.0`
definition is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

This is a documentation and release-planning change with no spec-level behavior
change, so the change sets `skip_specs: true`. The existing specs remain the
behavior contract.

## Impact

- `RELEASE.md`: the introduction, version path, a candidate-themes section, the
  open decisions, and the non-goals and reversed plans.
- `CHANGELOG.md`: one `Unreleased` entry under `Changed`.
- `README.md`: no change required; it already links `RELEASE.md`.
- `docs/`: no change required; the interface standard stays the HIG owner and
  `docs/develop/releasing.md` already points to `RELEASE.md`.
- `AGENTS.md`: no change required; it already points to `RELEASE.md` for the
  checklist, platform evidence, and version path.
- No source, test, dependency, public API, or vault-format change.
