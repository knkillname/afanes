# AGENTS.md

**Audience:** AI coding agents (OpenCode/DeepSeek and equivalents), maintainers, reviewers.

**Status:** Operating manual. Change this file only through an OpenSpec change or explicit maintainer direction.

**Read order:** `AGENTS.md` -> `README.md` -> `docs/develop/documentation.md` -> `CHANGELOG.md` -> `pyproject.toml` -> `openspec/specs/` -> active change in `openspec/changes/` -> code and tests.

**Precedence:** explicit user instruction > OpenSpec behavior specs > this file > local code patterns. If sources conflict, stop and ask.

**Tie-breaker:** Zen of Python (PEP 20). Prefer explicit, flat, readable, obvious designs.

**Design principles:** SOLID, DRY, KISS, and YAGNI, read through the Zen of Python (PEP 20). The Zen is necessary but not sufficient. Structure is object-oriented with immutable value objects and small public methods that return values; no free functions. Use functional style inside methods — explicit inputs, returned outputs, no hidden mutation. Prefer the simplest design that satisfies the spec and keep one source of truth for each behavior.

> This file contains prohibited vocabulary only in sections 4.1 and 6.1, as an enforcement target. Never copy those strings into code, UI, tests, specs, commits, or user docs.

## 1. Project snapshot

- Offline, local-first Markdown vault: a personal wiki plus project engine. The `.md` files are authoritative; there is no account, telemetry, cloud, or hidden network call in application code.
- Flow: capture -> clarify -> browse -> review. Three note types: `note` (Inbox capture), `reference` (optional free-form `category`), `project` (body holds Markdown task-list steps). Filename stem is identity; the first H1 is the display title.
- Vaults are versioned. A vault root contains `afanes.yaml` with `schema_version: 1`; a folder without a valid file is refused. An older writable folder with the five default folders can be adopted explicitly, which writes only that file. Opening a versioned vault is read-only.
- Default layout: `inbox/`, `trash/`, `reference/<category>/`, `projects/`. Folders are conventions, not requirements. `trash/` is excluded from scans and reference resolution.
- Current state: there is no SQLite index. Each vault is scanned into an in-memory `VaultSnapshot`; `core/search.py` derives browser, project, and review views from it. Do not add `indexer`, `afanes index`, or `afanes doctor` without an approved change.
- Behavior details belong to `openspec/specs/*/spec.md` (normative) and `docs/` (user-facing narrative); `README.md` is the landing page. Do not duplicate or re-derive them here.
- UI: Flet 1.x. The desktop window is the default; `--web` is explicit, loopback-only, and single-session. The first development desktop run may fetch the Flet client once as provisioning; packaged builds bundle it.

## 2. Environment and commands

Hatch is the only developer interface. Do not run `uv`, `pip`, `poetry`, or `conda`, and do not create or edit `.venv/` by hand; `hatch env create` owns it. There is no CI, so run the gates locally.

```bash
hatch env create
hatch run afanes                    # desktop
hatch run afanes --web              # loopback browser
hatch check                         # Ruff lint + format check + Pyrefly strict
hatch check --fix                   # lint/format fixes only; types need manual fixes
hatch run docs:build                # Sphinx documentation; warnings are errors
hatch run docs:serve                # local documentation preview
hatch test --cover                  # coverage; fail_under = 85
hatch test tests/core/vault/test_service.py::TestVaultOpen::test_opens_an_existing_directory
hatch test -k "frontmatter and not slow"
hatch test --all                    # 3.13 + 3.14 + oldest-dependency floor
hatch run pytest ...                # focused diagnosis only
hatch run python scripts/scan_benchmark.py --notes 1000 5000 10000 --repeat 5
```

- Interpreter: `.venv/bin/python` (Windows: `.venv\Scripts\python.exe`).
- Version: `hatch version`. Bump only through 5.3; never edit `src/afanes/__about__.py`.
- Build: `hatch run flet build <linux|macos|windows> --build-version "$(hatch version)"`. Build only on the host OS; artifacts land in `build/<platform>/`. `src/main.py` is the packaged launcher.
- Documentation: `docs/` is the user-facing manual; build it with `hatch run docs:build` and preview it with `hatch run docs:serve`. The `docs` Hatch environment installs Sphinx only for documentation work.
- OpenSpec: `openspec list --json`, `openspec status --change "<name>" --json`, `openspec instructions apply --change "<name>" --json`, `openspec validate --all --strict`, `openspec doctor`, `openspec archive "<name>"`. Slash commands: `/opsx-propose`, `/opsx-apply`, `/opsx-archive`, and siblings.
- `rg` is not installed here. Use `grep -r` (see 6.1).

