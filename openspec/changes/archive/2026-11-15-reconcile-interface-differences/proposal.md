# Proposal

## Why

`date-entry` added the anchored calendar popover as the sixth bounded Flet difference. The interface
standard and the date-picker requirement record it, but the general `interface-theme` requirement,
`RELEASE.md`, and `AGENTS.md` still say five. The repeated lists have already drifted once, and the
next difference would make them drift again.

## What Changes

- Make the interface standard's bounded-differences table the single list. The `interface-theme`
  requirement points to that table instead of enumerating its own copy.
- Drop the numeric difference counts from `RELEASE.md` and `AGENTS.md`; both point to the standard.
- Add one operating rule to `AGENTS.md`: never restate the bounded-differences count outside the
  standard.
- Record that this change has no user-facing behavior, no changelog entry, and no version bump.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-theme`: the bounded-differences requirement stops enumerating its own list and names the
  interface standard's table as the single source.

## Impact

- `openspec/specs/interface-theme/spec.md` changes when the delta is synced.
- `RELEASE.md` and `AGENTS.md` lose the stale numeric counts and gain the single-source rule.
- No source code, test, dependency, API, schema, or user-facing documentation changes.
- Design is deliberately skipped: this is a specification and documentation correction, so none of
  the design document's triggering conditions apply.
