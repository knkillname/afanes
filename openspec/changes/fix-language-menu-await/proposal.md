# Proposal

## Why

The language menu in the packaged `0.14.0` build does nothing. Choosing
English or Spanish neither writes the preference nor shows the restart toast:
`~/.config/afanes/settings.json` keeps no `language` key, and the application
log records `RuntimeWarning: coroutine 'AppShell.set_language' was never
awaited`.

`openspec/specs/interface-localization/spec.md` already requires the override
("An override applies on the next launch"), so this is an implementation defect,
not a missing capability. It fails the language row of the `1.0.0` gate and
blocks that release.

## What Changes

- Make the three `LanguageMenu` handlers coroutine functions that await the
  selection callback. Flet awaits a handler only when the handler itself is a
  coroutine function; the current sync wrappers return a coroutine that is
  discarded.
- Tighten the callback contract from
  `Callable[[str | None], Awaitable[None] | None]` to
  `Callable[[str | None], Awaitable[None]]` in `LanguageMenu` and the two view
  action records, because every call site passes the asynchronous
  `AppShell.set_language`. The optional form invited the sync-return mistake.
- Fix the regression test that awaited the handler's return value directly,
  which is what the application does not do. Assert instead that each menu
  item's `on_click` is a coroutine function and that choosing each option
  writes the expected preference.
- No interface copy, theme, layout, dependency, vault-format, or version change.
  The changelog entry stays under `Unreleased`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `interface-localization` already requires the override and the restart
behavior; this change restores the specified behavior without changing the
contract, so it sets `skip_specs: true`.

## Impact

- `src/afanes/ui/components/language.py`: handlers and callback type.
- `src/afanes/ui/views/inbox.py` and `src/afanes/ui/views/workspace.py`:
  callback annotations.
- `tests/ui/test_app.py`: language-menu regression tests.
- `CHANGELOG.md`: one `Unreleased` entry. README: no change required
  (documented behavior is unchanged). Docs: no change required.