### 2.1 Dependencies

- Runtime dependencies use compatible ranges in `pyproject.toml` (lower bound tested by the floor matrix, upper bound below the next major). There is no lock or constraints file.
- A new dependency requires an OpenSpec change covering the need, alternatives, license, offline behavior, and cross-platform impact. Never add cloud, telemetry, or auto-update packages.
- Flet components come through `flet[desktop]` / `flet[web]` extras; never re-pin a component to a patch version.
- Ruff, Pyrefly, pytest, and coverage are the only code-quality tools. Do not add a second linter, formatter, type checker, test runner, or coverage tool. `hatch fmt` is deprecated; use `hatch check`.
- Sphinx builds the documentation; it is not a second linter, formatter, test runner, or coverage tool. Documentation dependencies live in the `docs` dependency group.

## 3. Architecture

### 3.1 Layout and entrypoints

- `src/main.py` — packaged desktop launcher for `flet build`; delegates to `afanes.__main__.Launcher.launch_packaged`.
- `src/afanes/__main__.py` — GUI/web launcher. Dispatches `vault` subcommands before importing Flet, verifies the selected runtime package, and binds web to `127.0.0.1`.
- `src/afanes/cli/main.py` — argparse headless commands. Never import `flet` or `afanes.ui`. Exit codes are `0` success, `1` expected failure, `2` usage error; reports go to stdout and failures to stderr.
- `src/afanes/ui/app.py` — `main(page, launch_vault=None)` Flet entry.
- `src/afanes/ui/state/` — the state package. `AppState` lives in `controller.py`; views use the singleton `afanes.ui.state.app_state` and tests call `app_state.reset()`.
- `core/templates.py` loads bundled Markdown trees from `src/afanes/templates/<template>/<locale>/`; `_guide` is the always-seeded guide and `{{date:±Nd}}` placeholders resolve at creation time.
- Dependency DAG: `models <- core <- ui` and `core <- cli`. `ui` and `cli` never import each other. `models` imports only the standard library. `core` never imports Flet, `ui`, or `cli`. The graph must stay acyclic at submodule level.
- `core/` owns parsing, names, links, steps, templates, vault I/O, processing, search, settings. `ui/` is presentational: no Markdown parsing, SQL, or direct vault I/O. `ui/state/` must not import views/components; `theme.py` and `strings.py` are import leaves. `cli/` is a thin adapter over `core`.
- `core/search.py` services (`Browser`, `ProjectBoard`, `ReviewPlanner`) are read-only over a scanned snapshot; they never read files.

### 3.2 Import rules

- Import modules for functions/constants: `import afanes.core.frontmatter` then `afanes.core.frontmatter.parse_note(...)`. Never `from afanes.core.frontmatter import parse_note`, and never `from afanes.core import frontmatter`.
- Import CamelCase types/classes directly: `from afanes.models.note import NoteType`.
- Allowed stdlib patterns include `from pathlib import Path`, `from collections.abc import Sequence`, and `from typing import Self`. Access other `typing` members through `import typing`.
- No relative imports, wildcard imports, `from __future__ import annotations`, or `typing.TYPE_CHECKING`. Quote an unavoidable forward reference.
- Keep `__init__.py` thin; do not re-export implementation symbols.
- No dependency-injection containers, service locators, or injected clocks/collaborators. Pass plain values; dependency inversion is expressed through explicit parameters, and tests patch module behavior.

## 4. Code standards

### 4.1 Vocabulary

Afanes is independent of proprietary productivity methodologies. These strings are prohibited product vocabulary:

- `GTD`
- `Getting Things Done`
- abbreviations, plurals, translations, hyphenated forms, stylized forms, or close variants of the above
- `Inbox Zero` and similar proprietary slogans

They must never appear in source, identifiers, comments, docstrings, UI copy, tests, fixtures, OpenSpec artifacts, commits, issues, README, or user docs. The only permitted occurrence is this section (and the grep patterns in 6.1). Do not copy these strings elsewhere.

Use neutral vocabulary: Inbox, Processing Wizard / Clarification Pipeline, Step, Next step, Project, Reference, Category label, Person (a `category: person` reference). Write original copy; do not paraphrase proprietary material.

### 4.2 Object ownership and the architecture gate

