# Tasks

## 1. Entry point and launch options

- [x] 1.1 Add `argparse` options `--web`, `--vault DIR`, and `--port N` to `src/afanes/__main__.py`,
      parsed by a pure `parse_launch_options` function returning a frozen `LaunchOptions` value.
      Verify with unit tests covering the default, `--web`, `--port`, `--vault`, and an unknown
      option (usage error, exit code 2).
- [x] 1.2 Guard the Flet and `afanes.ui.app` imports so a missing SDK prints one actionable message
      instead of a traceback. Verify with a test that removes the module from `sys.modules` and
      patches the import machinery to raise `ModuleNotFoundError`, then asserts the message and a
      status of 1.
- [x] 1.3 Check the selected runtime package with `importlib.util.find_spec` before starting and
      exit 1 with a message naming the install command when it is absent. Verify with tests for the
      desktop and web branches that assert `ft.run` is never called.
- [x] 1.4 Dispatch to `ft.run` with the presentation-specific keyword arguments: desktop keeps the
      current call, web passes the browser view, `host="127.0.0.1"`, `no_cdn=True`, and the parsed
      port. Verify with a test that replaces `ft.run` with a recorder and asserts the exact keyword
      arguments for both presentations.
- [x] 1.5 Catch a desktop client launch failure and report it with `--web` named as the alternative,
      then exit 1 without starting a web server. Verify with a test that raises from the recorded
      `ft.run` and asserts the message, the status, and that no second launch occurred.

## 2. Presentation-aware interface shell

- [x] 2.1 Compute `is_desktop = not page.web` once in `src/afanes/ui/app.py` and skip the
      `page.window` assignments when false. Verify by extending the fake page in
      `tests/ui/test_app.py` with a `web` flag and asserting the window attributes stay untouched in
      the web case and are set in the desktop case.
- [x] 2.2 Change `build_welcome` to accept an optional native `on_choose` callback and an optional
      `on_open_path` callback, rendering the folder button for the first and a path field with an
      `Open` button for the second. Verify in `tests/ui/test_inbox_view.py` that each variant renders
      exactly one primary action and no controls belonging to the other variant.

## 3. Vault selection in a browser session

- [x] 3.1 Add a controller command that opens a vault from entered text, resolving and validating it
      through the existing vault-opening path and surfacing a message on failure. Verify in
      `tests/ui/test_state.py` that a valid path opens the vault and writes settings, and that a
      missing path, a file, and an unreadable directory each leave the vault unopened with a message.
- [x] 3.2 Wire the web welcome field to that command so a browser session can reach the Inbox.
      Verify in `tests/ui/test_app.py` that entering a valid path renders the workspace and that an
      invalid path leaves the welcome state with a banner and no settings file.
- [x] 3.3 Support `--vault` at launch: resolve and validate before the interface starts, use it for
      that run only, never write it to settings, and exit 1 with a standard-error message when it is
      invalid. Verify with tests for precedence (supplied beats remembered), for an unchanged
      settings file, and for each invalid-path case.
- [x] 3.4 Make the shell's change-vault command presentation-aware: keep the native picker on
      desktop, and in a browser session show a dialog with a path field plus Open and Cancel, backed
      by the same controller command. Verify in `tests/ui/test_app.py` that a browser session shows
      the dialog instead of calling the picker, that opening a valid path switches the vault and
      saves it, and that Cancel leaves the current vault and settings unchanged.

## 4. Single active session

- [x] 4.1 Add an active-session marker to `AppState` with a command to begin a session and one to
      release it. Verify in `tests/ui/test_state.py` that the second begin attempt is refused, that
      release allows a later session, and that a refused session never scans or writes the vault.
- [x] 4.2 Render the second-session notice instead of the workspace and release the marker from
      `page.on_disconnect`. Verify in `tests/ui/test_app.py` that a second session shows the notice
      without opening the workspace and that the disconnect handler releases the marker.

## 5. Documentation

- [x] 5.1 Add a `README.md` section describing the browser presentation, its install shape
      (`afanes[web]`), the `--web`, `--vault`, and `--port` options, loopback-only serving, the
      single-session rule, and that the desktop presentation remains the default. Verify every
      command shown matches the implemented options.
- [x] 5.2 Update `AGENTS.md` section 2.3 and 4.11 to state that the browser presentation is an
      explicit mode, binds loopback only, serves local assets, allows one active session, and that
      code must never install a runtime package at startup. Verify no section still implies the
      desktop client is the only presentation.
- [x] 5.3 Add an `Unreleased` entry to `CHANGELOG.md` describing the browser presentation and the
      new options. Verify the entry exists under the correct Keep a Changelog category.

## 6. Integration checks

- [x] 6.1 Run `hatch check`, `hatch test --cover`, and `openspec validate --all --strict`. Verify all
      three pass.
- [x] 6.2 Verify by hand on Linux that a normal launch still opens the desktop window, that
      `python -m afanes --web` serves the interface in a browser with networking disabled after
      installation, that `--port` is honored and the address is reported, and that a request from
      another host is refused. Record the results in the change notes.
- [x] 6.3 Run the prohibited-vocabulary checks from `AGENTS.md` section 6.6. Verify both commands
      produce no matches.

## Verification

Manual checks on Linux (2026-11-11) with an isolated `XDG_CONFIG_HOME` and a temporary vault, so no
user settings or notes were touched:

- Desktop launch (`python -m afanes --vault <temporary>`): the process stayed alive for the whole
  observation window, the cached Flet client started, and the session reported no exceptions.
- Browser launch (`python -m afanes --web --port 8766 --vault <temporary>`): the server logged
  `App URL: http://127.0.0.1:8766` and `No CDN configured: True`, and the page returned status 200.
- Loopback binding: the listener was bound to `127.0.0.1:8766` only, and a request to the machine's
  LAN address was refused.
- Local assets: the browser loaded `main.dart.js`, `canvaskit.wasm`, and every font from the local
  server; the served page contained no external URLs and set `flet.noCdn=true`.
- The browser session rendered without an exception, which is the path that previously raised on the
  folder picker.
- The welcome screen was captured in a real headless browser: it renders the title, the "Vault folder
  path" field, and the Open action. The workspace was captured in the same way with a vault open.
- A tab whose server process has exited shows Flet's own spinner with "Working…" indefinitely. That
  is the client waiting for a page session, not an Afanes hang, and the shell cannot render inside
  it. The README now explains how to recognize and recover from that state.
- The temporary `flet[web]` development-group entry used to run the server was reverted, and the
  full gate was rerun afterwards.
- Running the presentation from a checkout exposed that the development group installed only the
  desktop runtime. The dev group now installs `flet[web]` too, so a clean checkout can run
  `hatch run python -m afanes --web` without extra steps.

## Workflow follow-up

- Archive the change only after review and a passing gate, after `relax-dependency-pins` has landed
  or is archived, since the `web` install shape depends on the optional dependency groups.
- Include the browser verification results from task 6.2 in the archive summary.
