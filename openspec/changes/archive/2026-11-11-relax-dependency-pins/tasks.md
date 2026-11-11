# Tasks

## 1. Dependency declarations

- [x] 1.1 Replace the exact runtime pins in `[project.dependencies]` with the ranges from
      `design.md` (`flet>=1.0.4,<2`, `markdown-it-py>=4.0,<5`, `PyYAML>=6.0.3,<7`). Verify with
      `hatch build` followed by reading the wheel's `METADATA`: every `Requires-Dist` entry shows a
      range and no runtime entry contains `==`.
- [x] 1.2 Add `[project.optional-dependencies]` with `desktop = ["flet[desktop]>=1.0.4,<2"]` and
      `web = ["flet[web]>=1.0.4,<2"]`. Verify the same built wheel's `METADATA` lists both
      `Provides-Extra` entries and the extra requirements reference the `flet[desktop]` and
      `flet[web]` forms rather than standalone client packages.
- [x] 1.3 Replace the `dev` group's `flet-desktop==1.1.2` entry with `flet[desktop]>=1.0.4,<2` so a
      source run resolves the same way an end-user desktop install does. Verify with
      `hatch env show -i --json` that the `hatch-test` and `default` environments carry the ranged
      entry and no remaining `flet-desktop==` pin.

## 2. Floor test environment

- [x] 2.1 Add the second `[[tool.hatch.envs.hatch-test.matrix]]` table and the
      `matrix.deps.dependencies` override from `design.md` so a floor environment pins
      `flet[desktop]==1.0.4`, `markdown-it-py==4.0.0`, and `PyYAML==6.0.3`. Verify with
      `hatch env show -i --json` that a `hatch-test.py3.13-floor` environment exists, that it lists
      the three floor pins, and that no other matrix environment received them.
- [x] 2.2 Run the full suite against the floor and confirm it passes with no exclusions:
      `hatch test --all --cover`. Verify the run includes the floor environment and that coverage
      still meets the 85% gate.

## 3. Policy and documentation

- [x] 3.1 Rewrite `AGENTS.md` section 2.2 so runtime dependencies use compatible-release ranges,
      the lower bound must be exercised by the test matrix, release notes record the resolved
      versions, and optional runtimes use Flet's extras instead of Afanes-side patch pins. Update
      section 2.3 (Flet pinning) and the dependency table in 2.7 to match. Verify by searching
      `AGENTS.md` for the exact-pin mandates and confirming none remain and that the replacement
      text covers all four rules.
- [x] 3.2 Update the `README.md` install and development sections to describe the three install
      shapes (`afanes`, `afanes[desktop]`, `afanes[web]`), when to choose each, and the supported
      Flet floor. Verify every documented command matches the `Requires-Dist` and `Provides-Extra`
      entries in the built wheel from task 1.2.
- [x] 3.3 Add an `Unreleased` entry to `CHANGELOG.md` describing the range-based install and the
      optional runtime groups. Verify the entry uses only the Keep a Changelog categories and names
      no internal file inventory.

## 4. Integration checks

- [x] 4.1 Run `hatch check`, `hatch test --cover`, and `openspec validate --all --strict`. Verify
      all three pass and that `hatch check` reports no change to formatted files.
- [x] 4.2 Run the prohibited-vocabulary checks from `AGENTS.md` section 6.6 against the changed
      files. Verify both commands produce no matches.

## Workflow follow-up

- Record the resolved versions of the three ranged dependencies in the changelog entry produced
  during the post-archive release step in `AGENTS.md` section 5.8.
- Archive the change only after review and a passing gate.