Classify every new unit as one of: **value object** (immutable data + invariants), **service object** (owns one resource, validates it at construction), or **controller/view** (UI state + presentation). Split mixed roles. A stateless transformation is a method on the value object or service that owns the data, not a free function. No Java-style getters, anemic data bags, dependency-injection containers, service locators, or injected clocks; dependency inversion is expressed through explicit parameters and plain values.

Code is object-oriented: every behavior is a method on an owning class. Module-level functions are prohibited except `entrypoint` in `__main__.py`, the installed `afanes` script target, which delegates to `Launcher.main` in one line. Callback functions that a class or library receives as objects live on an owning class or as the local Flet entry closure. Apply SOLID, DRY, KISS, and YAGNI to the object graph: one responsibility per unit, composition over inheritance, narrow interfaces, and no speculative abstraction.

Prefer small, public, fruitful methods that return a value and can be tested directly. Keep a private method to an internal step of a public command; do not hide testable behavior in a large private helper.

`tests/core/test_architecture.py` is a hard gate:

- Module-level functions fail; the only allowed function is `entrypoint`, the installed script target.
- Ruff enforces `PLR0915` at 50 statements and selects the `PLR` family, including `PLR0913` and `PLR0911`; tests ignore `PLR0913`. `C901` is selected with the default complexity limit.
- Views must not define `_banner`, `_status_label`, `_panel`, or `_card`; shared helpers live in `ui/components/`.
- `AppState` may declare at most 10 annotated fields.
- `AppState` exposes at most 10 public names, counted as public annotated fields plus public commands.
- Any one domain controller may define at most 25 public commands.
- A class that declares state fields must define at least one public command.

Adding a duplicate view helper or an `AppState` field requires an approved change and an update to the gate. A free function is never added.

### 4.3 Python style, type checking, errors, and logging

- Target Python 3.13+. Use frozen slotted dataclasses for domain/value objects, `enum.StrEnum` for closed vocabularies, and `pathlib` for all paths.
- Annotate every public and private signature. Use built-in generics (`list[str]`, `dict[str, object]`), `X | None` instead of `Optional`/`Union`, and quoted forward references only when a real cycle makes them unavoidable. No `from __future__ import annotations`; Pyrefly strict is the type gate.
- No mutable module state in `core` or `models`. The `ui/state/` singleton is the only exception and must reset through `app_state.reset()`.
- `assert` is for invariants and tests only; validate untrusted input explicitly. No `eval`, `exec`, `pickle`, runtime `subprocess`, or `print` outside the CLI's dedicated output functions.
- Domain exceptions live in `core/errors.py`. Catch specific exceptions and preserve causes with `raise ... from exc`; never use a bare `except`. Use `logging.getLogger(__name__)` per module; never `logging.basicConfig` in library code. Do not log note bodies or absolute paths at INFO or above.
- Filename policy lives in `core/names.py`: reject reserved Windows device names, trailing dots or spaces, invalid characters, and case-insensitive collisions.
- Domain-policy constants are public `UPPER_CASE` names; access them through their module, never by importing constants.
- Source files under `src/` start with the AGPL-3.0-or-later SPDX header; keep it.

### 4.4 Docstrings

Strict NumPy-style docstrings are mandatory for every public module, class, enum, protocol, function, method, property, and public dunder. Include a one-line imperative summary, a blank line, then `Parameters` / `Returns` / `Yields` / `Raises` / `Attributes` / `Notes` as applicable. Types must match annotations exactly (`str | None`, `list[str]`). Test functions are exempt via `pyproject.toml` per-file ignores; do not weaken those ignores or silence D rules with `noqa`.

### 4.5 Vault writes

- All vault writes go through `afanes.core.vault.service.Vault`. UI and CLI never call `open(..., "w")` on a vault file.
- Resolve the root once; every candidate path must satisfy `is_relative_to(root)`. Reject traversal and symlinks that escape the vault.
- Write with `afanes.core.atomic.write_text_atomic` (same-directory temp file, fsync, `os.replace`).
- Preserve body, unknown frontmatter keys, and existing newline style. New files are UTF-8 without BOM, LF.
- Compare content before overwriting; if another program changed the file, stop and ask.
- Confirm rename and move. Trash is immediate and undoable: it moves to `trash/` and offers Undo in a toast; an irreversible action requires a confirmation. No recursive or permanent deletes, never follow symlinks, never touch paths outside the vault.
- Startup and scanning are read-only: opening or scanning a vault must not create files or folders. A valid read-only vault still opens for browsing.
- A vault root contains `afanes.yaml` with `schema_version: 1`. Opening requires it and never creates it. Creating a vault writes it before the default folders and starter content; adoption of an older folder writes only that file.
- One writer per vault; serialize writes.

