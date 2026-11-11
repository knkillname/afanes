# Design

## Context

See `proposal.md` - Why for the motivation. The following constraints shape the approach.

- `pyproject.toml` is the single source of metadata and tool configuration. `AGENTS.md` section 2.2
  forbids `uv.lock`, `requirements.txt`, `Pipfile`, and `poetry.lock`, so a lock file is not
  available as a reproducibility mechanism.
- `AGENTS.md` section 2.2 currently mandates exact runtime pins "for reproducible desktop builds";
  section 2.7 repeats it. Those clauses contradict the proposal and must be rewritten, not deleted.
- Flet ships its client and web runtime as separate packages pinned exactly to the SDK version:
  `flet==1.1.2` declares `flet-desktop==1.1.2; extra == "desktop"` and
  `flet-web==1.1.2; extra == "web"`. Flet also installs a replacement with `pip` at runtime when the
  installed runtime package's version differs from the SDK (`flet/utils/pip.py`), which is a
  network call the project forbids.
- The test suite runs in Hatch's isolated environments, so a floor environment must be expressible
  in `pyproject.toml`.
- Python 3.13 and 3.14 are both supported. Wheel availability bounds the floor independently of API
  compatibility: PyYAML 6.0.2 publishes CPython 3.13 wheels but no 3.14 wheels, while 6.0.3
  publishes both.
- The UI accesses `page.services`, `page.window`, `page.web`, `AppView`, `ft.run`, and
  `ft.FilePicker`. All exist in Flet 1.0.4, which was checked directly against that release.

## Goals / Non-Goals

**Goals:**

- An install that succeeds on a mirror carrying releases from roughly one month before this change.
- Adopting a patched release inside the same major without editing `pyproject.toml`.
- A lower bound that is exercised by the existing test suite in the normal quality gate.
- Version lockstep between `flet`, `flet-desktop`, and `flet-web` without Afanes hardcoding a patch.
- No lock file, constraints file, or vendored wheel in the repository.

**Non-Goals:**

- Proving compatibility across every 1.x release; the window is floor-to-latest.
- Making `flet` itself optional. That is deferred, and the web presentation mode that would justify
  it is proposed separately.
- Any change to `requires-python` or the supported interpreter set.
- Reproducible bit-for-bit environments. This design replaces that guarantee with a recorded release
  environment.

## Decisions

### Decision: compatible-release ranges with a major ceiling

```toml
dependencies = [
  "flet>=1.0.4,<2",
  "markdown-it-py>=4.0,<5",
  "PyYAML>=6.0.3,<7",
]
```

Each floor is justified by verified evidence rather than convenience:

| Package | Floor | Why that floor |
| --- | --- | --- |
| `flet` | 1.0.4 | All APIs used by `ui/` exist there. 1.x began on 2026-09-28, so a lower floor is a different API (`ft.app`, `page.overlay`, no services). |
| `markdown-it-py` | 4.0.0 | Only `MarkdownIt("commonmark").parse` and `Token` are used; 4.0 is the current major and is a year old. |
| `PyYAML` | 6.0.3 | First release with CPython 3.14 wheels; 6.0.2 would force a source build on the upper supported interpreter. |

Alternatives considered:

- `~=1.1.2` (equivalent to `>=1.1.2,<1.2`): rejected because the floor stays at the release mirrors
  lack, which is the reported failure.
- An exact pin on an older release (`flet==1.0.4`): rejected because it keeps blocking the patched
  releases a security review wants to adopt.
- No upper bound: rejected because an unreviewed major upgrade would reach users silently.

### Decision: runtimes as optional extras, Flet SDK stays in the base install

```toml
[project.optional-dependencies]
desktop = ["flet[desktop]>=1.0.4,<2"]
web = ["flet[web]>=1.0.4,<2"]
```

Using Flet's own extras transfers the lockstep obligation to the resolver: whichever Flet patch pip
selects, it also selects the matching `flet-desktop` or `flet-web`. Afanes declares a range once and
never has to keep three version numbers aligned by hand.

Alternatives considered:

- Listing `flet-desktop` / `flet-web` directly with independent ranges: rejected because the resolver
  could install mismatched patches, and Flet would then attempt a `pip install` at startup.
- Making `flet` optional too: rejected for this change. `ui/` imports Flet at module import time and
  the entry point would need an import guard, while the SDK wheel is small (0.66 MB) and contains no
  native client. Keeping it avoids an import-time failure mode that would need its own spec.
- Installing both runtimes by default: rejected because a web-only machine would still download the
  desktop client, which is the artifact some environments block.

### Decision: the floor is tested through a Hatch test matrix entry

