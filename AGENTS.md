# AGENTS.md

**Audience:** AI coding agents (OpenCode/DeepSeek and equivalents), maintainers, and reviewers.

**Status:** Initial operating manual. Changes to this file require an OpenSpec change or explicit maintainer direction.

**Read order:** `AGENTS.md` -> `README.md` -> `CHANGELOG.md` -> `pyproject.toml` -> relevant `openspec/specs/` -> active change artifacts -> code and tests.

**Precedence:** explicit user instruction within the constraints below > OpenSpec behavior specs > this file > local code patterns. If two sources conflict, stop and ask. Do not silently choose one.

**Tie-breaker:** when a design or style choice is still ambiguous, apply the Zen of Python (PEP 20). Beauty, explicitness, simplicity, flat structure, readability, and obviousness win. If the result is hard to explain, the design is wrong.

> This file contains prohibited vocabulary only in sections 4.2 and 6.6, where it is an enforcement target. Never copy those strings into product code, UI copy, tests, specs, commits, or user documentation.

---

## 1. Project Overview & Philosophy

### 1.1 What Afanes is

Afanes is a cross-platform desktop productivity engine and personal wiki. It captures unfiltered thoughts, clarifies them into action items or reference material, and organizes work through projects, due dates, people, and bidirectional name-based references.

The application is local-first. A user's vault is an ordinary directory of Markdown files that remains readable, editable, and portable without Afanes. The application is a lens over those files, not a replacement for them.

### 1.2 Product principles

1. **Files are the source of truth.** The vault of `.md` files is authoritative. Every durable fact must be recoverable from those files alone.
2. **Offline by default.** No accounts, cloud sync, telemetry, analytics, crash reporting, or background network calls. Build-time dependency installation is the only permitted network activity.
3. **Capture before structure.** The Inbox accepts raw, incomplete thoughts without forcing classification.
4. **Clarify explicitly.** The Processing Wizard turns ambiguous captures into typed records through small, reversible steps.
5. **The cache is disposable.** SQLite exists only to accelerate graph traversal, link resolution, timeline views, and full-text search. Deleting it must never lose user data.
6. **Strict separation.** The domain and persistence engine in `core/` knows nothing about Flet. The UI in `ui/` knows nothing about Markdown parsing or SQL.
7. **Cross-platform parity.** macOS, Linux, and Windows are equal targets. No platform is a second-class citizen.
8. **Neutral vocabulary.** The product and codebase use original, methodology-neutral language. See 4.2.
9. **Minimal dependencies.** Prefer the Python standard library. Every runtime dependency must justify its weight and remain offline-capable.
10. **Reversible operations.** Prefer atomic writes, confirmations, and recoverable states over destructive shortcuts.

### 1.3 Canonical file format

A vault is a directory tree containing Markdown files. New files use UTF-8 without a BOM and LF line endings. Existing files keep their current newline style when edited.

Each note has YAML frontmatter delimited by `---` at the start of the file, followed by a Markdown body.

```markdown
---
type: action
status: active
due_date: 2026-11-20
people:
  - "person:Ada Lovelace"
project: "project:Release 1.0"
---

# Release migration checklist

Draft the migration checklist and link it to [Release 1.0](<project:Release 1.0>).
```

Frontmatter contract:

| Key | Type | Rules |
| --- | --- | --- |
| `type` | string enum | Required. Initial values: `note`, `action`, `project`, `reference`. Extend only through an OpenSpec change. |
| `category` | string enum or absent | Optional on `reference` notes only. Initial value: `person`. A categorized reference belongs to its category scheme; an uncategorized reference belongs to the `note` scheme. |
| `status` | string enum or absent | Optional. Actions and projects: `active`, `waiting`, `done`, `cancelled`, `archived`, `later`. References: `later`, `archived`, or absent. Captures: absent. `inbox` is not a status. Per-type validity is defined by `models/` and the relevant spec. |
| `due_date` | ISO date or absent/null | `YYYY-MM-DD`, date-only, no timezone. A due date is a calendar date, not an instant. |
| `people` | list of strings | Zero or more `person:Name` references, for example `["person:Ada Lovelace"]`. |
| `project` | string or absent/null | At most one `project:Name` reference, for example `"project:Release 1.0"`. |

Rules for frontmatter:

- Unknown keys are preserved when a note is rewritten. Never silently drop data.
- Unknown enum values are not coerced. Surface a validation error and offer a raw edit path.
- A captured note has no `status`. The Inbox is the `inbox/` directory; capture adds no status, category, project, people, or due date.
- A person page is a `reference` note with `category: person`; `person` is not a note type. The `person` scheme resolves only to those notes. The `note` scheme resolves to `note`, `action`, and an uncategorized `reference`. A note belongs to exactly one scheme.
- The body is standard Markdown. Internal references use `[Label](scheme:Name)` with the schemes `person`, `project`, and `note`; use angle brackets when the name contains spaces, for example `[Ada](<person:Ada Lovelace>)`. Resolution rules live in `core/links.py` and the relevant spec.
- A malformed frontmatter block is a parse error, not an invitation to guess. Do not overwrite the file.
- New files use stable key order and canonical YAML. Existing files only have keys modified that the current operation owns.
- The filename stem is the note's identity and reference name. The display title is the first level-1 Markdown heading in the body, falling back to the stem when there is none; it is derived and never stored. Directories classify only; moving a note never changes a reference. No `id` or `title` key participates in identity.
- The format must remain human-editable. Do not introduce a hidden database-only field that is required to understand a note.

### 1.4 Core workflows

| Workflow | Required behavior | Primary code |
| --- | --- | --- |
| Inbox | Rapid capture of a raw thought as a Markdown file under `inbox/`. The first non-blank line becomes the filename and is written as a level-1 heading at the start of the body; all other text is preserved. No status or other classification is assigned at capture time; the Inbox lists the folder newest first and shows each note by display title with its vault-relative path as the secondary line. | `ui/views/inbox.py`, `core/vault.py` |
| Processing Wizard | Step-by-step clarification into one of Trash, Later, Reference, Action, or Project, with status, due date, people, and project assignment where applicable. People and project inputs suggest existing pages by display title or identity and store identities. Every step is explicit, previewed, and confirmed before writing. | `ui/views/processing.py`, `core/processing.py`, `core/vault.py` |
| Clarification Pipeline | The plan/apply state machine and validation used by the Processing Wizard. Must be testable without Flet. | `core/processing.py`, `core/vault.py`, `models/` |
| Timeline | Dynamic view ordered by `due_date`, including overdue and undated buckets. | `ui/views/timeline.py`, `core/search.py` |
| People / Contacts | Network view over reference notes with `category: person` and their bidirectional links to actions, projects, and references. | `ui/views/people.py`, `core/links.py` |
| Next Actions | Matrix view over open action items. Exact axes and filters are defined by the spec, not improvised in the UI. | `ui/views/next_actions.py`, `core/search.py` |

The default vault layout is `inbox/` for captures, `trash/` for recoverable discards, `reference/` for non-actionable notes with category folders such as `reference/people/`, `projects/` for outcomes, and `actions/` for single steps. These are default destinations, not required structure. Notes under `trash/` are excluded from scans, identity, and reference resolution.

### 1.5 What Afanes is not

- Not a cloud service, sync product, account system, or collaboration platform.
- Not a general-purpose document editor. Markdown is the interface and the storage format.
- Not a task database. SQLite is an index and cache, never the system of record.
- Not a clone or rebrand of any proprietary productivity methodology. All vocabulary and workflows are original and neutral.

---

## 2. Tech Stack & Tooling

### 2.1 Runtime

- CPython **3.13+** only. `pyproject.toml` declares `requires-python = ">=3.13"`.
- Do not target 3.12 or earlier. Do not use syntax or standard-library behavior that requires 3.14+ unless the spec explicitly raises the baseline.
- Prefer the standard library: `pathlib`, `sqlite3`, `argparse`, `dataclasses`, `enum`, `datetime`, `logging`, `tomllib`, `contextlib`, `collections.abc`.
- `pyproject.toml` is the single source of project metadata and tool configuration. Do not add `setup.py`, `setup.cfg`, `requirements.txt`, `Pipfile`, `poetry.lock`, `uv.lock`, or ad-hoc virtual environments.

