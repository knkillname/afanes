# Design

## Context

See `proposal.md` for motivation. The local Ubuntu 26.10 machine has no
`clang`, CMake, Ninja, `pkg-config`, or GTK 3 development headers. Flutter
3.47.9 is already present at `~/flutter/3.47.9`, which is the version Flet
1.1.2 expects, and the Flet desktop client baseline is
`flet-desktop-light-ubuntu24.04-1.1.2`. The repository is public, `gh` is
authenticated, and there is no `.github/` directory or workflow history.

`hatch run package linux` compiles the gettext catalogs and then runs
`flet build linux`; the artifact is copied to `build/linux`, and Flet needs
`--yes` to install its SDK when none is present. The project has no runtime
network behavior; the build already uses network access to resolve dependencies.

## Goals / Non-Goals

**Goals:**

- Build the Linux bundle on a pinned GitHub Actions runner with the documented
  native toolchain.
- Run the automated gates on the runner before the build, so the artifact comes
  from a green commit.
- Produce a downloadable, checksummed artifact whose commit, runner image, tool
  versions, and build version are recorded.
- Make the release documentation describe the Linux workflow and the wheel, and
  stop promising a macOS/Windows nightly that does not exist.
- Keep the packaged manual gate, release attachment, and version decisions
  local and manual.

**Non-Goals:**

- macOS or Windows nightly workflows or native builds.
- Automatic tagging, publishing, or release attachment.
- Running the packaged manual gate in CI.
- Building the wheel in CI.
- Installing the local toolchain, adding a container build, or changing runtime
  code, tests, dependencies, or specs.
- Caching as a correctness requirement.

## Decisions

### D1. One manual Linux workflow, no PR trigger

Use `.github/workflows/linux-release.yml` with `workflow_dispatch` as the
primary trigger. Add a `push` trigger limited to `release/**` only as a fallback
for a branch that cannot be dispatched. Do not trigger on pull requests; the
workflow builds and uploads an artifact, and untrusted pull-request code must
not run in that context.

Use a single job and a `concurrency` group with `cancel-in-progress: false` so
two release builds cannot race. Set a 60-minute timeout.

Alternatives: building on every push (noisy and unnecessary), pull-request
builds (untrusted artifact), or a release tag trigger (the project does not tag
until a release is confirmed).

### D2. Pin `ubuntu-24.04`

Use `runs-on: ubuntu-24.04`. It matches the Flet desktop client baseline, its
glibc is older than the maintainer's Ubuntu 26.10, and its clang, CMake, and
Ninja versions meet Flutter's Linux desktop minimums. Record the runner image
version from the `ImageOS` and `ImageVersion` variables in the run summary.

