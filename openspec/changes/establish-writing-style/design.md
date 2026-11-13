# Design

## Context

See `proposal.md` - Why. The interface standard already names wave 3 and points
at `AGENTS.md` 4.6, which still says control labels use sentence case until the
writing-style wave lands. All interface copy lives in
`src/afanes/ui/strings.py`; all command-line copy lives in
`src/afanes/cli/strings.py`. Both modules are import leaves, and neither has an
automated style check today.

The visual gate in `tests/ui/test_conformance.py` uses a shrinking baseline and
counts token, button, and row violations. That model fits visual debt, not copy:
a style violation in a string is either fixed or it is not.

## Goals / Non-Goals

**Goals:**

- One written writing-style rule, with every catalog string migrated in this
  change.
- A deterministic copy gate with no baseline, scanning both catalogs.
- A classification that forces every future copy constant to declare whether it
  is header-case or sentence-case.
- Tests that survive copy edits by reading the catalog instead of literals.
- Documentation and `AGENTS.md` updated to the final rule.

**Non-Goals:**

- Translating copy or adding a locale catalog; that is the later
  internationalization change.
- Rewriting bundled template content or Markdown note text.
- Refreshing screenshots; wave 7 owns the identity pass.
- Changing layout, colors, icons, or control structure.
- Adding a grammar checker or an English lexicon.

## Decisions

### D1. Adopt the GNOME writing style verbatim, with two project stances

The HIG supplies the rules: header capitalization for headings and short
control labels, sentence capitalization for field labels and prose, ellipses
only for further input or confirmation, no final period, neutral tone, and
typographic marks. Two project choices tighten it:

- every first- and second-person pronoun is banned, including `your`, although
  the HIG allows `your` when ownership must be named; no current string needs
  it;
- the final period is removed from every string, including a one-sentence
  description, matching the HIG's "text generally shouldn't end with a period".

Alternatives considered:

- allow `your` as the HIG does: leaves a judgment call the gate cannot settle;
- keep periods on multi-sentence messages: produces mixed punctuation in the
  same view without a rule that explains which string keeps one.

### D2. Classify every copy constant explicitly

`tests/ui/test_copy.py` holds a `HEADER_CASE` set of constant names and a
`SENTENCE_CASE` set. Mapping names such as `WORKSPACE_SECTION_LABELS` are
classified as a unit. A completeness test asserts the two sets are disjoint
and cover every module-level string constant and every mapping value in both
catalogs. A future string without a classification fails the gate, so the
author must decide its role rather than inherit a default.

Alternatives considered:

- classify by name suffix (`_ACTION`, `_TITLE`, `_BODY`): many controls already
  break the suffix convention, and renaming dozens of constants would churn
  tests for no behavioral gain;
- infer the role from the view call site: indirect uses and helper functions
  make it brittle;
- classify by string length or sentence punctuation: guesses wrong on short
  field labels and long headings.

### D3. Split mechanical checks from capitalization checks

The gate reads both catalogs as ASTs and:

- applies the mechanical rules to every string literal except docstrings: no
  straight apostrophe, no three-dot ellipsis, no trailing period, no banned
  pronoun;
- applies the capitalization rules only to classified constants and mapping
  values;
- applies the ellipsis rule to every literal that ends with `…`.

This keeps format fragments, command names, and interpolated fields out of the
classification burden while still catching typography anywhere in the catalogs.

Alternatives considered:

- classify every literal, including `{title} - {description}` and `"afanes"`:
  noise with no behavioral value;
- scan only classified strings: misses typography in helper-built messages.

### D4. Validate header capitalization by violation, not by reconstruction

The checker flags a header-case string when:

- the first or last word starts lowercase;
- a word of four or more letters starts lowercase unless it is a short-word
  article, conjunction, or preposition (`a`, `an`, `the`, `and`, `or`, `of`,
  `to`, `in`, `on`, `for`, `with`, and similar);
- either part of a hyphenated word starts lowercase;
- a short-word article, conjunction, or preposition in the middle starts
  uppercase.

It does not attempt to identify short nouns and verbs, so a lowercase
three-letter content word in the middle of a label is a manual-review catch.
The HIG's noun/verb rule needs a lexicon, and a project-maintained lexicon
would drift faster than it would help.

Alternatives considered:

- rebuild the expected string and compare: forces a lexicon for every short
  content word;
- a third-party grammar checker: a new dependency and an offline risk for a
  rule the project can state plainly.

