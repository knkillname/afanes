# Tasks

## 1. Generate representative vaults

- [x] 1.1 Add `scripts/scan_benchmark.py` with a parameterized vault generator (`--notes`, `--body-paragraphs`, `--steps-per-project`, `--reference-ratio`) that writes captures, references with optional categories, and projects with step metadata into a temporary directory; verify a 50-note run leaves a tree that `Vault.open` and `Vault.scan` accept.
- [x] 1.2 Add the generator to the same script behind a `generate` subcommand so tests can call it without timing; verify the subcommand produces the expected file counts.
- [x] 1.3 Add `tests/core/test_scan_benchmark.py` that imports the generator, builds about 50 notes in `tmp_path`, scans with the public `Vault` API, and asserts the snapshot counts and an empty failure list; verify it passes.

## 2. Measure

- [x] 2.1 Implement the timing harness: `Vault.open`, the first `Vault.scan`, and `Vault.scan_fingerprint`, each after a warm-up, with `--repeat` samples and min/median/max reported through `time.perf_counter`; verify a 100-note run prints a table.
- [x] 2.2 Print the environment block: Python version, platform, filesystem, CPU count, and current commit; verify the block appears with the table.
- [x] 2.3 Run the benchmark at 1,000, 5,000, and 10,000 notes, twice, and add a `## Measured baseline` section to `design.md` with the environment, the three phases, and the observed spread; verify the second run lands within the spread of the first.

## 3. Record the decision

- [x] 3.1 Apply the design's decision rule to the 10,000-note median and agree the pass line with the maintainer before archive; write the number, the line, and the outcome into `design.md`; verify the outcome either closes the question or names a follow-up change with the measured justification.
- [x] 3.2 Add the benchmark command to `AGENTS.md` section 2 beside the other developer commands; verify the command runs as written from a clean checkout.
- [x] 3.3 Add the `Unreleased` changelog entry naming this change, the benchmark, and the recorded result; verify the entry is written as an observable outcome.

## 4. Integration checks

- [x] 4.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the 6.6 compliance check; verify all pass.