### 2.2 Environment and dependency management

- **Hatch 1.18+** is the only developer-facing environment, build, test, and check interface.
- Hatch may use `uv` internally for its built-in check and test environments. Agents must not invoke `uv`, `pip`, `poetry`, or `conda` directly. The only `.venv` in the repository is the Hatch-managed development environment; never create one manually.
- `[dependency-groups]` is the single source of truth for development tool versions. The `dev` group contains the full editor toolchain; the `test` group contains test-only extras and is included by `dev`.
- `[tool.hatch.envs.default]` uses Hatch's `uv` installer, lives at `.venv/` in the project root (`path = ".venv"`), and installs `dependency-groups = ["dev"]`. This gives `.venv` Ruff 0.13.2, Pyrefly 1.0.0, pytest 9.x, pytest-mock, pytest-randomly, pytest-rerunfailures, pytest-xdist, coverage 7.x, coverage-enable-subprocess, and Hypothesis 6.x.
- The `.venv/` interpreter is `.venv/bin/python` on Linux/macOS and `.venv\\Scripts\\python.exe` on Windows. Editors and IDEs should select that interpreter; `.venv/` is already ignored by Git.
- Use `hatch shell` or `hatch run` to access these tools directly for diagnosis (`hatch run pytest`, `hatch run ruff`, `hatch run pyrefly`). The authoritative gates remain `hatch check` and `hatch test`.
- `hatch check` and `hatch test` run in Hatch's isolated internal environments (`hatch-check-*`, `hatch-test.*`), not in `.venv`; they are gate environments, not editor environments. Hatch supplies their core tool versions, while `hatch-test.*` and `hatch-check-types` add the `test` dependency group for test-only packages.
- When Hatch is upgraded, compare `hatch env show -i --json` with the `dev` group pins and update them together so local and gate environments stay aligned.
- Runtime dependencies use compatible-release ranges in `pyproject.toml`, with a lower bound that a `hatch-test` matrix environment exercises and an upper bound below the next major version. A lower bound that no test environment runs is not a supported version.
- Every release records the resolved versions of the ranged runtime dependencies in its changelog entry. The repository holds no lock file and no constraints file, so the release record replaces them.
- Express optional runtime components through the owning package's extras, for example `flet[desktop]` and `flet[web]`, so the resolver keeps the component and its host package on the same version. Never re-pin such a component to a patch version in this project.
- Development and test tools may use bounded ranges or exact pins; they never reach a runtime install.
- Every new dependency requires an OpenSpec change that states the need, alternatives considered, license, offline behavior, and cross-platform impact.
- Forbidden dependencies: cloud SDKs, hosted databases, analytics, telemetry, crash-reporting services, auto-update services, and anything that performs hidden network I/O.

### 2.3 Graphical user interface

- **Flet** (Python powered by the Flutter engine) is the GUI toolkit.
- Depend on Flet through a compatible-release range that stops below the next major. Widen or move the supported window only through an OpenSpec change.
- Target Flet 1.x. A Flet 1.x runtime downloads its desktop client on first use unless a packaged build or a pre-provisioned cache supplies it.
- Depend on `flet[desktop]` through the same range in the development group so source runs have a client, and let Flet's extra keep the client version locked to the SDK. Shipped desktop builds must bundle the client through `flet build`; a bare Python install is not a runnable offline desktop app.
- Treat the first development run as environment provisioning, never as product behavior. Application code must not trigger the client download from a shipped build.
- Use public Flet APIs only. Do not depend on private modules, internal widget trees, or undocumented behavior.
- Do not mix incompatible Flet API generations in the same codebase.
- The UI must be lightweight and 100% cross-platform on macOS, Linux, and Windows.
- The UI follows the single-`AppState` controller pattern described in 4.11.
- The desktop window is the default presentation. The browser presentation is an explicit opt-in mode; the application must never switch presentation on its own, and a failed desktop launch must name `--web` as the alternative.
- A browser session binds the loopback interface only, serves every interface asset from the local installation, and allows one active session; see 4.11.
- Never install or download a runtime package while starting. Check for the package and report the install command instead.

### 2.4 Persistence and data engine

- **Markdown + YAML frontmatter** is authoritative.
- Parse the frontmatter block with an explicit `---` fence parser and load it with `PyYAML` `safe_load`; serialize with `safe_dump`. Never use `yaml.load` or an unsafe loader.
- Parse Markdown bodies with `markdown-it-py` so reference extraction follows CommonMark rather than a hand-rolled scanner.
- **SQLite** via the standard-library `sqlite3` module is the derived graph index and search cache. No ORM.
- The cache may be file-backed or in-memory. It must be fully rebuildable from the vault.
- Use SQLite FTS5 for local full-text search when available. Detect FTS5 support at runtime and fall back to `LIKE` queries if it is unavailable.
- WAL mode, a versioned schema table, parameterized SQL, and explicit transactions are mandatory.

### 2.5 Command-line interface

- Use the standard-library `argparse` module. No Click, Typer, or other CLI framework.
- The CLI is a thin adapter over `core/` and `models/`. It contains no business logic.
- CLI commands must work headless. They must never import Flet or require a display server.
- Exit codes: `0` success, `1` expected operational failure, `2` usage error (argparse default).
- Human-readable output is the default. Add `--json` only where machine-readable output is specified.

### 2.6 Specification and quality tooling

- **OpenSpec 1.17+** with the `spec-driven` schema. The spec home is `openspec/`. The repository also ships OpenCode skills and commands under `.opencode/`.
- **Hatch 1.18+** built-ins are authoritative:
  - `hatch check` runs Ruff lint, Ruff format verification, and Pyrefly type checking.
  - `hatch test` runs pytest with coverage, `pytest-xdist`, `pytest-randomly`, `pytest-rerunfailures`, and `pytest-mock`.
- **Ruff** is the only linter and formatter. Effective configuration is the Hatch-generated default rule set plus the project rules in `pyproject.toml`:
  - 120-character lines, double quotes, magic trailing commas.
  - Module imports only; the first-party package is `afanes`. Relative imports and direct function/constant imports are forbidden; direct imports are limited to CamelCase types and classes.
  - Additional rule families: `D` (docstrings), `ANN` (annotations), `C90` (complexity), `S` (security).
- **Pyrefly** is the only type checker, configured with `preset = "strict"` for `src/` and `tests/`.
- **NumPy-style docstrings** are mandatory for every public API; see 4.6 for the strict contract.
- **Coverage** must be at least 85% overall. Parser, link, vault, and indexer modules should target 90% or higher.
- **Hypothesis** is required for property-based tests of parsing, link extraction, and path containment.
- Do not add a second linter, formatter, type checker, test runner, or coverage tool. Do not use `hatch fmt`; it is deprecated in favor of `hatch check`.

### 2.7 Dependency summary

| Dependency | Scope | Rule |
| --- | --- | --- |
| Python | runtime | 3.13+ only |
| Hatch | development | 1.18+; sole workflow interface |
| Flet | runtime | compatible-release range; library and public APIs only |
| Flet runtime clients | optional runtime | `flet[desktop]` in the development group and `flet[web]` as an extra; install only the presentation in use |
| markdown-it-py | runtime | compatible-release range; CommonMark parsing only |
| PyYAML | runtime | compatible-release range; `safe_load` / `safe_dump` only |
| SQLite / FTS5 | runtime | stdlib; optional FTS5 with fallback |
| argparse | runtime | stdlib CLI |
| Hypothesis | test only | property-based tests |
| Ruff / Pyrefly / pytest / coverage | development | Hatch-managed |

---

## 3. Repository Structure Guide

### 3.1 Target layout

Create directories only when a change needs them. This is the intended shape, not a mandate to add empty packages.

