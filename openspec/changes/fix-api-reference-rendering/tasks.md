# Tasks

## 1. Render the API reference as reStructuredText

- [x] 1.1 Wrap every `{automodule}` in `docs/api/models.md`, `docs/api/core.md`, and
  `docs/api/vault.md` in an `{eval-rst}` fence so the autodoc output is parsed as RST.
- [x] 1.2 Add `.. autotype::` entries for the public aliases `PageDraft`, `PageContent`, and
  `BodyBlock` next to their modules.
- [x] 1.3 Build the docs and confirm `api/models.html`, `api/core.html`, and `api/vault.html` contain
  Python domain entries and no literal `.. py:` or `.. attribute::` text.

## 2. Resolve the warnings exposed by the real parse

- [x] 2.1 Add targeted `nitpick_ignore_regex` entries in `docs/conf.py` for the standard-library
  types (`Path`, `pathlib`, `datetime.date`, `enum.StrEnum`, `collections.abc`, and
  `importlib.resources.abc`); keep Afanes references strict.
- [x] 2.2 Correct the `VaultSnapshot` module path in `src/afanes/core/search.py`, the `BASE_LOCALE`
  reference in `src/afanes/core/templates.py`, and the `UnparsedPage`, `NoteType.REFERENCE`, and
  `Vault.create` references in the vault service and page modules.

## 3. Guard the authoring rule

- [x] 3.1 Extend `tests/docs/test_style.py` to reject a bare `{automodule}` fence in `docs/api/`.

## 4. Document and record the change

- [x] 4.1 Add the `{eval-rst}` and `.. autotype::` rules to `docs/develop/documentation.md`, and
  note the new check in its checks table.
- [x] 4.2 Record the rendered API reference fix under `Unreleased` in `CHANGELOG.md`; record that
  `README.md` needs no change and no version bump is warranted.

## 5. Verify and commit

- [x] 5.1 Run `hatch run docs:build` and confirm it completes with warnings as errors. When unrelated
  in-flight work is present in the working tree, build this change from a clean copy of the tree.
- [x] 5.2 Run `hatch test tests/docs/test_style.py` and `hatch test --cover`.
- [x] 5.3 Run `hatch check`.
- [x] 5.4 Run `openspec validate --all --strict` and `openspec doctor`.
- [x] 5.5 Run the vocabulary compliance greps from `AGENTS.md` section 6.1.
- [x] 5.6 Commit the change with a subject that names the delivered behavior, keeping the in-flight
  work out of the commit.
