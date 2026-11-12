# Design

## Context

`docs/api/models.md`, `core.md`, and `vault.md` generate their content from `src/afanes/` docstrings.
The pages use MyST Markdown with `{automodule}` directives. MyST's directive state parses a directive
body with the Markdown parser, so the reStructuredText that `sphinx.ext.autodoc` generates is treated
as Markdown. The rendered page contains paragraphs such as `.. py:class:: NoteType(*values)` and
indented code blocks that begin with `.. attribute:: NOTE`.

`docs:build` uses `-W`, but the malformed page emitted no warning, so the gate never noticed.

## Goals

- Render the API reference as a normal Sphinx Python domain: class signatures, attributes, methods,
  parameters, returns, and raised exceptions.
- Keep the documentation build local and offline.
- Keep `nitpicky` meaningful for Afanes references instead of turning it off.
- Add a regression check that fails before the page can silently become literal text again.

## Non-Goals

- Changing docstring content beyond broken cross-references.
- Adding `sphinx.ext.intersphinx`, a vendored Python inventory, or a network fetch.
- Renaming or converting `docs/api/*.md` to reStructuredText source files.
- Publishing API pages for the in-flight template-card module; that belongs to its own change.

## Decisions

### Use `{eval-rst}` around each `automodule`

MyST documents `{eval-rst}` as the way to parse a directive body as reStructuredText. The generated
autodoc content is RST, so the fence is applied around `.. automodule::` and its options. This keeps
the page in Markdown, keeps the existing heading and toctree structure, and requires no new
extension.

Converting the API pages to `.rst` would also work, but it would split the documentation source
format, bypass the Markdown heading checks in `tests/docs/test_style.py`, and add unnecessary churn.

### Document PEP 695 aliases with `.. autotype::`

`automodule` recognizes `PageDraft`, `PageContent`, and `BodyBlock` as aliases but creates no Python
domain target for them. `.. autotype::` renders the alias value and creates a `py:type` target that
`py:class` cross-references can fall back to. This is better than ignoring three real Afanes
references and also fills a gap in the API reference.

### Ignore only standard-library targets

The API pages annotate parameters with `pathlib.Path`, `datetime.date`, `enum.StrEnum`, and
`collections.abc` types. Resolving those targets requires an intersphinx inventory; fetching one at
build time would break the offline rule, and vendoring one would add a large, versioned binary file
for no Afanes behavior. The change adds `nitpick_ignore_regex` entries scoped to those external
types. An unresolved Afanes target remains a build error.

### Fix internal references instead of ignoring them

The real RST parse exposes five incorrect cross-references: `VaultSnapshot` names the wrong module,
`BASE_LOCALE` points at an undocumented constant, `UnparsedPage` is unqualified in `Vault`, and
`NoteType.REFERENCE` and `Vault.create` are not resolvable as written. The change fixes the
references so the API pages link to the real targets. `nitpick_ignore` is not used for Afanes names.

### Put the regression check in the docs style test

The test suite runs without the documentation dependencies, and a full Sphinx build is too heavy for
a unit test. `tests/docs/test_style.py` already parses Markdown fences with `markdown_it`. The new
test rejects a `{automodule}` fence under `docs/api/`, which is the exact authoring mistake that
produces literal autodoc output. The `docs:build` gate continues to catch unresolved references.

## Risks and Tradeoffs

- `{eval-rst}` adds a nested fence and indentation to each API module. The gain is correct rendering
  with no new dependency.
- `.. autotype::` depends on Sphinx 9.2.0, which is already pinned in the `docs` dependency group.
  A future Sphinx upgrade must keep it; the docs build will fail loudly if the directive disappears.
- The chapter-level `nitpick_ignore_regex` list must stay narrow. It names standard-library types,
  not a catch-all pattern, so an Afanes reference cannot accidentally match it.

## Verification

- `hatch run docs:build` completes with warnings as errors.
- The built `api/models.html`, `api/core.html`, and `api/vault.html` contain Python domain entries and
  no literal `.. py:` or `.. attribute::` text.
- `hatch test tests/docs/test_style.py` passes, including the new authoring check.
- `hatch check` and `hatch test --cover` pass.