```text
afanes/
├── AGENTS.md
├── README.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── openspec/
│   ├── config.yaml
│   ├── specs/                     # main capability specs
│   └── changes/                   # active and archived changes
├── .opencode/
│   ├── commands/                  # opsx-* slash commands
│   └── skills/                    # OpenSpec workflow skills
├── src/
│   └── afanes/
│       ├── __init__.py
│       ├── __about__.py
│       ├── __main__.py            # GUI entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── errors.py          # exception hierarchy
│       │   ├── atomic.py          # shared atomic text writer
│       │   ├── frontmatter.py     # parse / serialize Markdown + YAML
│       │   ├── names.py           # name normalization and filename sanitization
│       │   ├── links.py           # scheme reference extraction and resolution
│       │   ├── vault.py           # vault discovery, path safety, note operations
│       │   ├── processing.py      # processing plan, outcomes, and apply
│       │   ├── indexer.py         # incremental SQLite index
│       │   ├── search.py          # timeline, people, next-actions queries
│       │   └── settings.py        # platform paths and app configuration
│       ├── models/
│       │   ├── __init__.py
│       │   ├── note.py            # NoteType, ReferenceCategory, Status
│       │   ├── action.py          # ActionItem
│       │   ├── project.py         # Project
│       │   └── link.py            # NoteReference and ReferenceScheme
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── app.py             # Flet app shell and navigation
│       │   ├── state.py           # single AppState controller
│       │   ├── theme.py           # colors, spacing, typography
│       │   ├── strings.py         # centralized user-facing copy
│       │   ├── views/
│       │   │   ├── inbox.py
│       │   │   ├── processing.py
│       │   │   ├── timeline.py
│       │   │   ├── people.py
│       │   │   └── next_actions.py
│       │   └── components/
│       │       ├── __init__.py
│       │       ├── note_editor.py
│       │       └── link_chip.py
│       └── cli/
│           ├── __init__.py
│           ├── main.py            # argparse parser and dispatch
│           ├── index.py           # index / rebuild commands
│           └── doctor.py          # vault and cache diagnostics
└── tests/
    ├── conftest.py
    ├── core/
    ├── models/
    ├── ui/
    └── cli/
```

### 3.2 Package responsibilities

| Path | Owns | Must not contain |
| --- | --- | --- |
| `src/afanes/models/` | Domain types, enums, value objects, validation rules | File I/O, SQL, Flet imports, `core/` imports, `ui/` imports, `cli/` imports |
| `src/afanes/core/` | Markdown/frontmatter parsing, name normalization, scheme reference resolution, vault I/O, SQLite indexing, search, platform paths | Flet imports, `ui/` imports, `cli/` imports, network calls |
| `src/afanes/ui/` | Flet app shell, views, components, `AppState`, theme, user-facing strings | Markdown parsing, SQL, direct file I/O, business rules |
| `src/afanes/cli/` | argparse definitions, headless commands, output formatting | Flet imports, business rules, direct SQL |
| `tests/` | Unit, property, integration, and architecture tests | Real user vaults, network access, committed secrets |

### 3.3 Import rules

The dependency graph is a DAG:

```text
models  <-  core  <-  ui
                  <-  cli
```

- `models/` imports only the standard library.
- `core/` may import `models/`.
- `ui/` may import `core/` and `models/`.
- `cli/` may import `core/` and `models/`.
- `ui/` and `cli/` must never import each other.
- `core/` must never import `ui/` or `cli/`.
- `models/` must never import `core/`, `ui/`, or `cli/`.
- No circular imports, including type-only imports and submodule cycles. Do not use `from __future__ import annotations` and do not use `typing.TYPE_CHECKING`. Import types at runtime and keep the graph acyclic. If a forward reference is unavoidable, quote it.
- Import modules for functions and constants; import CamelCase types and classes directly from their defining module. For example, use `import afanes.core.frontmatter` and `afanes.core.frontmatter.parse_note(...)`, but `from pathlib import Path`, `from collections.abc import Sequence`, and `from afanes.models.note import NoteType`. Do not qualify a class through its module when a direct import is available. Module qualification is appropriate when the module namespace itself is the subject, such as an architecture or export test that inspects many symbols, and when the owning library mandates its import convention (for example, pytest fixtures use `pytest.MonkeyPatch` with `import pytest`).
- Do not import functions, constants, enum members, or lowercase classes directly. Relative imports and `from afanes.core.frontmatter import parse_note` are forbidden.
- Use the full dotted module path (`import afanes.core.frontmatter`). Do not use `from afanes.core import frontmatter`; the project standard is an explicit module import. Do not re-export implementation symbols from `__init__.py`.
- Relative imports are rejected by the Hatch Ruff defaults. Architecture tests must reject the remaining forbidden import forms.
- No wildcard imports. No import-time side effects that open files, connect to SQLite, or read the environment beyond simple constants.
- The dependency graph is acyclic at both package and submodule level. Within `core/`, `vault.py` may import `frontmatter.py`, but `frontmatter.py` must not import `vault.py` or `indexer.py`. Within `ui/`, `app.py` may import views and state; views may import components, state, theme, and strings; components may import theme and strings; state may import `core/` and `models/`; `theme.py` and `strings.py` must not import other `ui/` modules. `state.py` must never import views or components.
- Keep every `__init__.py` thin. It may define a package docstring and stable public type aliases, but must not re-export implementation functions or create hidden cycles.
- Do not hide a cycle with a function-local import, `importlib`, or a lazy proxy. Restructure the modules instead.

### 3.4 Placement guide

| Change | Location |
| --- | --- |
| New frontmatter field or parser rule | `models/`, `core/frontmatter.py`, relevant spec |
| New reference syntax, scheme, or resolution rule | `core/links.py`, `core/names.py`, `models/link.py`, relevant spec |
| New vault operation | `core/vault.py`, tests, spec |
| New index table or query | `core/indexer.py`, `core/search.py`, schema migration, spec |
| New screen | `ui/views/`, `ui/state.py`, `ui/strings.py`, tests |
| New reusable Flet control | `ui/components/`, tests where practical |
| New CLI command | `cli/`, core service, spec |
| New dependency | OpenSpec change, `pyproject.toml`, this file if policy changes |
| One-off investigation script | Outside `src/` and `tests/`; never commit it |

---

## 4. Agent Operating Rules & Code Standards

### 4.1 Non-negotiable constraints

1. **Offline only.** No runtime network calls, telemetry, analytics, cloud storage, account systems, or hidden update checks. Build-time package installation through Hatch is the only network activity.
2. **Files are truth.** Never make SQLite authoritative. Never store the only copy of a user fact in the cache.
3. **Architectural separation.** `core/` has zero Flet imports. `ui/` has zero parsing, SQL, and direct file I/O. Enforce this with tests where practical.
4. **No prohibited methodology vocabulary.** See 4.2.
5. **No data loss.** Use atomic writes, preserve unknown frontmatter, and confirm destructive operations.
6. **No unapproved dependencies.** Add one only through an OpenSpec change.
7. **No secrets or user data in the repository.** This includes tests, fixtures, logs, screenshots, and commit messages.
8. **No unrelated refactors.** Keep each change scoped to its OpenSpec tasks. Do not mix formatting-only churn with behavior changes.
9. **No unverified claims.** Do not report that tests, linting, or type checking pass unless you ran the exact commands.
10. **Cross-platform by default.** Use `pathlib`, avoid OS-specific assumptions, and consider case-insensitive filesystems.
11. **Acyclic dependencies and no DI.** Keep the import graph acyclic at package and submodule level. Do not use dependency injection, service containers, or injected collaborators; pass plain values and patch module behavior in tests.

### 4.2 Vocabulary and legal compliance

Afanes is independent and unaffiliated with any proprietary productivity methodology. The following strings are **prohibited product vocabulary**:

- `GTD`
- `Getting Things Done`
- Any abbreviation, plural, translation, hyphenated form, stylized form, or close variant of the above
- `Inbox Zero` and similar proprietary slogans

These strings must never appear in source code, identifiers, comments, docstrings, UI elements, tests, fixtures, OpenSpec artifacts, commit messages, issues, README files, or user documentation. The only permitted occurrence is this enforcement clause. Do not copy this clause into other files.

Approved neutral vocabulary:

| Concept | Use | Do not use |
| --- | --- | --- |
| Capture queue | **Inbox** | Proprietary method names |
| Classification flow | **Processing Wizard**, **Clarification Pipeline** | Proprietary method names |
| Single actionable unit | **Action Item** | Proprietary task terminology |
| Prioritized open work | **Next Actions** | Proprietary method names |
| Outcome containing multiple actions | **Project** | Proprietary method names |
| Non-actionable knowledge | **Reference** | Proprietary method names |
| Contact page | **Person** | Proprietary relationship terminology |

