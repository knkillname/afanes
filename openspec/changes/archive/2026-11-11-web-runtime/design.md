# Design

## Context

See `proposal.md` - Why for the motivation. The following verified facts shape the approach.

- `src/afanes/__main__.py` calls `ft.run(afanes.ui.app.main)` with no options, which selects
  `AppView.FLET_APP` and the desktop client.
- Flet forces the web server when `FLET_FORCE_WEB_SERVER` is set or when it detects a headless Linux
  host. So the web transport is already reachable today without anyone asking for it, and it is
  broken: `FilePicker.get_directory_path()` raises `FletUnsupportedPlatformException` in web mode,
  which is the only action the welcome state offers.
- When a runtime package is missing or its version differs from the SDK, Flet runs `pip install` in
  a subprocess at startup and exits the process with status 1 if that fails.
- `no_cdn` defaults to `False`, which loads CanvasKit, Pyodide, and fonts from a remote origin.
- The `flet-web` wheel bundles CanvasKit, Pyodide, and the fonts (about 30 MB), so local asset
  serving needs no extra work at runtime.
- `page.web` is a boolean set before the application's `main` runs. `page.window` exists in both
  presentations but is ignored by the browser client.
- A browser file dialog cannot return a directory path. `FilePickerFile.path` is documented as
  `None` in web mode and `name` is a basename only, so content is available and location is not.
- `AppState` is a module-level singleton shared by every session in the process. Its `_lock`
  serializes state mutations, but an edit view pushes body changes into `state.page` through
  `change_body`, so two sessions would overwrite each other's draft.
- `build_welcome` currently renders exactly one `FilledButton`, and `tests/ui/test_app.py` asserts
  that shape.
- `ui/strings.py` imports no other `ui/` module, so the entry point can read launch messages from it
  without importing Flet indirectly.

## Goals / Non-Goals

**Goals:**

- The browser presentation is reachable on demand, works with no native client, and is honest about
  what it does not support.
- Starting Afanes with no options is byte-for-byte the same experience as before.
- No code path installs packages, downloads a client, or requests a remote asset while starting.
- The vault cannot be reached from another host.

**Non-Goals:**

- Serving more than one person. No accounts, no sessions per user, no TLS.
- Deploying behind a reverse proxy or exporting an ASGI application.
- Replacing the browser's inability to see directories with a server-side directory browser.
- Making the desktop client optional at import time.

## Decisions

### Decision: an explicit `--web` flag, parsed by `argparse` in the entry point

`__main__.py` gains `--web`, `--vault DIR`, and `--port N`, parsed by `argparse` into a frozen
`LaunchOptions` value with `parse_launch_options(argv: Sequence[str]) -> LaunchOptions` as a pure
function that tests can call without a display.

Alternatives considered:

- A `serve` subcommand: rejected. There is one alternative presentation, and a flag leaves
  `python -m afanes` unchanged.
- An environment variable such as `AFANES_VIEW`: rejected as a hidden interface that is harder to
  discover and to document than a flag.
- Automatic fallback when the desktop client fails: rejected for this change. Detecting a blocked
  client is unreliable (the binary may be quarantined, the download may hang, or the process may be
  killed), and a silent presentation switch hides a real failure. The desktop failure path names
  `--web` instead, which a launcher script can adopt.

### Decision: runtime availability is checked before Flet starts

The entry point checks `importlib.util.find_spec("flet_web")` or `"flet_desktop"` according to the
selected presentation before calling `ft.run`, and exits with status 1 and a message naming the
install command when the check fails. The interface modules are imported inside the entry function
rather than at module scope, wrapped in `try`/`except ModuleNotFoundError`, so a missing SDK becomes
the same one-line message instead of an import traceback. The import is a deliberate availability
check, not an attempt to hide a dependency cycle, and it carries a `noqa` explaining that.

This is deliberately placed before `ft.run`, because Flet's own guard installs a replacement package
from the network and then exits without a useful message.

Alternatives considered:

- Letting Flet's `ensure_*_package_installed` handle it: rejected, it is a runtime network call and
  a process exit the application cannot control.
- A hard dependency on both runtime packages: rejected, it defeats the purpose for web-only and
  desktop-only environments.

### Decision: presentation detection through `page.web`

`ui/app.py` computes `is_desktop = not page.web` once and uses it for two things: skipping the
`page.window` assignments, and choosing which vault selection action the welcome state receives.
Views do not receive the page object, so the welcome builder takes explicit callbacks rather than
reading presentation state.

