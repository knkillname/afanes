# Design

## Context

See `proposal.md` - Why. Measured from the current `src/afanes/ui/state.py`:

| Class | Fields | Properties | Setters | Public commands | Class lines |
| --- | --- | --- | --- | --- | --- |
| `AppState` | 7 | 44 | 29 | 69 | 2802 |
| `VaultSession` | 8 | 1 | 0 | 7 | 192 |
| `BrowserState` | 3 | 0 | 0 | 5 | 79 |
| `PageEditorState` | 15 | 0 | 0 | 0 | 52 |
| `ProcessingState` | 6 | 0 | 0 | 0 | 24 |
| `ReviewState` | 6 | 0 | 0 | 0 | 24 |

`AppState` has 77 public names. Only six are unreferenced by `ui/views/` and
`ui/app.py`: `page_is_new`, `preview_body`, `reset`, and `session_active`
(each inflating the count because a property and its setter share a name).
So pruning does not solve the problem; the surface is genuinely used.

## Goals / Non-Goals

**Goals:**

- Make the gate fail when the state object graph grows without ownership.
- Put each command on the object that owns the data it mutates.
- Turn `ui/state.py` into the `ui/state/` package, one module per controller.
- Leave every user-visible behavior and every spec scenario unchanged.

**Non-Goals:**

- Rewriting the views beyond mechanical call-site changes.
- Changing what the UI shows, how it refreshes, or when it autosaves.

## Decisions

### D1. Enforce public surface, not just annotated fields

Count, per class, the distinct public names defined in the class body:
properties (getter and setter count once), public methods, and public async
methods. `AppState` also keeps the existing 10-field budget.

Confirmed budgets:

- `AppState`: at most 10 public names.
- Any one collaborator: at most 25 public names.
- Every collaborator that declares state fields must define at least one
  command (public method or async method). A zero-command collaborator fails,
  which is exactly the anemic-bag rule in `AGENTS.md` 4.3. `UiStatus` is
  included: its message, busy, and session flags become commands, so it stops
  being a plain flag holder.

The last rule is the important one. It converts "this class has no behavior"
from a review comment into a failing test.

### D2. Expose domain controllers instead of forwarding every command

`AppState` keeps the shared `UiStatus`, the command lock, and five domain
controllers. Views call through the controller:

```
before                              after
app_state.vault .................. app_state.session.vault
app_state.start_review() .......... app_state.review.start()
app_state.save_page() ............. app_state.pages.save()
app_state.set_browser_query(q) .... app_state.browser.set_query(q)
app_state.begin_processing(p) ..... app_state.processing.begin(p)
```

The alternative - keep `AppState.<command>` as a thin delegator - was rejected:
the delegator is itself a public name, so the surface stays at 77 no matter how
much behavior moves, and the gate would measure the same thing it measures now.

### D3. Move behavior with the data

- `VaultSession` owns the vault service, the scan snapshot, selection, preview,
  and the snapshot-only commands: `capture`, `select_note`, `note_title`,
  `assignment_candidates`, `template_summaries`, and `vault_root`.
- `WorkspaceController` owns `start`, open/choose/create/close/change, and both
  refresh commands, because each one resets or reconciles more than one domain.
- `BrowserState` already owns section and query; it keeps the two setters.
- `PageEditorState` owns the draft, editing mode, save, autosave, the page
  queries, the leave guard, and the pending repair offer.
- `PageNavigator` owns `open_page`, `back`, `follow_link`, `open_failure`,
  `ambiguous`, and the history stack.
- `PageDialogState` owns label, type, and category confirmations, conflict
  recovery actions, repair actions, unresolved-link actions, and the
  rename/trash previews. The page domain exceeds the 25-name budget in one
  class, so it splits by ownership: the editor owns the open draft, the
  navigator owns movement, and the dialog state owns transient confirmations.
- `ProcessingState` gains begin, plan, apply, cancel, finish, and the
  append-step target search.