Additional rules:

- Do not copy proprietary text, diagrams, checklists, or workflow descriptions. Write original explanations.
- UI copy must be original, neutral, and free of method names or slogans.
- When in doubt, use a descriptive phrase rather than a branded term.
- Run the compliance check in 6.6 before completing a change.

### 4.3 Design principles: Zen of Python, SOLID, DRY, KISS

The Zen of Python (PEP 20) is the tie-breaker for every design and style decision. When two rules appear to conflict, choose the option that is beautiful, explicit, simple, flat, readable, and unsurprising. In particular:

- Beautiful is better than ugly.
- Explicit is better than implicit.
- Simple is better than complex; complex is better than complicated.
- Flat is better than nested.
- Readability counts.
- Special cases are not special enough to break the rules.
- Errors should never pass silently, unless explicitly silenced.
- There should be one obvious way to do it.
- If the implementation is hard to explain, it is a bad idea.

These principles are engineering constraints, not suggestions. Apply them at module, class, and function scope.

- **Single Responsibility (SRP).** A module, class, or function has one reason to change. `NoteDocument` parses and serializes notes; it does not query the index or render UI. `ui/state.py` coordinates UI state; it does not parse Markdown.
- **Open/Closed (OCP).** Extend behavior by adding new functions, modules, or explicit dispatch tables; do not rewrite stable call sites for every variant. Do not build plugin systems or registries unless the spec requires them.
- **Liskov Substitution (LSP).** Subtypes honor the contract of their base type. Prefer composition over inheritance. Do not use inheritance merely to share implementation details.
- **Interface Segregation (ISP).** Define small, purpose-specific `Protocol` types. Do not create broad interfaces that force implementers to supply unrelated methods.
- **Dependency Inversion (DIP).** High-level modules depend on stable public functions, small immutable value objects, and narrow `Protocol` types, not on private implementation helpers. Achieve this through acyclic module boundaries. Do not use dependency injection, service locators, or containers.
- **DRY.** Each rule has one authoritative implementation. Frontmatter validation, reference parsing, name normalization, path containment, and status transitions must not be duplicated across `core/`, `ui/`, and `cli/`. Apply the rule of three: abstract only after the third real duplication, and only when the abstraction is simpler than the duplication.
- **KISS.** Choose the simplest design that satisfies the spec. Prefer the standard library, plain functions, and frozen dataclasses or small frozen classes over frameworks, metaclasses, dynamic dispatch, or speculative abstractions.
- **Composition over inheritance.** Use dataclasses, functions, and small Protocols. Avoid deep class hierarchies and mixins.
- **Cohesive objects over function bags.** When functions share state or must preserve an invariant together, model that unit as a small frozen class with focused methods. `NoteDocument`, `NameCatalog`, `Settings`, and `Vault` are the reference examples: parsing, serialization, body replacement, and reference rewriting live with the note metadata they protect; catalog construction, candidate lookup, and resolution live with the name mapping they protect; schema validation lives with the settings value object and file I/O with its store; and vault operations live with the resolved root they protect. Keep constructors validated through factories, keep the method surface small, and do not add Java-style getter/setter ceremony or anemic data bags. Pure stateless transformations remain module-level functions. See **Object boundaries** below for the classification rules and review checklist.
- **Public by default, private by purpose.** A leading underscore is only for implementation details. Domain rules, formats, limits, security sets, and other policy are public constants, functions, or value objects; callers and tests read them through the module. If a private behavior needs testing, promote it instead of reaching into internals.
- **No dependency injection.** Do not add constructor injection, provider objects, service containers, or injected clocks, ID generators, or collaborators. Pass plain values as explicit parameters. A value object that carries its own immutable data is not dependency injection. Tests replace public module behavior with `monkeypatch` or `unittest.mock.patch`.
- **Acyclic dependencies.** The import graph, including submodules and type-only imports, must be a directed acyclic graph. Do not hide cycles with function-local imports, `importlib`, or `__init__.py` re-exports. Fix the design.
- **YAGNI.** Do not add extension points, configuration flags, or abstractions for hypothetical future needs. The spec defines the scope.

#### Object boundaries

Every new module, class, function, and method must fit one of four roles. State the role in the docstring when it is not obvious. If a unit fits two roles, split it.

| Role | Owns | Must not own | Reference examples |
| --- | --- | --- | --- |
| Value object | Immutable data and the local invariants that protect it; a validating factory such as `from_text` or `from_payload` | File I/O, environment access, SQL, UI state | `Settings`, `VaultNote`, `NoteDocument`, `NameCatalog` |
| Service object | One resource or cross-operation invariant; validates that resource at construction; exposes intent methods | Presentation, UI state, parsing rules owned by value objects | `Vault`, `SettingsStore` |
| Pure function | A stateless transformation with no hidden state or resource handle | File I/O, cached parsers, mutable module state | `normalize_name`, `safe_filename`, `parse_reference` |
| Controller / view | UI state and presentation; forwards intent to services | Markdown parsing, SQL, direct vault file I/O | `AppState`, `InboxView` |

Rules:

- Classify a new unit before writing it. If it mixes roles, split it rather than adding a comment that excuses the mix.
- A function that repeats the same resource parameter across operations is a service waiting to be born. Move the resource into a service and call methods on it.
- A data bag surrounded by free functions is not cohesive. Move behavior that protects the data onto the object, or make the object immutable and keep the transformation a pure function.
- Do not wrap a stateless transformation in a class merely to satisfy an "OOP" label. `normalize_name` stays a function.
- A service validates its resource at construction and raises a domain exception when the resource is missing or invalid. Do not defer invariant checks to every method.
- Methods express intent (`vault.capture(text)`), not filesystem steps (`move_file(root, ...)`). Keep resource paths inside the object that owns them.
- A low-level primitive with no owned resource may remain a module function even when it performs I/O; `write_text_atomic` in `core/atomic.py` is the reference example.
- Tests exercise the public contract of the object or function. Do not test private helpers; promote the behavior if it needs a test.
- Keep the dependency graph acyclic. A service may depend on value objects and pure primitives; a value object must not depend on a service or on file I/O.

Review checklist for a change:

- [ ] Does each new unit have one clear role from the table?
- [ ] Is data plus its invariant owned by one object, or is a free function still reaching into the data?
- [ ] Does a service validate its resource once at construction?
- [ ] Is a stateless transformation still a function?
- [ ] Are file I/O, environment access, and UI concerns outside value objects?
- [ ] Are tests targeting public methods rather than private helpers?
- [ ] Is the import graph still acyclic and within the layering rules in section 3.3?

### 4.4 Python style

- Target Python 3.13. Do not use 3.14-only syntax or standard-library behavior.
- **Do not use `from __future__ import annotations`.** The project standard is runtime-evaluable annotations. Use PEP 604 unions such as `str | None` and built-in generics such as `list[str]`. Quote forward references only when unavoidable, or restructure the code.
- Follow the import rules in 3.3: import modules for functions and constants, and import CamelCase types and classes directly from their defining module. Import order is enforced by Ruff's isort integration.
- Import matrix:

  | Allowed | Forbidden |
  | --- | --- |
  | `import functools` | `from functools import partial` |
  | `import dataclasses` | `from dataclasses import dataclass, field` |
  | `from typing import Self` | `from typing import cast` |
  | `import contextlib` | `from contextlib import suppress` |
  | `import pytest` | `from pytest import raises` |
  | `import hypothesis` | `from hypothesis import given` |
  | `import afanes.core.frontmatter` | `from afanes.core.frontmatter import parse_note` |
  | `from pathlib import Path` | `from afanes.__about__ import __version__` |
  | `from afanes.models.note import Note` | `from afanes.models.note import STATUS_LABELS` |
  | `from afanes.core.errors import NoteParseError` | `from flet import app` |
  | `import flet as ft` | `from collections import defaultdict` |

- Use the full dotted module path for first-party modules (`import afanes.core.frontmatter`). Do not use `from afanes.core import frontmatter`, even though it imports a module object; the standard is explicit full-module imports.
- Never import constants. Access them through the module, for example `import afanes.__about__` and `afanes.__about__.__version__`. Enum members are accessed through their enum class.
- Line length is 120 characters. Use double quotes, magic trailing commas, and Ruff formatting.
- Naming:
  - Modules and packages: `snake_case`.
  - Functions, methods, and variables: `snake_case`.
  - Classes and exceptions: `PascalCase`.
  - Constants: `UPPER_CASE`.
  - Private helpers: leading underscore.
  - Avoid abbreviations except established domain terms such as `id` and `url`. Prefer `note_path` over `np`, `person` over `prsn`.
