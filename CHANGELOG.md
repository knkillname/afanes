# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-10

### Added

- First-run vault selection with a folder picker; the chosen vault is remembered outside the vault and reopened on later launches.
- An Inbox that captures raw thoughts as notes under `inbox/`, lists them newest first, refreshes external changes, and previews Markdown read-only with inert links.
- Recoverable startup and scanning behavior for missing or unreadable vaults, corrupt settings, and notes that cannot be parsed.
- A Flet 1.1.2 desktop interface with keyboard capture and light and dark theme support.
- Main specifications for the `vault-selection` and `inbox-capture` capabilities.

### Fixed

- Filename sanitization is now idempotent when a forbidden character exposes a leading space, such as `.|0`.

## [0.1.0] - 2026-11-10

### Added

- A changelog following Keep a Changelog 1.1.0.
- Name-based note references in standard Markdown using `person:`, `project:`, and `note:` schemes, with resolved, unresolved, and ambiguous outcomes.
- Filename-based note identity with per-scheme uniqueness, cross-platform sanitization, and reference-preserving directory moves and renames.
- Read-only vault scanning and atomic note creation, move, rename, deletion, and inbound-reference reporting.
- Runtime dependencies on `markdown-it-py` for CommonMark parsing and `PyYAML` for safe frontmatter handling.

### Changed

- The canonical vault format now uses scheme references instead of bracket links; `AGENTS.md` and the README document the new format.
- The operating manual now requires strict NumPy-style docstrings for every public API, including all parameters, return values, raised exceptions, and public attributes.
- Archiving an OpenSpec change now bumps the version, updates the changelog and README, runs the quality gates, and creates a release commit.
- OpenSpec project context now records the offline, neutral-vocabulary, docstring, and cross-platform constraints, and archive guidance carries the release steps.
- The project license is now consistently AGPL-3.0-or-later across the LICENSE file, package metadata, README, and source headers.

### Security

- Active URL schemes such as `javascript:` are classified as unsafe and never resolve as internal references.

## [0.0.1] - 2026-11-10

### Added

- Initial Python 3.13 package layout under `src/afanes/` with Hatch build and development environments.
- Ruff, Pyrefly, pytest, Hypothesis, and coverage configuration.
- OpenSpec workspace with the `spec-driven` schema, workflow skills, and slash commands.
- `AGENTS.md` operating manual, MIT licensing, and baseline README.