### 4.6 Flet UI and concurrency

- Views are presentational. They call `afanes.ui.state.app_state` commands, then update controls; they never create state, parse Markdown, or do file I/O.
- The workspace shell has three regions: navigation (destinations, counts, vault identity, primary menu), browser (destination title, global search, actions, list/calendar/queue), and detail (page or focused flow with its toolbar). The primary menu sits above the navigation list. Search spans every destination and clears when the destination changes. The shell adapts at 1100 px (wide) and 1024 px (medium), and the minimum window is 1024x600.
- Flet desktop windows use native decorations and cannot host application controls in the title bar; the in-window headers are the structural equivalent of the reference header bar. Custom title-bar emulation is prohibited.
- `core/` and `models/` stay synchronous. Async belongs to the UI boundary and the CLI's top-level orchestration; blocking core I/O is reached through `asyncio.to_thread`.
- Never block the UI thread. Offload I/O with `asyncio.to_thread` or Flet's documented task mechanism and show progress. No `time.sleep` in UI code.
- One writer per vault; serialize writes so two commands cannot replace the same file concurrently.
- Colors, spacing, typography, and dimensions live in `ui/theme.py`; all user-facing copy lives in `ui/strings.py` and `cli/strings.py`. No magic hex colors or pixel values in views. The interface standard in `docs/develop/interface-standard.md` is the durable reference for the strict HIG target, the Adwaita 1.8.0 palette, the four surface roles, the neutral navigation-sidebar selection, the GNOME standard text roles, and the five Flet toolkit limits; `tests/ui/test_conformance.py` enforces the visual rules, and its baseline may only shrink.
- The earlier per-section icon-hue requirement is retired. Browser section icons are monochrome, and the active section uses the neutral selected-row fill. The accent is reserved for suggested actions, focus, links, and log marks. Do not reintroduce a per-section palette or an accent selection without an approved change.
- Copy follows the GNOME writing style: header capitalization for headings and short control labels, sentence capitalization for field labels and prose, no final period, ellipses only on actions that open further input or a confirmation, neutral tone without first- or second-person pronouns, and typographic apostrophes (`’`) and ellipsis (`…`). `tests/ui/test_copy.py` enforces these rules on both catalogs with no baseline; classify every new copy constant in its header-case or sentence-case set and run `hatch test tests/ui/test_copy.py` after a copy change. A new exception requires a standard change.
- Read `page.web` once in the shell; views must not branch on presentation.
- Feedback follows the lifetime of the event: a transient toast for a one-time result or undo, a banner owned by the state for a condition that remains true, inline text for a field or form problem, and an inline panel or dialog for a decision. A background refresh never clears an owned banner or a waiting notice.
- Show concise, actionable feedback, never tracebacks. A destructive action requires a confirmation or a visible undo path; trash moves immediately and offers Undo. Support light/dark, keyboard access, visible focus, and no color-only status.
- Persist only UI preferences such as window size and last view; never persist vault data in UI state.
- Cancel timers/tasks/subscriptions on dispose. Allow one active web session; a second must neither scan nor write.

### 4.7 Testing

- Mirror `src/` under `tests/` (`tests/core/vault/test_service.py`, ...). Use `Test<Behavior>` classes; test names describe behavior. One behavior per test, arrange-act-assert.
- Use `tmp_path` and fixture-created vaults. Never touch the real vault, the home directory, or the network. There is no shared `tests/conftest.py`; fixtures are local or autouse.
- Reset the UI singleton in UI tests: `afanes.ui.state.app_state.reset()`.
- Use Hypothesis for parser round-trips, reference extraction, name normalization, filename sanitization, path containment, and frontmatter types. Add a deterministic regression test for every minimized failure.
- Do not import, call, monkeypatch, or test leading-underscore members. Promote the behavior if it needs coverage.
- `pytest-randomly` is active: tests must not depend on order or shared mutable state. `--strict-markers` is on and no custom markers are registered; register any marker in `pyproject.toml`.
- Coverage minimum is 85% (`fail_under`); parser, link, and vault modules should stay at 90% or higher.

### 4.8 Definition of Done