- Domain-policy constants are public `UPPER_CASE` names: forbidden filename characters, reserved device names, byte limits, fallback names, note suffixes, frontmatter fences, unsafe URL schemes, and similar rules callers and tests must share. Implementation details such as compiled regexes, parser token tables, and internal edit plans stay private. Tests read public constants through their module and never duplicate the policy.
- Use `pathlib.Path` for all filesystem paths. Never build paths with string concatenation or hardcoded `/` or `\`.
- Use `enum.StrEnum` for closed vocabularies such as `NoteType` and `Status`.
- Use `@dataclasses.dataclass(frozen=True, slots=True)` for domain models and value objects. Keep local invariants in `__post_init__`; put parsing and cross-field validation in a `core/` factory that can raise domain exceptions.
- Never use mutable default arguments. Use `dataclasses.field(default_factory=...)`.
- Prefer pure functions. Keep I/O, clocks, environment access, and ID generation at the module boundary. Pass plain values such as paths, dates, and identifiers as explicit parameters. Do not use dependency injection: no constructor injection, service containers, provider frameworks, or injected collaborators. Tests replace module behavior with `monkeypatch` or `unittest.mock.patch`.
- No mutable module-level state in `core/` or `models/`. The single `ui/state.py` `AppState` singleton is the only permitted exception; expose a reset hook for tests. Module-level constants are allowed but must be accessed through their module.
- Use `assert` only for internal invariants and tests. Never use it to validate user input, because optimized mode removes it.
- No `eval`, `exec`, or `pickle` for untrusted data. No `subprocess` in application runtime. If a subprocess becomes necessary, require a spec, use `shell=False`, pass an argument list, and validate every path.
- No `print` in library, core, or UI code. Use logging. CLI output is the only place where printing user-facing results is acceptable, and it must go through a dedicated output function.
- Never use a bare `except:`. Catch specific exceptions and preserve the cause with `raise ... from exc`.
- Use `with` statements and the `contextlib` module (for example `contextlib.suppress`) for files, database connections, locks, and temporary resources.
- Comments explain *why*, not *what*. Do not leave commented-out code. Every `TODO` must reference an OpenSpec change or issue.
- Keep functions focused. The complexity limit is 10 (`C901`). Prefer functions under 50 lines. If a function needs more than five parameters, group related values in a dataclass.
- Public APIs must remain stable within a release. Breaking changes require an OpenSpec change and a migration note.

### 4.5 Type checking

- Annotate every function and method signature, including parameters, return types, and test functions.
- Use modern Python 3.13 typing: `X | None`, `list[str]`, `dict[str, int]`, `tuple[str, ...]`, abstract types from `collections.abc` (`Iterable`, `Mapping`, `Sequence`), and `Self` for methods that return the concrete class. Import `Iterable`, `Mapping`, and `Sequence` from `collections.abc`, and `Self` from `typing`; access any other typing member through the `typing` module.
- Do not use `Optional`, `List`, `Dict`, `Tuple`, `Union`, quoted forward references, or `from __future__ import annotations`.
- Avoid `Any` in public APIs. Use `object` at true boundaries and narrow it, or define a `Protocol` or generic type.
- `# type: ignore[code]` is a last resort. It must include the specific error code and a justification comment. Prefer `typing.cast` with a comment explaining the invariant.
- Do not use `typing.TYPE_CHECKING`. Import types at runtime, keep the import graph acyclic, and quote a forward reference only when unavoidable.
- Pyrefly strict mode must pass. Do not add configuration that weakens strictness for a module or file.
- Types do not validate untrusted data. Validate YAML, CLI arguments, and UI input at their boundaries before constructing domain models.

### 4.6 Docstrings

Strict NumPy-style docstrings are mandatory for every public API. Ruff enforces the `D` rule family with `convention = "numpy"` and the `ANN` annotation rules; reviewers enforce the section content that Ruff cannot check. A missing or incomplete docstring is a blocking review finding, not a style preference.

**Scope.** Every public module, package, class, exception, enum, `Protocol`, function, method, property, `classmethod`, `staticmethod`, and public dunder method requires a docstring. This includes `__init__`, `__call__`, `__enter__`, `__exit__`, `__iter__`, `__next__`, and `__len__` when they form part of the object's contract. Public dataclasses and enums document their fields and members in an `Attributes` section. Private helpers require a docstring whenever their behavior is not obvious from the name and signature.

**Required content.**

- A one-line imperative summary that ends with a period.
- A blank line after the summary, before the extended description or the first section.
- An extended description when the summary cannot convey the contract.
- `Parameters` documenting every public parameter, including positional-only, keyword-only, `*args`, and `**kwargs`. Omit `self` and `cls`. State accepted range, units, invariants, ownership, and defaults when they are not obvious from the annotation.
- `Returns` for every callable that returns a value. State the meaning and shape of the result. Omit `Returns` only for `-> None`; describe the side effect in `Notes` instead.
- `Yields` for generators, with the same detail as `Returns`.
- `Raises` for every exception a caller may reasonably handle. List domain exceptions from `core/errors.py`, never internal `AssertionError` invariants.
- `Attributes` for public dataclass fields, enum members, and class attributes.
- `Notes` for I/O, blocking behavior, thread or async constraints, path-safety requirements, ordering guarantees, and side effects.
- `See Also`, `References`, and `Examples` when they add real value.

**Formatting.**

- Types in docstrings must match the runtime annotations exactly: `str | None`, `list[str]`, `datetime.date`, not `Optional[str]`, `List[str]`, or `date`. When the annotation is `Self`, name the concrete class in the docstring so the reader sees the actual type.
- Use the canonical section order: summary, extended description, `Parameters`, `Returns` or `Yields`, `Raises`, `Attributes`, `See Also`, `Notes`, `References`, `Examples`.
- Underline each section heading with at least three hyphens, matching the heading length.
- Write parameter entries as `name : type` on one line, followed by an indented description. Write exception entries the same way.
- Put one blank line between sections and indent descriptions by four spaces.
- Do not use Google style, reStructuredText field lists, or Sphinx-only directives.
- Do not restate the signature. Document meaning, constraints, and failure modes.
- Do not use `# noqa: D...` to silence a docstring rule. Fix the docstring.
- Do not include prohibited vocabulary in docstrings or examples.

Test functions are not public API and remain exempt through the per-file ignores in `pyproject.toml`. Do not weaken those ignores to avoid documenting production code.

Example:

```python
import pathlib

from afanes.models.note import Note


def parse_note(path: pathlib.Path, vault_root: pathlib.Path) -> Note:
    """Parse a Markdown note from inside a vault.

    Parameters
    ----------
    path : pathlib.Path
        Absolute path to the note. The path must resolve inside ``vault_root``.
    vault_root : pathlib.Path
        Resolved root of the vault.

    Returns
    -------
    Note
        Parsed note with normalized frontmatter and the original body.

    Raises
    ------
    VaultPathError
        If ``path`` escapes ``vault_root`` or is not a regular file.
    NoteParseError
        If the frontmatter is malformed or contains an invalid enum value.

    Notes
    -----
    This function performs blocking file I/O. Call it from a worker thread when
    invoked from a Flet event handler.
    """
```

### 4.7 Domain models and data

- Domain models live in `models/` and are frozen, slotted dataclasses with enums and value objects.
- Models do not import Flet, `core/`, `ui/`, or `cli/`.
- Validate at the boundary that can raise domain errors. `models/` value objects stay standard-library-only and may enforce local invariants in `__post_init__`; parsing and cross-field validation that need domain exceptions happen in `core/` factories such as `NoteDocument.from_text` and `NameCatalog.from_entries`. Never use a bare `ValueError` at a public boundary unless the spec defines it.
- Normalize at the parse boundary:
  - `due_date` becomes `datetime.date | None`.
  - `people` becomes a tuple of `NoteReference` values with the `person` scheme.
  - `project` becomes a `NoteReference` with the `project` scheme.
  - `type`, `category`, and `status` become enums.
