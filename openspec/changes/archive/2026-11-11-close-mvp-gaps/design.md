# Design

## Context

Current state that shapes the approach:

- There is no SQLite indexer. `Vault.scan()` parses the vault into an in-memory `VaultSnapshot`
  (notes, failures, name catalog), and every browser, project, and review query is derived from that
  snapshot. `VaultSession` holds the latest snapshot.
- `AppState.refresh()` already exists for the explicit refresh button: it scans, replaces the
  snapshot, re-reads an open page when the user is not editing, and re-reads the preview body.
- `PageEditorState` already owns one background task, the autosave loop, created at vault open and
  cancelled on reset. It is the established pattern for periodic work.
- Disk conflicts already have a state machine: `conflict` is `changed` or `missing`, with reload,
  overwrite, recreate, and discard actions and centralized copy.
- `_Shell` in `ui/app.py` owns the page lifecycle: it claims the session, configures the page, renders
  the workspace, and releases the session on disconnect.
- `flet build` ships with the installed `flet` package and is available as `hatch run flet build`. It
  targets `macos`, `linux`, and `windows`, and needs a Flutter SDK, which this machine does not have.
  There is no CI configuration in the repository.
- The project version is dynamic through Hatch (`src/afanes/__about__.py`).
- The OpenSpec apply step ignores a delta `## Purpose` on an existing spec, so a purpose rewrite
  cannot travel through a delta file.

See `proposal.md` for motivation.

## Goals / Non-Goals

**Goals:**

- Make a packaged desktop build the documented delivery path, with an offline first run.
- Make the workspace converge on the vault without a manual refresh, at bounded cost.
- Keep the open-page and conflict behavior identical to what already exists.
- Leave the documentation describing only what exists, plus clearly marked planned work.

**Non-Goals:**

- Code signing, notarization, auto-update, and a release pipeline. Artifacts are unsigned local
  builds.
- A SQLite index, FTS5 search, or the `afanes index` and `afanes doctor` commands.
- OS-level filesystem watching and any new runtime dependency.
- A user-facing refresh-interval setting.

## Decisions

### D1. Purpose paragraphs are edited in the main specs, not through a delta

**Decision.** Correct the three stale `## Purpose` paragraphs directly in
`openspec/specs/{processing,project-overview,reference-categories}/spec.md`, and record the edit in
`tasks.md`.

**Why.** The delta format cannot express a purpose change for an existing capability: the apply step
warns "delta Purpose ignored; already has one". A delta file with the corrected text would validate
and then be discarded at archive.

**Alternatives.** A `skip_specs: true` change that edits the prose (same result, but this change also
has requirement deltas, so the marker does not apply). Leaving the text stale (rejected: the specs
are the primary source for maintainers and agents).

### D2. Packaging uses `flet build` per target platform, with an explicit version

**Decision.** Document `hatch run flet build <platform> --build-version "$(hatch version)"` as the
packaging command for macOS, Linux, and Windows. Each artifact is built on its own platform; there
are no cross-built desktop artifacts. The Flutter SDK is a documented build prerequisite, not a
vendored tool. README gains a "Build a desktop app" section with the command, the prerequisite, the
output directory, and an offline launch check.

**Why.** This is the only path AGENTS 2.3 permits for a shipped desktop build, and it bundles the
client that would otherwise be downloaded on first run. Passing the version explicitly avoids two
sources of truth for a dynamic Hatch version. Building on the target platform avoids the
unsupported cross-compilation path and matches the parity requirement.

**Alternatives.** PyInstaller or Briefcase (they do not bundle the Flet client and leave the first-run
download in place); a CI matrix (no CI exists, and adding hosted infrastructure is out of scope);
shipping only a wheel with `flet[desktop]` (rejected: first run needs the network, which the spec
forbids for a distributed build).

### D3. Liveness is a coalesced poll, not a filesystem watcher

**Decision.** A single background task wakes every `REFRESH_SECONDS` (proposed default 5), computes a
cheap fingerprint of the scanned vault, and rescans only when the fingerprint changed. No
filesystem-watching dependency is added.

**Why.** A stat walk is far cheaper than parsing every note, works identically on all three
platforms, needs no native wheel, and cannot leak a thread or a subscription on close. A 5-second
bound is fast enough that a vault edited side by side converges before the user acts on stale data.

