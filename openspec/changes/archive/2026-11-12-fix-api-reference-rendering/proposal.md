# Proposal

## Why

The generated API reference pages (`docs/_build/html/api/models.html`, `core.html`, and `vault.html`)
show autodoc markup as literal text. A reader sees `.. py:class:: NoteType(*values)` in a paragraph
and `.. attribute:: NOTE` above an indented code block instead of a class signature and an attribute
entry. The build succeeds, so the failure is invisible to the current gate.

MyST parses the body of a directive as Markdown. `{automodule}` runs `sphinx.ext.autodoc`, which
generates reStructuredText, and MyST then parses that generated RST as Markdown. The generated
`.. py:class::`, `.. attribute::`, and `:type:` lines become paragraphs and code blocks rather than
doctree nodes.

## What Changes

- Wrap every `{automodule}` in `docs/api/models.md`, `docs/api/core.md`, and `docs/api/vault.md` in an
  `{eval-rst}` fence, so Sphinx parses the generated content as reStructuredText.
- Document the three public PEP 695 type aliases (`PageDraft`, `PageContent`, and `BodyBlock`) with
  `.. autotype::`. `automodule` sees the aliases but creates no target for them, and their
  cross-references fail under `nitpicky`.
- Add targeted `nitpick_ignore_regex` entries in `docs/conf.py` for standard-library types (`Path`,
  `pathlib`, `datetime.date`, `enum.StrEnum`, `collections.abc`, and `importlib.resources.abc`). The
  documentation builds offline without an intersphinx inventory, so those targets cannot resolve.
  Afanes targets remain strict.
- Correct the docstring cross-references that the real RST parse exposes: the `VaultSnapshot`
  reference names its module, `BASE_LOCALE` is literal, and `UnparsedPage`, `NoteType.REFERENCE`, and
  `Vault.create` use fully qualified targets.
- Extend `tests/docs/test_style.py` to reject a bare `{automodule}` fence under `docs/api/`.
- Document the `{eval-rst}` rule and the `autotype` addition in `docs/develop/documentation.md`.
- Record the fix under `Unreleased` in `CHANGELOG.md`. No version bump and no `README.md` change.

Out of scope: changing the public Python API, adding an intersphinx dependency or inventory,
converting the API pages to `.rst`, adding a second documentation build tool, and the in-flight
template-card API page.

## Capabilities

### New Capabilities

None. This is a documentation and docs-testing change with no product behavior change, so the
change sets `skip_specs: true` instead of inventing a requirement.

### Modified Capabilities

None.

## Impact

- `docs/api/*.md` change from bare `automodule` directives to `{eval-rst}` fences and gain
  `autotype` entries for public aliases.
- `docs/conf.py` gains standard-library-only `nitpick_ignore_regex` entries; `nitpicky` stays on for
  Afanes references.
- Five source docstrings get corrected cross-references. No signature, behavior, or public name
  changes.
- `tests/docs/test_style.py`, `docs/develop/documentation.md`, and `CHANGELOG.md` change.
- No runtime dependency, network access, application behavior, vault format, CLI, UI, or version
  change. The docs build remains local and offline.