- [ ] The approved change's tasks are all checked and the behavior is implemented.
- [ ] New behavior has tests; bug fixes have regression tests.
- [ ] Documentation is updated for the affected behavior, or the change records why no user-facing documentation changed.
- [ ] `hatch run docs:build` passes when `docs/` or the documented examples change.
- [ ] `hatch check` passes.
- [ ] `hatch test --cover` passes at 85% or higher.
- [ ] `openspec validate --all --strict` and `openspec doctor` pass.
- [ ] No prohibited vocabulary; no runtime network, telemetry, or cloud dependency.
- [ ] Vault writes are atomic, path-contained, and preserve unknown data.
- [ ] The diff is scoped, cross-platform, and free of unrelated formatting churn.

## 5. OpenSpec workflow

### 5.1 The specification gate

No implementation without an approved OpenSpec change. Implementation includes source, tests, dependencies, tool configuration, schema, UI/CLI, and behavior-changing docs. Before approval you may read, analyze, write or revise artifacts, and run read-only diagnostics. If asked to code directly, explain the gate and offer a minimal change. Only a maintainer may waive it in writing; record the waiver.

### 5.2 Applying a change

1. Name the change explicitly; run `openspec status --change "<name>" --json`.
2. Run `openspec instructions apply --change "<name>" --json` and read every returned context file.
3. Work one task at a time; keep the diff scoped. Check `docs/` for the behavior the task changes and update the page, or record why the change has no user-facing documentation effect.
4. Run the narrowest relevant tests, then check the task checkbox at its exact path and line.
5. Commit each task or coherent unit as soon as it is green. The subject names the behavior (`feat(processing): add append-step outcome`), not the version. Checkbox edits travel with their commit.
6. Never accumulate implementation work for a later release commit; a history of only `chore(release)` is a blocking review finding.
7. If a task is ambiguous or needs behavior beyond the spec, stop and propose an artifact update. Never mark a partial or deferred task complete.

A propose workflow stops after presenting artifacts. Do not start implementation in the same response.

Archive only after approval and completion. `openspec archive` updates `openspec/specs/`; do not copy deltas by hand. Use `--skip-specs` only for genuine no-behavior changes.

### 5.3 Post-archive release

Every successful archive, including `--skip-specs`, ends with a release step.

1. **Bump only when the archive completes a coherent milestone.** `1.0.0` is reserved for the first usable MVP (open a vault, capture, clarify, browse, review without hand-editing files); the checklist, platform evidence, and version path live in `RELEASE.md`. Incompatible changes to unreleased APIs are MINOR or PATCH, never MAJOR. If no milestone completes, keep the entry under `Unreleased` and skip the bump. Never edit `src/afanes/__about__.py`; use `hatch version patch|minor|major`.
2. **CHANGELOG.md** (Keep a Changelog 1.1.0, SemVer): move `Unreleased` entries under `## [X.Y.Z] - YYYY-MM-DD`, leave a fresh empty `Unreleased`, use only Added/Changed/Deprecated/Removed/Fixed/Security, write observable outcomes, name the change, record resolved runtime dependency versions, and list moved or removed public APIs with replacements. Update comparison links only when release tags exist; never rewrite a released entry.
3. **README.md and docs/**: update the landing page for installation, quick start, features, platforms, configuration, CLI, or stale behavior, and update the affected docs pages. Record `README: no change required` and `Docs: no change required` when neither changed.
4. **Gates**: `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the 6.1 compliance check.
5. **Commit** the archive move, synced specs, and release artifacts together. The subject names the delivered behavior; the body contains `Archived OpenSpec change: <name>` and, when bumped, `Release: vX.Y.Z`. Do not tag, push, or publish unless asked.
6. **Report** the previous/new version, bump rationale, changelog section, README status, docs status, and commit hash.

If the archive succeeds but the release step fails, leave the work in the tree, report the failure, and do not create a partial release commit.

## 6. Verification

### 6.1 Compliance check

`rg` is unavailable; these commands must exit 1 with no output (`AGENTS.md` is excluded):

```bash
grep -rniE '\b(gtd|getting[ -]things[ -]done)\b' \
  --include='*.py' --include='*.md' --include='*.toml' --include='*.yaml' --include='*.yml' --include='*.json' \
  --exclude=AGENTS.md --exclude-dir=.git --exclude-dir=.venv --exclude-dir=build --exclude-dir=dist .

grep -rniE 'gtd|getting_things_done|getting-things-done|inbox_zero' \
  --include='*.py' --include='*.md' --include='*.yaml' \
  --exclude=AGENTS.md --exclude-dir=.git --exclude-dir=.venv --exclude-dir=build --exclude-dir=dist src tests openspec README.md
```

Before finishing, also confirm: no `print` in library/UI code, no tracebacks in UI messages, no secrets or user data in tests or fixtures, and no runtime network calls in application code.