**Alternatives.** `watchfiles` (event-driven, but a new runtime dependency with native builds, a
watcher thread, and platform-specific event semantics); Flet timers (UI-thread coupling, no
cancellation story); refresh on window focus only (fails when both windows are visible, which is the
common case); refresh on every section switch (leaves an idle workspace stale indefinitely).

### D4. The shell owns the loop, the state owns the decision

**Decision.** `_Shell` creates and cancels one `asyncio.Task` for the lifetime of the claimed session,
and passes its interval through the loop. Each tick calls a new public `AppState.refresh_workspace()`
command inside the existing command lock, then repaints only when the call reports a change. The task
is cancelled on vault close, on session release, and when the workspace is replaced.

**Why.** The task is page lifecycle, like `page.on_disconnect`; the shell already owns that. Keeping
the decision in `AppState` means the refresh obeys the same lock as commands and no view gains
business logic. `AppState` gains no field, so the ten-field architecture gate is unaffected.

**Alternatives.** Put the loop in `PageEditorState` next to autosave (couples list freshness to the
page editor, which is not its concern); put it in a view (violates the view/controller split).

### D5. Freshness is decided by a stat fingerprint, not by content hashes

**Decision.** Add `Vault.scan_fingerprint()` returning a tuple of `(vault-relative path, mtime_ns,
size)` for the files the scan would parse, excluding `trash/` and hidden directories.
`VaultSession` stores the fingerprint taken with the last applied scan and exposes
`refresh_if_changed()`, which returns the new snapshot or `None`.

**Why.** A fingerprint is meaningful only if it comes from the same walk the scan uses, so the vault
service owns it and the exclusion rules stay in one place. `mtime_ns` plus size catches edits and
appends; the content hash of the open page remains the authority for the write guard, so a
coarse-grained filesystem cannot cause a false "unchanged" on the page being edited.

**Alternatives.** Compare `VaultSnapshot.content_hashes` (requires reading every file, which is the
cost we are avoiding); watch mtimes only in the UI layer (duplicates the exclusion rules).

### D6. An open page follows the change through the existing conflict machinery

**Decision.** On a changed scan, compare the open page with the new snapshot:

```
open page          draft clean?      draft dirty?
-----------------  ----------------  ----------------------------
still parses      reload content     set conflict = "changed"
missing            conflict="missing"  set conflict = "missing"
```

Reloading a clean page reuses `PageDraftFactory.from_page` and keeps read or raw mode. A dirty draft
is never replaced; the existing banner and its four actions do the resolution. When the draft is
dirty and a conflict is already set, the state is left alone.

**Why.** The conflict state machine is already specified, tested, and worded. Reusing it keeps one
way to explain "your file and your draft disagree" and avoids a second, weaker banner.

**Alternatives.** Always reload and drop the draft (data loss); always raise a conflict (noisy for a
read-only page); reload in edit mode and merge (a merge algorithm is out of scope and would need its
own spec).

### D7. Background refresh preserves what the user can see

**Decision.** `AppState.refresh_workspace()` differs from the manual `refresh()` in four ways: it
skips the tick when the command lock is busy, it does not set the busy indicator, it does not clear a
`status.message` raised by a command, and it never closes a dialog or a processing/review flow. The
snapshot replacement path takes a keyword flag so a background apply preserves the message while a
command-driven apply still clears it. If the scan fails, the previous snapshot stays and no message
is raised (a background failure must not interrupt).

**Why.** A refresh the user did not ask for must be invisible unless it changes something they can
see. Clearing a banner or flashing a spinner would make the application feel unstable.

**Alternatives.** Reuse `refresh()` unchanged (flashes busy, clears messages, and would reload a page
mid-edit only when editing is false, so it misses the dirty-draft conflict); always suppress
messages for every apply (hides deliberate feedback after commands).

### D8. Documentation states which planned components do not exist

**Decision.** Update `AGENTS.md` 3.1 and 3.2 to the real module tree (`views/page.py`,
`views/projects.py`, `views/review.py`, `models/step.py`, `core/steps.py`, `core/editing.py`,
`core/templates.py`, `cli/strings.py`, `cli/vault.py`), and annotate the SQLite indexer, `cli/index.py`,
and `cli/doctor.py` as planned. Section 4.10 keeps its rules but is introduced as applying when the
cache exists. No behavior, rule, or gate is weakened.

**Why.** The current text describes files and guarantees that do not exist, which misleads every
reader who follows the documented read order.

**Alternatives.** Build the index first (a separate change with its own performance argument); delete
the indexer sections (removes a documented direction the maintainer may still intend).