```python
def build_welcome(
    on_choose: Callable[[], Awaitable[None]] | None,
    on_open_path: Callable[[str], Awaitable[None]] | None,
) -> ft.Control: ...
```

Exactly one callback is supplied per presentation. The desktop call keeps the current single
`FilledButton`; the browser call renders an `ft.TextField` plus an `Open` button. Both route into
`AppState.choose_vault`, so path resolution and validation stay in one place.

Alternatives considered:

- Detecting presentation inside the view: rejected, it would make views read Flet page state and
  complicate the existing no-page unit tests.
- A server-side directory browser: rejected for this change as disproportionate work (permissions,
  drive letters, large directories) for a fallback presentation.

### Decision: `--vault` applies to one run and is validated before the UI starts

`--vault` resolves to an absolute path and is validated against the same rules as a chosen vault. A
valid path opens that vault for the run and is never written to settings. An invalid path prints the
reason to standard error and exits with status 1, because the caller is a launcher and there is no
one watching a window to correct it.

Precedence is `--vault`, then saved settings, then the welcome state.

Alternatives considered:

- Persisting a supplied vault: rejected. A launcher passing a path for one run should not silently
  rewrite the user's remembered preference.
- Falling back to the welcome state on an invalid path: rejected, it turns a configuration error
  into a UI state nobody can diagnose from a log.

### Decision: one active workspace session, released on disconnect

`AppState` gains an active-session marker. A page asks to begin a session before it starts the
controller; when the marker is set, the page renders a notice explaining that another window is
active and never scans or writes the vault. The marker is cleared from `page.on_disconnect`.

No takeover action is offered. A stale tab can still deliver events after another tab claims the
session, so a takeover button would imply isolation the shared controller cannot provide. Closing
the active tab is the only release path.

Alternatives considered:

- Per-session controller state: rejected as a large refactor of a controller that is intentionally a
  singleton with a single vault and a single settings file.
- Documenting the hazard and doing nothing: rejected because `change_body` pushes one tab's draft
  into shared state, so the loss is real and silent.

### Decision: loopback-only binding with a configurable port

`ft.run` is called with `host="127.0.0.1"`, `no_cdn=True`, and the parsed port (default `0`, an
automatically chosen free port). There is no option to change the host.

Alternatives considered:

- A `--host` flag: rejected. Without accounts or TLS it would publish read and write access to the
  user's notes on the local network, which contradicts the offline, single-user product principles.
- Leaving `host` unset: rejected because the guarantee would then depend on Flet's default rather
  than on Afanes' own contract.

### Decision: tests assert launch options, not a running server

The default suite mocks `ft.run` and asserts the exact keyword arguments for each presentation, and
drives the welcome variants and session guard through the existing fake page. No test binds a port
or renders a browser; browser rendering is not observable headlessly, and a server smoke test would
add a flake source without covering Afanes' own code. End-to-end browser verification is a manual
task in `tasks.md`.

## Risks / Trade-offs

- A browser tab that dies without firing disconnect leaves the session marker set → Mitigation: the
  notice offers reload, the marker is process-scoped, and restarting the process clears it. The
  window is small because the presentation is local and single-user.
- `page.web` could report incorrectly for an embedded view → Mitigation: the desktop branch is the
  default, so a wrong `False` degrades to the current behavior rather than breaking a new path.
- The path field accepts a relative path and resolves it against the server's working directory,
  which a browser user cannot see → Mitigation: the field label asks for an absolute path, and the
  same validation rejects anything that does not resolve to a readable directory.
- `--vault` failing hard means a launcher typo produces no window → Mitigation: the message goes to
  standard error with the rejected path, which is what a launcher log needs.
- Loopback binding means a user cannot open the browser from another machine → Accepted; remote
  access is explicitly out of scope.

## Migration Plan

1. Land the `relax-dependency-pins` change so the `web` and `desktop` groups exist.
2. Add the entry-point options and runtime guard, then the presentation-aware page setup, then the
   welcome variant and session guard, each with its tests.
3. Update `README.md` and `AGENTS.md` sections 2.3 and 4.11.
4. Verify by hand: desktop launch unchanged, `--web` with networking disabled, and a second tab.

No vault, cache, or settings migration is involved. Rollback is a revert of the change; users can
keep launching without flags.

## Open Questions

- Whether a later change should retry automatically after a desktop launch failure is deliberately
  deferred; the explicit flag is the contract now, and changing it later would not alter these
  specs because the specs already forbid a silent switch.
- Whether a headless browser smoke test is worth its maintenance cost is deferred until the browser
  presentation has real users. The development group does include the web runtime, so a contributor
  can run the presentation from a clean checkout without installing anything extra.