- `ReviewState` gains the review queue commands.
- `UiStatus` owns `show_message`, `clear_message`, `set_busy`,
  `begin_session`, `release_session`, and `reset`; no collaborator writes its
  flags directly.

Composition direction stays acyclic: `PageEditorState` depends on
`VaultSession`; `PageNavigator` depends on `PageEditorState`; `PageDialogState`
depends on `PageNavigator` and `PageEditorState`; `BrowserState` and
`ProcessingState` depend on `VaultSession`; `ReviewState` depends on
`PageNavigator`, `PageEditorState`, `ProcessingState`, and `BrowserState`;
`WorkspaceController` depends on every domain; `AppState` depends on all of
them. Nothing depends on `ReviewState` or `WorkspaceController` except
`AppState`.

### D4. Remove only provably unused public names

After the move, delete a public name only when `ui/views/`, `ui/app.py`, and
`tests/` do not reference it. `reset` stays for tests. `page_is_new` and
`preview_body` are candidates for removal or folding into a command; the design
does not assume they go until the call-site audit confirms it.

### D5. Package layout and singleton

`ui/state.py` becomes `ui/state/`:

```
ui/state/
  __init__.py     defines app_state and nothing else
  lock.py         CommandLock
  status.py       UiStatus
  session.py      VaultSession
  browser.py      BrowserState
  pages.py        PageEditorState
  navigation.py   PageNavigator
  dialogs.py      PageDialogState
  processing.py   ProcessingState
  review.py       ReviewState
  workspace.py    WorkspaceController
  controller.py   AppState
```

`__init__.py` imports `afanes.ui.state.controller`, constructs it, and binds
`app_state`. It does not bind `AppState`, so the package front door is not a
re-export. Tests and any other code that needs the type import it from
`afanes.ui.state.controller`, which the import rules already allow for a
class. Every view keeps using `afanes.ui.state.app_state`.

The alternative - putting `AppState` in `__init__.py` - was rejected because it
would make the front door hold machinery, and the rulebook asks for a thin
package init.

### D6. Test shape

Extend `tests/core/test_architecture.py`:

- Parse `ui/state/controller.py` for the `AppState` field budget (existing
  test, repointed).
- Parse every module in `ui/state/` for public-name counts and the
  collaborator-owns-a-command rule.
- Scan the whole `ui/state/` package in `test_state_does_not_import_views_or_components`
  instead of the single file.
- Assert `ui/state/__init__.py` binds `app_state` and does not bind
  `AppState`, which encodes D5.
- Keep the existing import-boundary tests untouched.

`tests/ui/test_state.py` is rewritten only where the command moved; assertions
and fixtures stay, mirroring the code move one-for-one.

### D7. Split the page domain by ownership

The page domain has more than twenty-five public names once the view-facing
commands move onto it. It splits three ways:

- `PageEditorState` - the open draft, save, autosave, the page queries, the
  leave guard, and the pending repair offer.
- `PageNavigator` - opening, back/history, link following, opening an
  unreadable note, and the ambiguous-candidate picker. It depends on the
  editor and never on the dialog state.
- `PageDialogState` - label, type, and category confirmations, conflict
  recovery actions, repair actions, unresolved-link actions, and rename/trash
  previews. It may depend on the navigator.

The pending repair offer stays with the editor that produces it, so navigation
never imports the dialog state; otherwise the two would form an import cycle.
The editor exposes a `blocking_message` field that the dialog state sets while
a confirmation is pending, so `commit()` can refuse to leave the page without
importing the dialogs.

### D8. Add a workspace coordinator

`AppState` keeps no lifecycle or refresh behavior. `WorkspaceController` owns
`start`, `choose_vault`, `open_vault_path`, `open_vault_for_run`,
`create_vault`, `close_vault`, `change_vault`, `refresh`, and
`refresh_workspace`, because each command either resets several domains or
reconciles a scan with the open page. It sits at the top of the domain graph and
is the only place that clears the page, navigation, dialog, processing, review,
and browser state when the vault changes.

