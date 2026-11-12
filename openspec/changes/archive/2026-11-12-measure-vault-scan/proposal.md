# Proposal

## Why

Afanes has no index by design: every scan reads each note, and
`Vault.scan_fingerprint()` stats every file so a change triggers a full
re-read. That decision rests on an assumption that has never been measured.
There is no baseline, no repeatable benchmark, and no budget, so nobody can say
whether a 1,000-note vault and a 20,000-note vault behave the same. Meanwhile
`openspec/config.yaml` still describes a SQLite cache, which implies the
question was answered somewhere that no longer exists. Without a number, the
next performance discussion is a matter of taste.

## What Changes

- Add a standalone benchmark (`scripts/scan_benchmark.py`, run through
  `hatch run python`) that creates a synthetic vault in a temporary directory,
  times `Vault.open`, a cold `Vault.scan`, and a no-op
  `Vault.refresh_if_changed` at several note counts, and prints a table.
- Parameterize the synthetic vault: note count, average body length, step
  count, and reference density, so the measurement reflects the documented
  note shapes rather than empty files.
- Record the measured baseline for the maintained sizes in the change design,
  including the machine, Python version, and filesystem, and state the method.
- Define the decision rule: the **10,000-note cold scan** is the defended
  metric, and the pass line is set after the first baseline is recorded. If
  the median exceeds that line, a separate change proposes a cache; if not,
  the no-index decision is documented as measured rather than assumed.
- Leave runtime behavior unchanged. No cache, no new dependency, no new
  command.

## Capabilities

None. This change adds tooling and a recorded measurement; it does not change
what the application does. `skip_specs: true` is declared in `.openspec.yaml`.

### New Capabilities

- None.

### Modified Capabilities

- None.

## Impact

- New `scripts/scan_benchmark.py`; nothing under `src/` changes.
- `tests/core/` gains a small test that the benchmark's vault generator
  produces a valid vault, so the tool cannot silently benchmark an unreadable
  tree.
- `AGENTS.md` section 2 records the benchmark command beside the other
  developer commands. This depends on `reconcile-repository-guide` landing
  first, or must be rebased onto it.
- `openspec/config.yaml` index wording is owned by `reconcile-repository-guide`;
  this change only records the measurement in its design.

## Open Questions

None. The maintainer confirmed the defended size (10,000 notes), the gating
metric (cold scan), and the order (measure, then set the pass line before
archive). The fingerprint and end-to-end refresh numbers are reported but do
not gate.