Alternatives: `ubuntu-22.04` (Flet's client is built for 24.04), `ubuntu-latest`
(the image can drift), or a custom container (more moving parts for no current
benefit).

### D3. Install the minimal documented toolchain

Install `clang`, `cmake`, `ninja-build`, `pkg-config`, and `libgtk-3-dev` with
apt. These cover Flutter's Linux doctor requirements and the GTK, GLib, and GIO
development libraries. Flet's canonical Linux list also names GStreamer, mpv,
libsecret, lld, llvm, and libunwind packages; Afanes does not use media playback
or secure storage, so add them only if the link step asks for one.

Alternatives: install Flet's full list (heavier and mostly unused) or use a
prebuilt image (another artifact to maintain).

### D4. Let Flet install Flutter, and run the gates first

Run `hatch check` and `hatch test --cover` before the build. Use Python 3.13 for
the Hatch environment and install `hatch` and `uv` with pip, because the project
configures the uv installer. The tests run headless today; if a UI test turns
out to need a display, wrap the test step in `xvfb-run` rather than skipping it.

Let `flet build linux --yes` install the pinned Flutter 3.47.9 on the fresh
runner. Do not add a third-party Flutter action or a second Flutter version.
Run the build with `--build-version "$(hatch version)"` so the artifact metadata
and the About dialog read the same source version.

Cache `~/flutter/3.47.9`, `~/.flet/client`, and `~/.flet/cache` only if the
first runs show the download dominates the job. Correctness comes first; a
manual workflow can afford a slower first run.

Alternatives: `subosito/flutter-action` (third-party action and a duplicated
version pin), or a manually downloaded SDK (more YAML for no benefit).

### D5. Package the bundle as a checksummed tar.gz

Run `tar -czf "afanes-linux-x64-$(hatch version).tar.gz" -C build/linux .` and
print `sha256sum`. Upload that file with `actions/upload-artifact` and
`if-no-files-found: error`. A tar.gz preserves executable bits and symlinks
across the download; a raw directory upload does not guarantee them. Include the
whole bundle root, including `share/`, `data/`, and `lib/`.

Write the commit SHA, `hatch version`, `uname -a`, `/etc/os-release`,
`ImageOS`, `ImageVersion`, the tool versions, and the checksum to
`$GITHUB_STEP_SUMMARY`. These fields are the traceability record for the later
`RELEASE.md` evidence.

Alternatives: upload the directory (permission risk) or skip the checksum
(weaker download verification).

### D6. Keep the artifact and the manual gate separate

The workflow artifact is short-lived and public; it is not a release asset.
The maintainer downloads it with `gh run download`, verifies the checksum,
extracts it, and runs the packaged manual gate on the Linux desktop. Release
attachment stays manual and occurs in the packaging change, not here.

The dry run at `0.14.0` proves the workflow and the bundle. It is not `1.0.0`
evidence; the packaging change bumps the version, dispatches the same workflow,
and records the run URL, commit, runner image, and checksum in `RELEASE.md`
after the manual checks.

### D7. Make the release documents match the real surface

Remove the macOS and Windows nightly promise from `RELEASE.md`,
`docs/develop/releasing.md`, `docs/getting-started/install.md`, and `README.md`.
Clarify in `docs/develop/setup.md` that the Flutter SDK and native build tools
are only needed for a local packaged build. The current release surface is the
Linux native build and the wheel; native macOS and Windows binaries are not
produced. A later change can add the nightly workflow and restore that policy.

Update `AGENTS.md` so the operating manual says the Linux release workflow
builds the artifact while the local gates and the packaged manual gate remain
required. Add the dispatch and download commands to the environment section.
Update the `RELEASE.md` work sequence so the workflow lands before packaging and
Linux evidence.

### D8. No version bump in this change

This is build tooling and documentation, not a completed MVP milestone. Keep the
changelog entry under `Unreleased` and leave the version at `0.14.0`. The
post-archive release step records the docs status and does not bump.

## Risks / Trade-offs

- **The release build depends on GitHub Actions.** Pin the runner, record its
  image version and the commit, keep the local build path documented, and keep
  release attachment manual. The runtime remains offline.
- **The runner toolchain drifts with the image.** Pin `ubuntu-24.04`, record the
  image version, and add a package only when the link step names it.
- **The first run may expose host-dependent tests.** Treat a failure as a test
  defect to fix, not as a reason to skip the step; use `xvfb-run` if a UI test
  needs a display.
- **The Flutter SDK download makes the first run slow.** Accept it for a manual
  workflow; add caching keyed on the Flet and Flutter versions if needed.
- **The artifact is built on 24.04 and runs on 26.10.** Verify the smoke launch
  on the host; if the bundle fails on the newer glibc, fall back to a newer
  runner image or the local toolchain and record the reason.
- **The workflow file must reach GitHub.** The local `main` is ahead of
  `origin/main`; the implementation needs maintainer approval to push `main` or
  a `release/**` branch. Nothing is pushed or published by this planning change.
- **Removing the nightly promise narrows the documented release surface.**
  Record it as a deliberate deferral; the Linux build and the wheel still meet
  the `1.0.0` policy.
- **Public workflow artifacts.** They contain the application, not a vault, and
  no secrets. Keep the workflow token read-only, pin actions by commit SHA, and
  avoid `pull_request_target`.

## Migration Plan

No runtime migration. The implementation adds the workflow, updates the policy
and release documents, pushes the chosen branch, and dispatches a `0.14.0` dry
run. The dry run is complete when the workflow succeeds, the checksum matches,
and the extracted bundle opens a vault and captures a note on the Linux desktop.
Rollback is deleting the workflow and reverting the documentation; the
application and the vault format are untouched.