## Architecture

```
 vault on disk
      |
      |  scan_fingerprint()  (stat walk, no parse)
      v
 +---------------------+   changed?   +----------------------------+
 | VaultSession        | -----------> | Vault.scan()  (parse)      |
 |  snapshot           |              +----------------------------+
 |  fingerprint        |                          |
 +---------------------+                          v
      ^                                   replace snapshot
      |                                          |
      |  AppState.refresh_workspace()            v
      |  (inside command lock)           browser / projects / review
      |                                          |
      |                                          v
      |                              open page? compare with snapshot
      |                                 clean -> reload
      |                                 dirty -> conflict = "changed"
      |                                 gone  -> conflict = "missing"
      |
 +---------------------------+
 | _Shell refresh task       |  every REFRESH_SECONDS, cancelled on
 | (one per claimed session) |  close, disconnect, or workspace swap
 +---------------------------+
```

Packaging is a separate flow with no runtime component:

```
 maintainer machine                         artifact
 ------------------                         --------
 hatch run flet build <os>                  build/<os>/...
   --build-version "$(hatch version)"  -->    bundles flet client
   requires Flutter SDK                        starts offline
   uses the network at build time only         reports project version
```

## Failure modes and recovery

| Failure | Behavior | Recovery |
| --- | --- | --- |
| Fingerprint walk fails (permissions, vanished root) | Tick is skipped; no message | Next tick retries; the explicit refresh still reports a failure |
| Scan fails mid-tick | Previous snapshot stays; no user-visible message | Next tick retries; explicit refresh reports it |
| Open page vanished during a dirty edit | `conflict = "missing"` with the existing recreate/discard actions | User recreates or discards |
| Open page rewritten by another editor | Clean draft reloads; dirty draft raises `changed` | Reload, overwrite, or discard |
| Vault closed or session released | Task is cancelled before the next tick | New session starts a new task |
| Build without Flutter SDK | `flet build` stops and names the missing toolchain | Install the SDK; no artifact is produced |
| Artifact launched with no network | Client is bundled, so startup succeeds | none needed |

## Cross-platform notes

- `mtime_ns` granularity differs by filesystem; it is used only to decide whether to rescan, and the
  content hash remains the write guard, so a false negative delays a refresh by one interval instead
  of causing a wrong write.
- The fingerprint uses vault-relative paths, so case-insensitive and case-sensitive filesystems
  behave the same as the existing scan.
- Desktop artifacts are produced only on their target platform. The offline launch check must run on
  macOS, Linux, and Windows before the change is reported done.
- No path, filename, or reserved-name rule changes.

## Migration plan

No user data or format migration. No cache schema to invalidate, because the SQLite cache is not
implemented. Rolling back means reverting the change; vault files are untouched by packaging and
background refresh is read-only.

## Test strategy

- `Vault.scan_fingerprint()`: stable for an unchanged vault, differs after an edit, an addition, a
  removal, and a move into `trash/`; ignores `trash/` and hidden directories. Uses `tmp_path` only.
- `VaultSession.refresh_if_changed()`: returns `None` when only mtimes are touched without content
  change (fingerprint changes, scan still applies), and returns a new snapshot after a real edit.
- `AppState.refresh_workspace()`: no-op without a vault; preserves `status.message`; keeps a dirty
  draft and sets `conflict`; reloads a clean page; reports a missing file; does not touch a pending
  processing plan; does not write any file.
- Integration: create a vault, capture, then write an external edit directly with `Path.write_text`,
  call `refresh_workspace()`, and assert the browser and project rows reflect it.
- Determinism: tests call the command directly; the loop is never exercised through real time. Any
  interval test patches the constant and the sleep.
- Packaging is verified manually with a documented checklist per platform, because no CI or Flutter
  SDK exists in the test environments.

## Privacy, offline behavior, and vocabulary

- Build-time dependency resolution is the only network activity; the artifact makes no request at
  startup. Background refresh reads only local files.
- No telemetry, accounts, or remote assets are added.
- New copy stays in `ui/strings.py` and uses neutral vocabulary; the existing conflict strings are
  reused rather than reworded.

## Open questions

- The 5-second default may need tuning after measuring scan cost on a large vault. It is a constant,
  not a setting, so changing it later is not a spec change.
- Signing and notarization remain open for the first public artifact.
- Whether the planned SQLite index should be built before or after the first packaged release is a
  maintainer decision that this change does not force.
