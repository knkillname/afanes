# Design

## Context

See `proposal.md` - Why. `LanguageMenu` in
`src/afanes/ui/components/language.py` is shared by the welcome state and the
workspace primary menu. Both pass `AppShell.set_language`, an asynchronous
method that writes `~/.config/afanes/settings.json` and shows the restart
toast.

Flet 1.1.2 awaits an event handler only when the handler is a coroutine
function. A synchronous handler that returns a coroutine is called, its result
is discarded, and Python emits the "never awaited" warning recorded in the
packaged run. The existing test awaited the returned coroutine itself, so it
passed while the application path stayed broken.

## Goals / Non-Goals

**Goals:**

- Restore the specified override behavior in both menus with the smallest
  change.
- Make the dispatch contract explicit so a sync wrapper cannot silently
  disable the menu again.
- Add a regression test that fails if a handler stops being a coroutine
  function.

**Non-Goals:**

- Changing locale resolution, the preference file format, or the set of
  supported languages.
- Switching copy in the running session, which the spec forbids.
- Adding a Flet integration harness; the suite uses a fake page and does not
  run the toolkit dispatcher.

## Decisions

### D1. Make the handlers coroutine functions

Define `_choose_english`, `_choose_spanish`, and `_choose_system` as
`async def` and `await self.on_select(...)`. Flet then awaits the handler and
runs the preference write.

Alternatives: calling `page.run_task` from a sync handler (needs page access in
a value object and hides the contract), or wrapping the callback in a
`functools.partial` (still synchronous, so Flet discards it).

### D2. Require an awaitable callback

Change `LanguageMenu.on_select` to
`Callable[[str | None], Awaitable[None]]` and update the `on_language`
annotations in `afanes.ui.views.inbox` and `afanes.ui.views.workspace`.
Every call site passes the asynchronous `AppShell.set_language`.

Alternatives: keep the optional union and await conditionally. That tolerates a
sync callback but preserves the exact shape that caused the defect, so the type
gate would no longer catch a future regression.

### D3. Pin the dispatch rule in the test

Extend the language test to assert `inspect.iscoroutinefunction(item.on_click)`
for the English, Spanish, and system items, then choose each one and assert the
written preference. This mirrors what Flet checks, without adding a toolkit
dependency to the UI tests.

Alternatives: an end-to-end render test (heavier, and the suite deliberately
avoids a display), or relying on the existing preference assertion (it awaits
the return value and therefore cannot catch this class of defect).

## Risks / Trade-offs

- **Flet's dispatch rule changes.** The coroutine-function assertion pins the
  current contract; updating Flet would update both the handler shape and the
  test in one place.
- **A future caller passes a sync function.** The tightened annotation turns it
  into a type error at the call site instead of a silent no-op.
- **The preference write can still fail.** That path already reports a toast in
  the active locale and leaves the file unchanged; this change does not alter
  it.
