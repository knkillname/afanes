# Proposal

## Why

Afanes presents its interface through the Flet desktop client, a native Flutter binary that Flet
downloads into the user's cache on first run. Some managed environments block that binary, block the
download that provisions it, or forbid installing a native executable from a package manager. On
those machines Afanes cannot start at all, even though the same interface can be served to a browser
by the Flet web runtime, whose wheel bundles every client asset and requires no native executable.

That path is also the only one that runs fully offline from a source install, and today it is broken
in fact while being unreachable on purpose. The entry point always requests the desktop view, and
when Flet itself falls back to the web server on a headless Linux host, the welcome screen's folder
picker raises `FletUnsupportedPlatformException`, so the first action a new user takes fails.

## What Changes

- Add `--web`, `--vault DIR`, and `--port N` to the graphical entry point. Desktop remains the
  default; web presentation is requested explicitly and never entered silently.
- Give the browser presentation a selection path that does not need a native folder dialog: an
  absolute-path field on the welcome state, plus `--vault` for launchers. A vault supplied on the
  command line applies to that run only and does not replace the remembered vault.
- Skip desktop-only window calls when the interface runs in a browser, so the same view code serves
  both presentations.
- Serve every client asset locally and bind the web server to the loopback interface only.
- Fail fast with an actionable message when the required Flet runtime package is absent, instead of
  letting Flet's automatic runtime installer reach the network or exit with a bare status.
- Permit one active workspace session per process in web presentation; a second browser session is
  told that another session is active and cannot drive the workspace.
- Update the dependency policy in `AGENTS.md` sections 2.3 and 4.11 and the `README.md` run
  instructions to cover the browser presentation.

**No breaking change** for existing desktop users: with no flags, behavior is unchanged.

## Capabilities

### New Capabilities

- `app-runtime`: how Afanes starts, which presentation it serves, and the offline, binding, and
  session guarantees each presentation must hold.

### Modified Capabilities

- `vault-selection`: vault selection must work when no native directory dialog exists, and a vault
  may be supplied for a single run.

## Impact

- `src/afanes/__main__.py`: argument parsing, presentation selection, runtime availability guard.
- `src/afanes/ui/app.py`: presentation-aware page setup and the web vault entry point.
- `src/afanes/ui/state.py`: single-run vault selection and the active-session guard.
- `src/afanes/ui/views/inbox.py`: welcome state variant for a browser session.
- `src/afanes/ui/strings.py`: new neutral copy for the path entry, session notice, and launch errors.
- Tests: `tests/ui/test_app.py`, `tests/ui/test_state.py`, `tests/ui/test_inbox_view.py`, plus a new
  entry-point test module.
- `pyproject.toml`: consumes the `desktop` and `web` optional dependency groups introduced by the
  `relax-dependency-pins` change; the `web` group supplies `flet-web`.
- `README.md` and `AGENTS.md` sections 2.3 and 4.11.
- No change to the vault format, the cache, `core/`, or `models/`.
- macOS, Linux, and Windows run the same browser code path; the server is the process host and the
  browser may be any of them.

## Success Criteria

- `python -m afanes --web` opens a working workspace in a browser on a machine with no desktop
  client installed and no network access after installation.
- `python -m afanes` behaves exactly as it does today when the desktop client is available.
- The welcome state never raises on a browser session, and a vault can be opened there without a
  native dialog.
- A second browser session cannot mutate workspace state while the first is active.
- `core/` and `models/` remain free of Flet imports.

## Risks

- The web server and the browser are separate processes sharing one filesystem view; a remote bind
  would expose the vault. Mitigation: loopback-only binding with no option to change it.
- Two browser sessions can interleave edits in the shared controller. Mitigation: one active
  session, released when the tab disconnects.
- The `web` extra adds `fastapi`, `uvicorn`, and `websockets` to a web-only install. This is the
  price of serving the interface without a native client, and it is opt-in.
- Flet's web runtime could change asset layout in a later 1.x release. Mitigation: the ceiling test
  environment from `relax-dependency-pins` plus a startup smoke check for the runtime package.

## Out of Scope

- Authentication, user accounts, TLS, or serving Afanes to other people. The product stays
  single-user and local.
- Deploying behind a reverse proxy with `flet.run(export_asgi_app=True)`.
- Uploading a vault from the browser or editing a server-side copy of the user's notes.
- A server-side directory browser. A path field plus `--vault` covers the browser case.
- Bundling the desktop client with `flet build`, which remains future work.
