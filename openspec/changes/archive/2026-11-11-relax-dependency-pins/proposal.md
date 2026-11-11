# Proposal

## Why

Afanes pins its three runtime dependencies to exact releases: `flet==1.1.2`,
`markdown-it-py==4.3.0`, and `PyYAML==6.0.3`. At the time of writing those pins were published
five days, one day, and fourteen months earlier respectively. A corporate artifact mirror synced
weekly cannot carry a package released yesterday, so the install fails at resolution before any
code runs. An exact pin also blocks the patched releases a security review expects to be able to
adopt, which is the second reason corporate environments reject the current dependency set.

The result is that Afanes cannot be installed in many companies even though every pinned package
is itself permitted. The pins are the obstacle, not the packages.

## What Changes

- Replace the exact runtime pins with compatible-release ranges whose lower bound is a release that
  mirrors already carry and that the application's API usage actually supports.
- Add `desktop` and `web` optional dependency groups. The Flet desktop client and the Flet web
  runtime are installed only by the person who chooses them, so a web-only install contains no
  desktop binary at all.
- Keep the Flet SDK in the base dependencies under a range, and obtain the client and web runtime
  through Flet's own `desktop` and `web` extras. Flet pins those packages to the resolved SDK
  version, so version lockstep is preserved without Afanes hardcoding a patch version.
- Add a Hatch test matrix entry pinned to the floor versions of every ranged dependency, so the
  lower bound is tested rather than asserted.
- Rewrite the dependency policy in `AGENTS.md` sections 2.2, 2.3, and 2.7: ranges plus tested
  floors replace exact pins, and release artifacts must record the versions they were built with.
- Update `README.md` to describe the three install shapes and when to use each.

Development tool pins stay exact. They never reach a runtime install, and loosening them would
trade gate reproducibility for a problem nobody has reported.

## Capabilities

### New Capabilities

None. This change alters dependency declarations, tooling configuration, and documentation. It
introduces no user-observable behavior, so it declares `skip_specs: true` rather than inventing a
requirement.

### Modified Capabilities

None. No existing capability's behavior changes: the same features work, installed from different
package versions.

## Impact

- `pyproject.toml`: `dependencies`, a new `optional-dependencies` table, the `dev` group, and the
  Hatch test matrix.
- `AGENTS.md` sections 2.2, 2.3, and 2.7.
- `README.md` install and development instructions.
- No source code, test code, or user-facing string changes.
- macOS, Linux, and Windows are unaffected; optional dependency groups resolve identically on all
  three, and no platform-specific package is introduced.
- Offline behavior is unchanged and slightly improved: choosing the `web` group removes the
  desktop client download from that install entirely.

## Success Criteria

- `pip install afanes` succeeds on a mirror that carries only releases available one month before
  this change.
- `pip install afanes[desktop]` and `pip install afanes[web]` each install a matched Flet SDK and
  runtime, with no runtime package installation attempted on first launch.
- The full test suite passes against the floor versions and against the currently resolved
  versions.
- No lock file, constraints file, or vendored wheel is added to the repository.

## Risks

- The Flet 1.x line began on 2026-09-28, so even the floor is weeks old. A quarterly-synced mirror
  may still be unable to satisfy `flet>=1.0.4,<2`. That is a mirror refresh problem, not a range
  problem; anything below 1.0 is a different API and would require rewriting the UI.
- Ranges remove the implicit reproducibility guarantee. Mitigation: the release workflow records
  the resolved versions, and the floor test keeps the supported window honest.
- A future Flet 1.x release could change behavior within the `<2` bound. Mitigation: the floor and
  ceiling test matrix, plus the existing UI tests.

## Out of Scope

- Changing `requires-python` or the supported Python versions.
- Packaging or bundling the desktop client with `flet build`.
- The web presentation mode itself, which is proposed separately as the `web-runtime` change.
- Loosening pins for development and test tools.