The alternative - letting `VaultSession` depend on the higher domains - reverses
the composition direction and creates an import cycle.

### D9. Share one command lock

Every mutating command keeps `async with self.command_lock:`. A small
`CommandLock` service owns the `asyncio.Lock`, exposes the async context
manager, and replaces the underlying lock in `replace()`. `AppState.reset()`
calls `replace()` so a new event loop starts with a clean lock. Passing the
shared object matches the existing shared `UiStatus` value and preserves the
one-writer-per-vault rule across every controller.

### D10. Cap the facade by fields plus commands

Controllers are public data fields on `AppState`; no getter methods are added.
The existing field budget allows ten annotated fields, and the new combined
check requires annotated fields plus public command names to stay at or below
ten. Today that is nine collaborator fields plus `reset`, so the facade has no
room to grow without a conversation. Domain controllers keep their separate
twenty-five-command budget and are not charged for their data fields.

### D11. Reach status through `app_state.status`

`AppState` exposes `status` as its ninth collaborator. Views read
`app_state.status.message` and call `app_state.status.show_message(...)`.
Keeping read-only forwarding properties on `AppState` would add names and
duplicate the owner.

### D12. Views keep one reference

Views keep `self._state = afanes.ui.state.app_state` and navigate one hop to the
owning controller (`self._state.pages.save()`). They do not cache controllers,
so `reset()` never leaves a stale reference.

## Risks / Trade-offs


- [Large mechanical diff across views and tests] -> Land in one commit per
  domain (session, pages, processing, review, browser) so each step is
  reviewable and reversible.
- [Circular imports among controllers] -> D3 fixes the direction; the
  architecture test's cycle check already fails on a violation.
- [Budgets block legitimate work] -> The numbers are confirmed but still
  reviewable if a real command cannot fit; the gate's purpose is to force the
  conversation, not to make work impossible.
- [Tests that poke `_state` attributes] -> The audit found six unreferenced
  names; any test reaching into a private field is migrated with the command
  that used it.
- [Package extraction churns imports] -> Only the type name `AppState` moves;
  `app_state` keeps its path. The move is mechanical and caught by the type
  checker.

## Migration Plan

1. Add the new gate tests against the current code with a temporary allowlist
   equal to today's counts.
2. Extract the `ui/state/` package with the classes unchanged and `app_state`
   at the front door; run the UI tests to prove no behavior moved.
3. Add `CommandLock`, `WorkspaceController`, and `PageNavigator` shells, wire
   them into `AppState`, and switch the remaining `AppState` commands to the
   shared lock.
4. Move one domain at a time; shrink its allowlist entry with the move. Land
   the coordinator and navigation moves before the dialogs, because the dialogs
   depend on both.
5. Delete the allowlist when it reaches zero; the final state has no
   exemptions.
6. Run `hatch check`, `hatch test --cover`, and the UI tests after each domain.

This mirrors the allowlist pattern the repository already used for
`refactor-cohesive-oop`, so reviewers have seen the shape before.

## Open Questions

Resolved during implementation:

- **Reset direction:** `WorkspaceController` owns lifecycle and refresh; no
  domain calls upward.
- **Command lock:** one shared `CommandLock`; `reset()` replaces its internal
  lock.
- **Status reach:** views use `app_state.status`; there are no forwarding
  properties.
- **Page budget:** the page domain splits into editor, navigator, and dialogs
  instead of raising the 25-name budget.
- **Snapshot commands:** all six stay on `VaultSession`.
- **Reset:** each controller resets its own fields; `AppState.reset()` walks
  them.
- **Repair prompt:** the pending offer lives on the editor so navigation never
  imports dialogs.
- **Facade metric:** annotated fields plus public command names must be at most
  ten.
- **View access:** views keep one `app_state` reference and navigate to the
  owning controller.