- Preserve the raw frontmatter mapping on the model so unknown keys can be written back. Do not discard unknown data.
- Identity is the filename stem: it is the note's name, identity, and reference target. The display title is derived from the first level-1 heading in the body, falling back to the stem when there is none; it is not stored and does not participate in identity. Directories are classification, never identity. No `id` or `title` key participates. Never rewrite paths or identities silently.
- Due dates are calendar dates. Do not attach a timezone or convert them to instants.
- People are stored as `person:Name` reference values. Resolve them through the name catalog; do not duplicate denormalized names into note bodies or auto-link bare words.
- Models are immutable and safe to pass across threads. Return new instances instead of mutating shared state.

### 4.8 Errors and logging

- Define a small exception hierarchy in `core/errors.py`, for example:
  - `AfanesError`
  - `VaultError`
  - `VaultPathError`
  - `NoteParseError`
  - `LinkResolutionError`
  - `IndexingError`
  - `ConfigurationError`
- Do not reuse built-in exception names. Use `IndexingError`, not `IndexError`.
- Core raises domain exceptions. The UI and CLI translate them into user-facing messages at the boundary.
- Never show a traceback in the UI. Log the full exception at debug level and show a concise, actionable message.
- Use `logging.getLogger(__name__)` at module level. Do not call `logging.basicConfig` in library code; configure handlers only in entry points.
- Do not log note bodies, personal data, or secrets at INFO or higher. Log vault-relative paths rather than absolute paths where possible.
- CLI errors go to stderr and return the documented exit code.
- UI errors use a banner or dialog with retry, raw-edit, or dismiss actions.
- Do not swallow exceptions. If degradation is intentional, log the cause with context and return an explicit fallback value.

### 4.9 Local file I/O safety

All vault writes must go through the `Vault` service in `core/vault.py`. UI and CLI code must never call `open(..., "w")` on a vault file directly. The low-level atomic primitive lives in `core/atomic.py`; `core/vault.py` and `core/settings.py` are its callers.