### D5. Ellipsis is an explicit action allowlist

The gate requires every string ending in `…` to appear in an
`ELLIPSIS_ACTIONS` set, and every member of that set to end in `…`. The set is
built by auditing each control's handler: an initiating control that opens a
dialog, form, confirmation, or native picker gets the ellipsis; the affirmative
control inside that surface does not, because it completes the action.

Examples: **New Vault…**, **Move to Trash…**, **Set Plan Date…**. Not:
**Capture**, **Refresh**, **Start Review**, **Back**, or a navigation
destination. The search placeholder loses its current ellipsis because it is
not an action.

Alternatives considered:

- mark actions in the view code: adds a parallel flag that can disagree with
  the label;
- infer from the handler: the gate would need to execute UI code.

### D6. Keep the copy gate separate from the visual conformance gate

`tests/ui/test_conformance.py` stays the visual token and control gate. The new
`tests/ui/test_copy.py` owns copy. The two have different failure models: the
visual gate may carry a shrinking baseline for unmigrated views, while copy must
be at zero immediately.

Alternatives considered:

- fold copy into `test_conformance.py`: mixes a baseline ledger with a
  zero-tolerance rule and makes the visual gate harder to read;
- a lint rule in Ruff: no Ruff rule understands the catalog's classification or
  ellipsis allowlist.

### D7. Typographic apostrophes are mandatory; command examples stay literal

Every contraction and possessive uses U+2019. Text that quotes an interpolated
value uses typographic quotation marks. A command example such as
`"pip install afanes[desktop]"` keeps straight quotes because the characters are
typed syntax, and the gate bans only the straight apostrophe and three-dot
ellipsis, not the straight double quote.

Alternatives considered:

- typographic quotes everywhere: makes copyable commands wrong;
- ban the straight double quote too: would reject the command examples.

### D8. Tests read the catalog, not literal copy

Tests that currently compare rendered text with a hardcoded phrase import the
catalog constant instead. A copy edit should not fail a behavioral test, and a
test that hardcodes copy silently duplicates the catalog.

Alternatives considered:

- keep literal assertions and update them here: works once, then breaks again on
  the next copy change;
- assert only non-empty text: loses the check that the right message appears.

### D9. Update the durable documents; defer screenshots

`AGENTS.md` 4.6 drops the sentence-case transition note and states the final
rule plus the gate. `docs/develop/interface-standard.md` gains a writing-style
section, records the copy gate, and marks wave 3 landed. Guide pages that quote
a changed label are updated. Screenshots keep their current labels and are
refreshed with wave 7, when the palette and identity settle; the change records
that deferral instead of leaving it silent.

Alternatives considered:

- refresh screenshots now: a second refresh is likely in wave 7;
- leave the standard untouched: `AGENTS.md` would point at a stale wave.

## Risks / Trade-offs

- [The bulk copy edit breaks tests or docs] -> Run the full suite and the docs
  build; convert literal assertions to catalog references before changing the
  strings.
- [Header capitalization is applied to field labels or prose] -> The explicit
  classification forces a per-constant decision, and the standard includes
  examples for each role.
- [The gate misses a lowercase short content word] -> Record the limit in the
  standard and review those words manually; do not add a drifting lexicon.
- [An ellipsis lands on an action that completes immediately] -> The allowlist
  is audited against the handlers, and the spec's immediate-action scenario
  pins the rule.
- [The gate rejects a legitimate exception later] -> A new exception requires a
  standard change with the reason, the same rule the visual gate follows.
- [Internationalization later moves the catalogs] -> The classification and
  mechanical rules move with the catalog; the i18n change owns that migration.
- [Visible labels change while screenshots stay old] -> Record the wave 7
  deferral in the change and the standard.

## Migration Plan

1. Convert tests that assert literal copy to catalog references.
2. Rewrite `src/afanes/ui/strings.py` and `src/afanes/cli/strings.py`:
   capitalization, periods, pronouns, apostrophes, ellipses.
3. Add `tests/ui/test_copy.py` with the classification sets and the mechanical,
   capitalization, ellipsis, and completeness checks.
4. Update `AGENTS.md` 4.6 and `docs/develop/interface-standard.md`; sweep the
   guide pages that quote changed labels.
5. Run `hatch check`, `hatch test --cover`, `hatch run docs:build`, the OpenSpec
   validation, and the vocabulary greps.
6. Rollback is a copy revert; no vault, schema, API, or dependency migration
   happens in this change.
