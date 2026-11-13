# Design

## Context

See `proposal.md` - Why. The repository has one release definition
(`RELEASE.md`) and one interface standard with migration waves
(`docs/develop/interface-standard.md`). The OpenSpec change system holds
approved work only; it has no place for candidate work that has not been
proposed. `AGENTS.md` requires an approved change before implementation, and
the post-archive workflow already treats `RELEASE.md` as the single release
record.

Two constraints shape the approach:

- The `1.0.0` definition is a contract. It can be changed, but only explicitly,
  and the maintainer has not decided whether the candidate themes belong before
  or after `1.0.0`.
- The HIG waves and the five bounded Flet differences already have an owner.
  Copying them into a second document would create drift.

## Goals / Non-Goals

**Goals:**

- Give the candidate themes one durable, discoverable home.
- Make the difference between a candidate, a deferred item, and a non-goal
  explicit.
- Repair the version path so it describes the current state and states a rule
  that will not age like a fixed checkpoint.
- Keep the `1.0.0` gate and the interface standard unchanged.

**Non-Goals:**

- Deciding whether i18n, reminders, or HIG completion are pre- or post-`1.0.0`.
- Choosing i18n languages, a catalog mechanism, reminder delivery, or reminder
  storage.
- Creating change proposals for any candidate theme.
- Adding a new product capability, spec, or runtime behavior.
- Replacing `RELEASE.md` with a general project plan.

## Decisions

### D1. Put the roadmap in `RELEASE.md`, not a new `ROADMAP.md`

`RELEASE.md` is already the single release record cited by `AGENTS.md`,
`README.md`, and `CHANGELOG.md`. Adding a second root document would create two
places to update and two places to drift. The file's scope grows from "release
readiness" to "release readiness and candidate next themes", which is a small
extension of its existing purpose.

Alternatives considered:

- a new `ROADMAP.md` at the root: clearer name, but a third source of truth;
- a `docs/develop/roadmap.md` page: good for contributors, but the release
  record already lives at the root and the two would cross-reference;
- OpenSpec changes only: keeps proposals as the only record, but there is no
  artifact for unapproved candidates, and the roadmap question would stay
  conversation-only.

### D2. Record themes, not commitments or an ordered backlog

Each theme names the area, the remaining work, and the owning document. It does
not carry dates, priorities, version numbers, or a sequence. A theme becomes
work only when a maintainer approves an OpenSpec change.

Alternatives considered:

- a dated roadmap: implies a commitment the project cannot keep while the
  platform checks are pending;
- a prioritized list: invites readers to treat the first item as next;
- a table of proposed change names: implies the changes are already scoped.

### D3. Link the HIG waves to the interface standard

The roadmap names waves 3, 4, 5, and 7 and the empty conformance baseline, then
points to `docs/develop/interface-standard.md` for the wave definitions, the
five bounded Flet differences, and the baseline rule. The standard remains the
owner of HIG conformance; the roadmap only records that the waves are a
candidate theme and what "done" means at the highest level.

Alternatives considered:

- copy the wave descriptions into `RELEASE.md`: duplicates the standard and
  guarantees drift;
- leave HIG out of the roadmap because it is already documented: loses the
  connection between HIG completion and the post-1.0 themes.

### D4. Replace the fixed checkpoint with a version rule

The version path records `0.7.0` as the current version, retires the `0.6.0`
checkpoint, and states the rule: an archive that completes no milestone stays
under `Unreleased`; a completed milestone that includes the queued breaking UI
changes is a MINOR bump; `1.0.0` follows only when the checklist and the
platform matrix are green. This is durable because it does not name a future
version.

Alternatives considered:

- name `0.8.0` as the next checkpoint: the same failure mode as `0.6.0`, since
  the next archive may be documentation-only and bump nothing;
- keep `0.6.0`: false, because `0.7.0` already shipped;
- delete the version path: loses the bump rule and the `1.0.0` gate
  connection.

### D5. Keep the `1.0.0` definition unchanged and record the scope question

The candidate section explicitly says that none of the themes is in the `1.0.0`
checklist today, and that moving one into `1.0.0` requires a change to
`RELEASE.md`. This preserves the existing contract and avoids answering a
product question the maintainer has not answered.

Alternatives considered:

- put the themes under `1.0.0`: silently expands the gate;
- describe them as post-`1.0.0`: decides the open question by implication;
- omit them until the scope is decided: loses the record this change exists to
  create.

### D6. Record the reversed plans explicitly

The roadmap's "Not planned" subsection names the SQLite index, `afanes index`,
and `afanes doctor` as rejected, and points to `AGENTS.md` for the rule. Older
changelog text called them planned; without an explicit reversal, a future
reader could resurrect them from history.

Alternatives considered:

- edit the old changelog entry: rewrites released history, which the release
  policy forbids;
- leave the reversal only in `AGENTS.md`: correct but hard to find from the
  release record.

### D7. Add a changelog entry and leave README and docs unchanged

The change produces a notable planning outcome, so it gets one `Unreleased`
entry under `Changed`, following the `define-mvp-release` precedent. `README.md`
already links `RELEASE.md`; `docs/develop/releasing.md` already describes
`RELEASE.md` as the release record; and the interface standard already owns the
HIG waves. No prose in either place becomes false.

Alternatives considered:

- no changelog entry: a documentation-only change still changes the project's
  planning record, and the release workflow expects an entry per archive;
- update the README project-status paragraph: duplicates the roadmap and adds a
  maintenance point;
- update the releasing guide: its description of `RELEASE.md` remains true.

## Risks / Trade-offs

- [The candidate section becomes a stale backlog] -> Keep it undated and
  unordered, and update it only when a theme is approved, started, or dropped.
  The section points to the owning documents instead of restating details.
- [Readers treat a theme as a commitment] -> Use "candidate" consistently, state
  that each theme needs an approved change, and avoid version numbers and dates.
- [The version rule drifts again] -> State the rule rather than a future version;
  record the current version in the changelog, not as a checkpoint.
- [HIG detail diverges from the standard] -> Link to the standard and name only
  the remaining waves and the empty-baseline target.
- [A reversed plan is resurrected from old text] -> Keep the "Not planned"
  subsection explicit and cite the rule in `AGENTS.md`.
- [The roadmap quietly expands `1.0.0`] -> Keep the checklist untouched and
  require a change to `RELEASE.md` before any theme enters it.

## Open Questions

None that block the documentation edit. The product decisions the roadmap
records - scope relative to `1.0.0`, i18n languages, reminder delivery, and
schema timing - are deliberately left to later changes.
