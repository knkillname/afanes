# Proposal

## Why

The interface standard requires the GNOME writing style, but the project still
ships mixed conventions: sentence-case control labels, final periods on nearly
every message, two straight apostrophes, first- and second-person pronouns, and
no automated copy check. Wave 3 of the migration is the writing-style and copy
gate. Without it, the localized copy in the later internationalization change
would encode inconsistent style in two languages, and the `1.0.0` gate could
not claim strict HIG conformance.

## What Changes

- **Writing-style rules.** Adopt the GNOME HIG writing style for all
  user-facing copy in both catalogs: header capitalization for headings,
  buttons, menu items, destination titles, and tooltips; sentence capitalization
  for field labels, hints, and prose; neutral tone without first- or
  second-person pronouns; no final period, including on complete sentences;
  typographic apostrophes (`’`) and a single-character ellipsis (`…`).
- **Ellipsis rule.** An ellipsis marks only an action that opens further input
  or a confirmation. A control that carries the action out immediately never
  carries an ellipsis.
- **Copy migration.** Rewrite every string in `src/afanes/ui/strings.py` and
  `src/afanes/cli/strings.py`, including launch and validation messages, to the
  new rules. Command examples keep straight quotes because they are typed
  syntax, not prose.
- **Copy gate.** Add `tests/ui/test_copy.py`, which scans both catalogs. It
  fails on a straight apostrophe, a three-dot ellipsis, a trailing period, a
  first- or second-person pronoun, an ellipsis outside the declared
  further-input action set, and a copy constant without a declared
  capitalization style. The gate has no baseline: the migration lands at zero
  violations.
- **Tests become copy-agnostic.** Tests that assert literal copy read the
  catalog constants instead, so a later copy edit cannot break a behavioral
  test.
- **Documentation.** `AGENTS.md` 4.6 replaces the sentence-case transition note
  with the final rule. `docs/develop/interface-standard.md` gains a writing
  style section and marks wave 3 landed. Pages that quote changed labels are
  updated.

This is **BREAKING (copy)** only in the sense that visible labels change; no
API, file format, vault schema, or command name changes.

## Capabilities

### New Capabilities

None. The writing style is part of the existing interface standard.

### Modified Capabilities

- `interface-theme`: adds requirements for the interface writing style and the
  copy gate, covering both the interface and the command-line catalogs.

## Impact

- `src/afanes/ui/strings.py` and `src/afanes/cli/strings.py`: every user-facing
  string.
- `tests/ui/test_copy.py`: new gate; `tests/ui/test_template_cards.py` and any
  other test that asserts literal copy now reference the catalog.
- `AGENTS.md` 4.6, `docs/develop/interface-standard.md`, and the guide pages
  that quote changed labels.
- `CHANGELOG.md`: one `Unreleased` entry.
- No dependency, runtime, vault, schema, or command-name change. The shipped
  screenshots are refreshed with the wave 7 identity work rather than here; the
  change records that deferral.
