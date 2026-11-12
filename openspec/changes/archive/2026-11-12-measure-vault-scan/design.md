# Design

## Context

See `proposal.md` - Why. Relevant implementation:

- `Vault` is a stateless service: it holds only a resolved `root`, so a scan
  cost is a property of the tree, not of accumulated state.
- `Vault.scan()` walks the vault and parses every note into `VaultNote`.
- `Vault.scan_fingerprint()` returns `tuple[tuple[str, int, int], ...]`, one
  `(relative path, size, mtime)` per note, and `VaultSession.refresh_if_changed`
  rescans when it differs.
- There is no cache, so the fingerprint pass is `O(notes)` syscalls on every
  refresh check.

## Goals / Non-Goals

**Goals:**

- Produce a reproducible number for vault sizes the product intends to support.
- Make the no-index decision defensible or overturn it with evidence.
- Keep the measurement out of the shipped package and out of the default test
  run.

**Non-Goals:**

- Optimizing anything in this change.
- Asserting timings in the test suite, which has no CI and runs under coverage
  and randomized ordering.
- Modeling every real vault. The benchmark is a tripwire, not a proof.

## Decisions

### D1. A standalone script, not a test

Put the benchmark in `scripts/scan_benchmark.py` and run it through
`hatch run python scripts/scan_benchmark.py`. The alternative - a marked
pytest - was rejected: `--strict-markers` would need a new marker, coverage and
`pytest-randomly` distort timing, and with no CI a timing assertion would only
fail on a developer machine at the worst moment.

The script lives outside `src/`, so the architecture gate's module-function
rule does not apply and the package gains no entry point.

### D2. Synthetic vaults generated in a temporary directory

The script builds its vaults under `tempfile.TemporaryDirectory()`. It never
accepts a path to a real vault, so a mistyped argument cannot scan user data.

The generator mirrors the documented note shapes: a `type: note` capture in
`inbox/` with a heading and prose; a `type: reference` note in `reference/`
with a category label for part of the set; a `type: project` note in
`projects/` with a status and a body containing task list items with
`owners`, `plan`, and `tags` metadata. A configurable fraction of notes carry
`note:` and `project:` references so link resolution is exercised, and step
owners populate the name catalog.

Parameters: `--notes`, `--body-paragraphs`, `--steps-per-project`,
`--reference-ratio`, and `--repeat`. Defaults should describe a plausible
personal vault rather than a best case.

### D3. Report the distribution, not one number

For each size, run a warm-up then `--repeat` timed samples and report min,
median, and max for three phases:

1. `Vault.open` (root resolution and validation).
2. `Vault.scan` (cold within the process, first call).
3. `Vault.scan_fingerprint` (the refresh check).

Use `time.perf_counter()`. Print a table plus an environment block: Python
version, platform, filesystem type, CPU count, and the current commit. The
median is the gating metric; min and max show the noise floor.

### D4. Gate the decision on the 10,000-note cold scan

The decision rule covers only the metric the user actually feels: a cold scan
of a 10,000-note vault. The fingerprint check is reported for context but does
not gate, because it is the cheap path the app uses on every refresh.

Record the threshold in this design after the first run, not before. Choosing a
number in advance would repeat the current mistake in the other direction.

- If the median is under the threshold, write the result into the release
  readiness record and close the question.
- If it is over, open a separate proposal for a cache with the measured number
  as its justification. That proposal, not this one, decides the design.

### D5. One test keeps the generator honest

Add a test under `tests/core/` that builds a small generated vault (about 50
notes) in `tmp_path`, scans it with the public `Vault` API, and asserts that the
snapshot contains the expected counts and no failures. This catches a generator
that drifts away from the documented note format, which would make the
benchmark measure parsing of unreadable files.

The test imports the generator from `scripts/` by path. If that is awkward
under the project's import rules, move the generator into a `tests/` helper and
have the script import it; the design prefers the script as the owner and the
test as the consumer.

## Risks / Trade-offs

- [Synthetic notes are not representative] -> The generator follows the note
  shapes in `README.md`; the parameters are explicit so a reviewer can judge
  them.
- [OS page cache makes repeated runs optimistic] -> Report a cold first scan
  separately and state that the number describes a warm filesystem.
- [Machine variance makes the number incomparable] -> Print the environment
  block and keep the script, so anyone can reproduce or challenge it.
- [The benchmark rots] -> The generator test fails when the note format drifts;
  the script is small enough to fix in one commit.
- [A passing number is read as a guarantee] -> Wording in the recorded result
  must call it a tripwire for one vault size on one machine.

## Measured baseline

Recorded on 2026-11-12 at commit `5f12671a1299`:

- Python 3.14.8, Linux 7.3.0-10-generic x86_64 with glibc 2.44, tmpfs, 16 CPUs.
- Method: `hatch run python scripts/scan_benchmark.py --notes 1000 5000 10000 --repeat 5`, run twice. Each phase runs once as a warm-up and then five timed samples with `time.perf_counter`.
- Synthetic vault shape: 40 percent references, the rest split between captures and projects; 3 prose paragraphs per note and 4 steps per project.

| Notes | Phase | Run 1 median (ms) | Run 2 median (ms) | Range across both runs (ms) |
| --- | --- | --- | --- | --- |
| 1,000 | open | 0.02 | 0.01 | 0.01-0.02 |
| 1,000 | scan | 1,199.60 | 1,187.11 | 1,179.56-1,205.32 |
| 1,000 | scan_fingerprint | 35.74 | 35.03 | 34.77-36.47 |
| 5,000 | open | 0.02 | 0.01 | 0.01-0.02 |
| 5,000 | scan | 6,032.57 | 5,967.65 | 5,935.66-6,035.95 |
| 5,000 | scan_fingerprint | 181.16 | 177.32 | 176.75-189.14 |
| 10,000 | open | 0.01 | 0.02 | 0.01-0.02 |
| 10,000 | scan | 12,007.79 | 12,092.46 | 11,965.85-12,282.21 |
| 10,000 | scan_fingerprint | 361.48 | 366.07 | 358.68-376.19 |

The two runs agree within about one percent at each size; the second 10,000-note
scan is 0.7 percent above the first median and inside the combined range. Cold
scan scales linearly with note count. The fingerprint pass is about 3 percent of
a cold scan and is the number the refresh loop pays.

**Decision.** The pass line is **15,000 ms for the 10,000-note cold-scan
median**. The measured median is 12,008 ms, so the no-index decision passes for
the defended size on this machine. The result is a tripwire for one vault size
on one machine, not a guarantee: a slower machine or a larger vault may cross
the line. The fingerprint cost is reported and does not gate, but a future
refresh-latency complaint at this size should start from these numbers rather
than reopen the cold-scan question.

The maintainer confirms this line before archive; if it is rejected, the
alternative is a separate proposal for a cache justified by the 12-second
median and the 0.36-second per-refresh fingerprint.

## Open Questions

None. The maintainer confirmed 10,000 notes as the defended size and the cold
scan as the gating metric. The pass line is deliberately set after the first
baseline and before archive; it is not an open design question.
