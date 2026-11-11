# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A changelog following Keep a Changelog 1.1.0.

### Changed

- The operating manual now requires strict NumPy-style docstrings for every public API, including all parameters, return values, raised exceptions, and public attributes.
- Archiving an OpenSpec change now bumps the version, updates the changelog and README, runs the quality gates, and creates a release commit.
- OpenSpec project context now records the offline, neutral-vocabulary, docstring, and cross-platform constraints, and archive guidance carries the release steps.

## [0.0.1] - 2026-11-10

### Added

- Initial Python 3.13 package layout under `src/afanes/` with Hatch build and development environments.
- Ruff, Pyrefly, pytest, Hypothesis, and coverage configuration.
- OpenSpec workspace with the `spec-driven` schema, workflow skills, and slash commands.
- `AGENTS.md` operating manual, MIT licensing, and baseline README.