1. **Resolve the vault root once.** Store it as an absolute, resolved `Path`.
2. **Contain every path.** Resolve candidate paths and verify `candidate.is_relative_to(vault_root)`. Reject traversal and symlinks that escape the root.
3. **Write atomically.** Call `afanes.core.atomic.write_text_atomic`, which creates a temporary file in the same directory, writes UTF-8 bytes, flushes, `os.fsync`, then `os.replace`, and removes the temporary file on failure.
4. **Preserve user content.** Modify only the frontmatter keys owned by the operation. Preserve the body, unknown keys, and existing newline style. New files use LF and UTF-8 without a BOM.
5. **Detect external edits.** Before overwriting, compare a content hash or modification marker captured when the note was read. If the file changed, abort and ask the user.
6. **Confirm destructive operations.** Rename, move, trash, and any permanent deletion require explicit user confirmation. Trashing moves the note to the vault-local `trash/` folder; permanent deletion is not part of the current workflow.
7. **Serialize writes per vault.** Do not run concurrent writers. Use an application-level lock or a single-writer queue.
8. **Reject unsafe filenames.** Sanitize for cross-platform use, reject reserved Windows names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`), trailing dots or spaces, and invalid characters. Detect case-insensitive collisions.
9. **No recursive deletes.** Never follow symlinks during trash or deletion. Never move or delete outside the vault. `trash/` is excluded from scans, identity, and reference resolution.
10. **Read-only startup.** Application startup and index refresh must not write to the vault.
11. **Watch for external changes.** Debounce file-watcher events, coalesce bursts, and ignore the application's own atomic writes.
12. **Use tests, not the real vault.** All I/O tests use `tmp_path` or a fixture-created vault. Never touch a user's actual notes.

### 4.10 SQLite cache rules

- Store the cache in a platform-appropriate application-data directory with user-only permissions. Never store it inside the vault or the repository.
- The cache is derived data. Deleting it must lose only speed, never user facts.
- Maintain a schema version table. Migrations are forward-only. If the schema is incompatible, rebuild the cache instead of migrating user data, because there is no user data in the cache.
- Enable WAL mode, foreign keys, a busy timeout, and explicit transactions.
- Use parameterized SQL exclusively. Never interpolate values or identifiers into SQL strings.
- Use one connection per thread, or serialize access to a single connection. Never share a connection across threads.
- FTS5 is optional. Detect support at runtime and fall back to `LIKE` queries.
- Store only derived data: vault-relative paths, normalized frontmatter values, searchable body text, and link edges. Do not store secrets.
- Index updates are transactional. A failed reindex must not leave a partially visible state.
- A corrupt cache must be deletable and rebuildable from the CLI. The application should still start and offer a rebuild.
- `core/search.py` returns domain models, never raw rows. UI and CLI code must not contain SQL.

### 4.11 Flet UI standards

- There is exactly one `AppState` instance, owned by `ui/state.py` and exposed as a module-level singleton. Views import `afanes.ui.state` and use `afanes.ui.state.app_state`; they do not receive injected controllers and do not create additional state. Access it by module path, never with `from afanes.ui.state import app_state`. This is the only permitted mutable module-level state.
- Views are presentational. They build controls and forward user intent to `AppState` commands. They must not parse Markdown, run SQL, or read and write files.
- Event handlers call a controller method and then update the affected controls. Batch updates and call `page.update()` once per logical change, not once per control in a loop.
- Never perform blocking I/O on the UI thread. Use `asyncio.to_thread` or Flet's documented task mechanism, and show progress or a busy indicator for long operations.
- Use stable keys and `ft.ListView` for large collections. Avoid rebuilding the entire view tree for a small state change.
- Centralize colors, spacing, typography, and component dimensions in `ui/theme.py`. No magic hex colors or pixel values in views.
- Support light and dark themes. Do not rely on OS-specific fonts or rendering behavior.
- Accessibility is required: labels for controls, keyboard navigation, visible focus, sufficient contrast, and never color-only status.
- Centralize user-facing copy in `ui/strings.py` for future localization. Use neutral vocabulary and sentence case.
- Destructive actions require confirmation. Recoverable errors use a banner or dialog; do not expose tracebacks.
- Cancel timers, background tasks, and subscriptions when a view is disposed. Close any resources the view owns.
- Persist only UI preferences such as window size and last view. Never persist vault data in UI state.
- No background network calls. If a user explicitly opens an external link, require a spec and a clear user action.
- The interface has two presentations: a native desktop window and a loopback-only browser session. The shell reads `page.web` once; views must not branch on presentation.
- A browser session binds `127.0.0.1` only, serves every client asset from the local installation, and permits one active `AppState` session. A second session shows a notice and must not scan or write the vault.
- Never install a runtime package or fetch a client while starting. Report the missing package and the install command instead.
- Flet upgrades require an OpenSpec change and a manual verification pass on macOS, Linux, and Windows.

### 4.12 Async, threading, and concurrency

- Keep `core/` and `models/` synchronous. Async is permitted only at the UI event boundary and in the CLI's top-level orchestration.
- Offload blocking parsing, indexing, and file I/O with `asyncio.to_thread` or an equivalent documented mechanism.
- Never mutate Flet controls from a worker thread. Marshal updates through Flet's documented thread-safe path.
- Honor cancellation. Clean up temporary files, locks, and partial work when a task is cancelled.
- Do not create orphan tasks. Track and await or cancel every task started by a view.
- One writer per vault. The indexer and the note writer must coordinate through a lock or queue.
- File-watcher events are debounced and coalesced. A burst of writes must not trigger a burst of full reindexes.
- No `time.sleep` in UI code. Use Flet timers or async waits.
- Tests must be deterministic. Do not use sleeps or rely on real wall-clock timing.

### 4.13 Testing standards

- `hatch test` invokes pytest. Do not run pytest outside Hatch.
- Group related tests in classes named `Test<Behavior>` and use plain test methods. Shared fixtures live in `tests/conftest.py`.
- Never test production-private members: do not import, call, or monkeypatch a leading-underscore function, method, class, or module attribute. Test the public contract through a public entry point. If a private behavior is worth testing and has no public path, promote it to a public value object or function; do not reach into internals. Test-local helpers may be private because they are scaffolding, not the subject under test.
- Mirror the source layout:
  - `tests/core/test_frontmatter.py`
  - `tests/core/test_links.py`
  - `tests/core/test_vault.py`
  - `tests/core/test_indexer.py`
  - `tests/models/test_note.py`
  - `tests/ui/test_state.py`
  - `tests/cli/test_main.py`
- Test names describe behavior and outcome, for example `test_parse_note_preserves_unknown_frontmatter_keys`.
- Follow arrange-act-assert. One behavior per test. No logic or branching in tests.
- Use `tmp_path` and fixture-created vaults. Never use the real vault, the user's home directory, or the network.
- Use Hypothesis for parser round-trips, reference extraction, name normalization, filename sanitization, path containment, and frontmatter type handling. Add a deterministic regression test for every minimized failure.
- Do not use injected clock or ID objects. Tests replace time and identifier generation by patching the owning module with `monkeypatch` or `unittest.mock.patch`. Do not depend on the current date or random values unless the test controls them.
- UI tests exercise `AppState` commands and view models by patching public module-level collaborators with `monkeypatch` or `unittest.mock.patch`, and reset the `AppState` singleton between tests. Do not require a rendered Flutter window for ordinary unit tests.
- Integration tests cover a full workflow: capture in the Inbox, run the Processing Wizard, write the note, reindex, and query the resulting views.
- Add an architecture test that parses imports with `import ast` and fails on cycles or forbidden edges. Verify that `core/` never imports `ui/` or `cli/`, that `models/` imports only the standard library, and that submodule dependencies remain acyclic.
- Cross-platform tests must avoid path-separator assumptions and cover reserved names and case-insensitive collisions.
- `pytest-randomly` is enabled. Tests must not depend on execution order or shared mutable state.
- Mark slow or integration tests with a registered marker. Do not use retries to hide flaky tests.
- Never assert on exact SQLite file bytes. Assert on query behavior and returned models.
- Every bug fix includes a regression test. Every feature includes tests derived from the spec scenarios.
- Coverage must be at least 85% overall. Parser, link, vault, and indexer modules should target 90% or higher.

### 4.14 Definition of Done

A change is complete only when all of the following are true:

- [ ] The OpenSpec change artifacts are complete and approved.
- [ ] Every task in `tasks.md` is checked and the specified behavior is fully implemented.
- [ ] New behavior has tests; bug fixes have regression tests.
- [ ] `hatch check` passes.
- [ ] `hatch test --cover` passes with at least 85% coverage.
- [ ] `openspec validate --all --strict` passes.
- [ ] No prohibited vocabulary appears in code, tests, UI copy, specs, or commits.
- [ ] No runtime network calls, cloud dependencies, or telemetry were added.
- [ ] Vault writes are atomic, path-contained, and preserve unknown data.
- [ ] The change was reviewed for macOS, Linux, and Windows behavior.
- [ ] Relevant specs and documentation are updated.
- [ ] The diff is minimal and contains no unrelated formatting churn.

Archiving adds one more gate: the post-archive release workflow in 5.8 must complete before the work is reported as done.

---

## 5. OpenSpec & Task Execution Workflow

### 5.1 The specification gate

**No implementation without an approved OpenSpec change.**

Implementation includes source code, tests, dependencies, tool configuration, schema changes, UI changes, CLI changes, and documentation that changes behavior. The following activities are allowed before approval:

- Reading code, specs, and configuration.
- Answering questions and producing analysis.
- Writing or revising OpenSpec artifacts.
- Running read-only diagnostics.

If a user asks for code directly, explain the gate and offer to create a minimal OpenSpec change first. Do not write code and then retroactively invent a spec.

A maintainer may explicitly waive the gate in writing. Record the waiver in the change or commit. Agents must never waive the gate themselves.

### 5.2 Source of truth

| Concern | Authority |
| --- | --- |
| Product behavior | `openspec/specs/` plus the active change delta |
| Engineering standards | This file |
| Project and tool configuration | `pyproject.toml`, `openspec/config.yaml` |
| Current implementation | Code and tests, as evidence only |

Code and tests do not override a spec. If the implementation and the spec disagree, stop and surface the conflict. Do not silently update the spec to match the code.

### 5.3 Lifecycle

| Phase | Action | Command | Output |
| --- | --- | --- | --- |
| Explore | Understand the problem and existing behavior | `/opsx-explore` or read-only inspection | Findings, open questions |
| Propose | Create the change and all required artifacts | `/opsx-propose <change-name>` or `openspec new change "<change-name>"` | `proposal.md`, delta specs, `design.md` when required, `tasks.md` |
| Review | User reviews and approves the plan | `/opsx-update <change-name>` for revisions | Approved artifacts |
| Apply | Implement tasks only | `/opsx-apply <change-name>` | Code, tests, checked tasks |
| Validate | Verify behavior and quality | `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor` | Passing checks |
| Archive | Merge the change into main specs | `/opsx-archive <change-name>` or `openspec archive "<change-name>"` | Updated main specs, archived change |
| Release | Bump version, update changelog and README, commit | `hatch version <part>` (see 5.8) | New version, `CHANGELOG.md`, release commit |

The planning boundary is strict: a propose workflow stops after presenting artifacts. Do not start implementation in the same response, even if the original request asked for it.

### 5.4 Artifact requirements

Use the templates and instructions returned by OpenSpec. Do not invent a different structure.

**Proposal**

- Problem and user impact.
- Goals and non-goals.
- Scope boundaries.
- Success criteria.
- Risks and open questions.
- Explicit statement of what is out of scope.

**Delta specs**

- One capability path per concern.
- `ADDED`, `MODIFIED`, and `REMOVED` requirements.
- At least one scenario per requirement.
- Observable behavior, not implementation details.
- No code snippets unless the behavior is a data format that must be exact.
- Preserve existing capability paths and requirement wording where possible.

**Design**

Create it when the change affects architecture, data format, indexing, concurrency, security, or cross-platform behavior. It must cover:

- Architecture and data flow.
- File format or schema changes.
- Index schema and rebuild strategy.
- Failure modes and recovery.
- Migration or cache invalidation.
- macOS, Linux, and Windows impact.
- Test strategy.
- Privacy, offline behavior, and vocabulary compliance.

**Tasks**

- Small, ordered, and verifiable.
- Each task maps to a requirement or a necessary enabling step.
- Include tests, documentation, and validation.
- No vague tasks such as "implement the feature" or "make it work".
- A task is complete only when its specified behavior is fully implemented and verified.

### 5.5 Applying a change

1. Select the change explicitly. Announce it and how to override it.
2. Run `openspec status --change "<change-name>" --json` and read the schema and artifact state.
3. Run `openspec instructions apply --change "<change-name>" --json` and read every context file it returns.
4. Work one task at a time. Keep the diff scoped to that task.
5. After implementing a task, run the narrowest relevant tests, then mark the checkbox at its exact source path and line.
6. Before claiming completion, run the full quality gates.
7. If a task is ambiguous, stop and ask.
8. If implementation reveals a design issue or missing behavior, pause and propose an artifact update. Do not absorb scope silently.
9. If a task needs behavior beyond the spec, stop and ask for a spec change.
10. Never mark a task complete when it is partially done, deferred, or narrowed.

### 5.6 Validation and archive

- Run `openspec validate --all --strict`.
- Run `openspec doctor` and resolve relationship problems.
- Run `hatch check` and `hatch test --cover`.
- Confirm the Definition of Done in 4.14.
- Archive only after the user approves and the work is complete.
- `openspec archive` updates the main specs. Review the resulting diff; do not manually copy deltas into `openspec/specs/`.
- Use `--skip-specs` only for infrastructure, tooling, or documentation changes that genuinely have no behavior delta.
- After a successful archive, run the post-archive release workflow in 5.8 before reporting completion. `--skip-specs` does not skip the release.
- Keep the change name in the commit or pull request for traceability.

### 5.7 OpenSpec configuration

- `openspec/config.yaml` holds durable constraints that must guide artifact generation. Keep it concise and do not duplicate this entire file.
- Use the `context` field for constraints an agent cannot infer from the code, such as offline-only behavior, cross-platform requirements, or vocabulary rules.
- Use per-artifact `rules` only when a rule applies to a specific artifact type.
- Use `operations.archive.guidance` for advisory post-archive steps that must survive regeneration of the OpenSpec skills and commands.
- Changing OpenSpec configuration is itself a change. Update it through the normal workflow.

### 5.8 Post-archive release

Every successful archive, including `--skip-specs` infrastructure changes, ends with a release commit. Do not report an archive as complete until this workflow finishes.

1. **Choose the bump.** Derive it from the archived change, not from the size of the diff.
   - **MAJOR** for an incompatible change to a public Python API, the vault or frontmatter contract, a CLI command or flag, or a spec-defined behavior that requires user migration.
   - **MINOR** for backward-compatible new behavior: a new capability, view, command, option, frontmatter field, or user-visible workflow.
   - **PATCH** for backward-compatible fixes, documentation, refactors, performance work, tests, and tooling or process changes with no behavior delta.
   - Pre-1.0 releases follow the same rules. Do not treat `0.x` as permission to break users silently.
2. **Bump the version.** Run `hatch version patch`, `hatch version minor`, or `hatch version major`. Use `hatch version "<exact>"` only when the maintainer specifies the version, and `hatch version release` only to graduate a prerelease. An explicit downgrade requires `--force` and maintainer approval. Never edit `src/afanes/__about__.py` by hand. Confirm the new version with `hatch version`.
3. **Update `CHANGELOG.md`.** Follow Keep a Changelog 1.1.0 and Semantic Versioning.
   - Add a concise entry for the archived change to `Unreleased` when one is not already present.
   - Move every `Unreleased` entry into a new `## [X.Y.Z] - YYYY-MM-DD` section dated with the archive date.
   - Leave a fresh, empty `## [Unreleased]` section at the top.
   - Use only `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, and `Security`. Omit empty sections.
   - Write user-facing, observable outcomes. Do not paste task lists, commit messages, or internal file inventories.
   - Name the archived OpenSpec change in the entry when it helps traceability.
   - Update the comparison links so `[Unreleased]` compares the new version to `HEAD` and the new version links to its release tag. If release tags are not used, omit the links instead of linking to nonexistent tags.
   - Never rewrite an entry for a version that was already released or tagged. Ship a new patch release instead.
4. **Review `README.md`.** Update it when the change affects installation, quick start, features, supported platforms, configuration, CLI usage, or any statement that is now stale. If nothing needs to change, record `README: no change required` in the archive summary.
5. **Run the gates.** Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the compliance check in 6.6. Do not commit while any gate fails.
6. **Commit.** Create one commit for the archive and its release artifacts: `chore(release): vX.Y.Z`. The body must contain `Archived OpenSpec change: <change-name>`. Include the archived change directory, synced main specs, `src/afanes/__about__.py`, `CHANGELOG.md`, and `README.md` when it changed. Do not tag, push, or publish unless the maintainer asks.
7. **Report.** State the previous and new versions, the bump rationale, the changelog section, whether `README.md` changed, and the commit hash.

If the archive succeeds but the release workflow fails, leave the archive and version changes in the working tree, report the failure, and do not create a partial or misleading release commit. Multiple archives on the same day each get their own bump and release commit.

---

## 6. Commands Cheat Sheet

### 6.1 Environment setup

```bash
hatch env create          # create .venv/ with the development toolchain
hatch env show            # list environments
hatch env show -i         # include Hatch-internal check/test environments
hatch shell               # enter the .venv/ environment shell
hatch env prune           # remove all Hatch environments, including .venv/
```

The default environment includes the development toolchain. Verify it with:

```bash
hatch run ruff --version
hatch run pyrefly --version
hatch run pytest --version
hatch run coverage --version
hatch run python -c "import hypothesis; print(hypothesis.__version__)"
```

Do not run `pip install`, `uv sync`, `uv add`, `poetry install`, or create `.venv` manually.

### 6.2 Run the application

```bash
hatch run python -m afanes              # GUI entry point (once implemented)
hatch run python -m afanes.cli --help   # CLI entry point (once implemented)
hatch run python -c "import afanes; print(afanes.__version__)"
```

Add console-script entry points only through an OpenSpec change.

### 6.3 Tests

```bash
hatch test                                              # first compatible environment
hatch test --cover                                      # coverage report, 85% minimum
hatch test --cover-xml                                  # XML coverage report
hatch test tests/core/test_frontmatter.py               # one file
hatch test tests/core/test_frontmatter.py::TestFrontmatterParsing::test_round_trip
hatch test -k "frontmatter and not slow"                # pytest expression
hatch test -py=3.14                                     # one Python version
hatch test --all                                        # full matrix
```

`hatch test` is the authoritative pytest entry point. `hatch run pytest ...` is permitted for focused local diagnosis; never run bare `pytest` outside Hatch.

### 6.4 Lint, format, and types

```bash
hatch check                 # Ruff lint + Ruff format check + Pyrefly strict
hatch check --fix           # apply Ruff lint fixes and formatting
hatch check code            # Ruff lint only
hatch check code --fix      # Ruff lint fixes only
hatch check fmt             # Ruff format check only
hatch check fmt --fix       # Ruff formatting only
hatch check types           # Pyrefly strict type check
hatch check types --summarize
```

- `hatch check --fix` does not fix type errors. Fix those in code.
- `hatch fmt` is deprecated. Use `hatch check` and its subcommands.
- The development environment also exposes `hatch run ruff ...` and `hatch run pyrefly ...` for diagnosis; `hatch check` remains the authoritative gate.
- Effective Ruff configuration is the Hatch default rule set plus `[tool.ruff]` in `pyproject.toml`.
- Pyrefly strict mode comes from `[tool.pyrefly]` in `pyproject.toml`.

### 6.5 OpenSpec

```bash
openspec context --json
openspec list --json
openspec list --specs --json
openspec new change "<change-name>"
openspec status --change "<change-name>" --json
openspec instructions <artifact> --change "<change-name>" --json
openspec instructions apply --change "<change-name>" --json
openspec show "<spec-or-change>" --json
openspec validate --all --strict
openspec doctor
openspec archive "<change-name>"
```

OpenCode slash commands:

```text
/opsx-explore
/opsx-propose <change-name>
/opsx-update <change-name>
/opsx-apply <change-name>
/opsx-sync <change-name>
/opsx-archive <change-name>
```

Use `openspec archive` only after the change is complete and approved. It updates the main specs. A successful archive always triggers the release workflow in 5.8.

### 6.6 Compliance check

Run this before completing a change. Exit code `1` with no output means the check is clean.

```bash
rg -n -i --glob '!AGENTS.md' --glob '*.{py,md,toml,yaml,yml,json}' \
  '\b(gtd|getting[ -]things[ -]done)\b' .