Add a second matrix table to `[tool.hatch.envs.hatch-test]` that expands a floor environment for the
lower interpreter only, and use a `matrix.<dimension>` override to replace the three ranged
dependencies with their floor versions:

```toml
[[tool.hatch.envs.hatch-test.matrix]]
python = ["3.13", "3.14"]

[[tool.hatch.envs.hatch-test.matrix]]
python = ["3.13"]
deps = ["floor"]

[tool.hatch.envs.hatch-test.overrides]
matrix.deps.extra-dependencies = [
  { value = "flet[desktop]==1.0.4", if = ["floor"] },
  { value = "markdown-it-py==4.0.0", if = ["floor"] },
  { value = "PyYAML==6.0.3", if = ["floor"] },
]
```

The override targets `extra-dependencies` rather than `dependencies`, because the test environment owns
`dependencies` for its own tooling and replacing that list would drop pytest and coverage from the
floor run.

The floor environment runs the same tests with no exclusions. `hatch test --all` therefore proves
the floor. The floor entry pins `flet[desktop]` rather than `flet` so the extra's lockstep still
applies.

Alternatives considered:

- A standalone `hatch-test-min` environment: rejected because nothing runs it by default, so it rots.
- Testing the floor on both interpreters: rejected as duplicate cost; the floor decision is about
  API availability, which does not vary by interpreter, while wheel availability is already handled
  by choosing PyYAML 6.0.3.

### Decision: reproducibility moves from the manifest to the release record

`AGENTS.md` section 2.2 is rewritten so that the release workflow, not the dependency declaration,
records the resolved environment. At release time the resolved versions of the three ranged
dependencies are written into the changelog entry for that release. Nothing is committed as a lock
artifact.

Alternatives considered:

- A committed constraints file: forbidden by section 2.2 and is a lock file in all but name.
- Ignoring reproducibility: rejected because a bug reported against 1.4.0 would be unattributable.

### Decision: development tool pins remain exact

`ruff`, `pyrefly`, `pytest`, and the coverage tools keep their current pins. They do not participate
in a runtime install, and the Hatch gate environments already install them from `pyproject.toml`.
The `dev` group's `flet-desktop==1.1.2` becomes `flet[desktop]>=1.0.4,<2` so source runs resolve the
same way an end-user desktop install does.

### Decision: AGENTS.md policy text describes the new rule

Sections 2.2, 2.3, and 2.7 must state, in the project's own voice:

- Runtime dependencies use compatible-release ranges with an upper bound below the next major.
- The lower bound must be a release the test matrix exercises.
- Release notes record the resolved versions used for a release.
- Optional runtimes are expressed through Flet's extras, never through AFANES-side patch pins.

Removing the exact-pin sentence without replacing it would leave the next agent free to reintroduce
exact pins.

## Risks / Trade-offs

- A mirror synced less often than the floor's age still fails to install → Mitigation: document the
  floor as the supported minimum in `README.md`; the remedy is a mirror refresh, and lowering the
  floor below 1.0 is a UI rewrite, not a version bump.
- Testing the floor only on 3.13 misses a 3.14-specific wheel problem → Mitigation: the default 3.14
  environment still resolves the floor because pip picks the newest version satisfying the range,
  and the PyYAML floor was chosen for its 3.14 wheels.
- A future Flet 1.x release regresses behavior inside `<2` → Mitigation: the ceiling environment
  resolves the newest 1.x, so `hatch test --all` exercises both ends of the window.
- Removing exact pins makes a reproduction report ambiguous → Mitigation: the release record names
  the versions.
- A partially synced mirror has `flet` but not the matching runtime package → Mitigation: the
  resolver fails loudly at install time, which is the correct failure; `flet`'s runtime installer is
  never reached because the dependency is declared.
- The floor test doubles matrix size for one extra environment → Mitigation: only the lower
  interpreter gets a floor entry.

## Migration Plan

1. Rewrite `pyproject.toml`: ranges, `[project.optional-dependencies]`, dev group, floor matrix.
2. Create the Hatch environments and run the suite against the floor before changing any
   documentation, so a broken floor is discovered while the diff is small.
3. Rewrite `AGENTS.md` sections 2.2, 2.3, and 2.7 and the `README.md` install section.
4. Record the resolved versions in the changelog entry produced by the post-archive release step.

Rollback is a single revert of `pyproject.toml`, `AGENTS.md`, and `README.md`; no user data, cache
schema, or vault format is involved.

## Open Questions

- The cadence at which the target mirrors sync is unknown. It does not change this design: the floor
  is a supported minimum either way, and a mirror older than the floor is an environment problem
  rather than a version-range problem.
- Whether the `web` group should also join the `dev` group for a future end-to-end server test is
  deferred to the `web-runtime` change, which is where a server smoke test would live.