```

Also check identifiers and filenames:

```bash
rg -n -i 'gtd|getting_things_done|getting-things-done|inbox_zero' \
  src tests openspec README.md
```

### 6.7 Build and release

```bash
hatch build
hatch version                 # print the current version
hatch version patch           # 0.0.1 -> 0.0.2
hatch version minor           # 0.0.1 -> 0.1.0
hatch version major           # 0.0.1 -> 1.0.0
hatch version "<exact>"       # maintainer-specified version
hatch version release         # graduate a prerelease
```

Version bumps happen only through the post-archive release workflow in 5.8. Never edit `src/afanes/__about__.py` by hand. `hatch publish` is maintainer-only. Do not publish without a passing quality gate and an approved change.

---

## Appendix A: Agent Pre-Flight Checklist

Before editing:

- [ ] Read this file and the relevant main specs.
- [ ] Identify the active OpenSpec change and its approved tasks.
- [ ] Confirm the change does not require a new dependency or schema migration.
- [ ] Locate the module that owns the behavior; do not put logic in the wrong layer.
- [ ] Check for prohibited vocabulary before writing UI copy or docstrings.

Before finishing:

- [ ] All tasks are checked.
- [ ] `hatch check` passes.
- [ ] `hatch test --cover` passes with at least 85% coverage.
- [ ] `openspec validate --all --strict` passes.
- [ ] Vault writes are atomic and path-contained.
- [ ] No network, telemetry, or cloud dependency was introduced.
- [ ] No user data or secrets were added to the repository.
- [ ] The diff is scoped and reviewed for cross-platform behavior.
- [ ] The completion summary states exactly which commands were run.
