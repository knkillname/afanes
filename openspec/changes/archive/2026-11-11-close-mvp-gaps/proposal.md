# Proposal

## Why

The three-note milestone is implemented and archived, but three gaps keep the current release from
being usable and trustworthy end to end. Afanes still cannot be shipped: it runs only from a source
checkout, and a packaged build is exactly where the offline promise is untested. The workspace shows
a snapshot taken at the last scan, so a vault edited in any other program silently disagrees with
what the application displays. And the repository's own documentation still describes the retired
model it left behind, which misleads maintainers and agents that read the specs first.

All three are defects of the current milestone rather than new product surface. Closing them is what
makes `0.5.x` shippable and gives the next milestone an honest starting point.

## What Changes

- **Packaged desktop builds.** Add a documented `flet build` path for macOS, Linux, and Windows that
  bundles the interface client, derives its version from the project version, and starts with no
  network access. The documented checks include launching an artifact with networking unavailable.
- **Workspace liveness.** The workspace detects edits made outside the application and refreshes the
  browser, projects, and review lists without a manual refresh. An open page with a clean draft
  follows the change; a dirty draft raises the existing disk-conflict state instead of losing work.
  Background refresh is read-only and never clears a user-visible message.
- **Documentation alignment.** Rewrite the three stale capability purposes and bring the `AGENTS.md`
  layout and data-engine descriptions in line with what the repository actually contains, marking
  planned components as planned instead of describing them as present.
- No file-format, frontmatter, or reference-scheme change. No new runtime dependency. The build
  toolchain is a development prerequisite, not a shipped one.

## Capabilities

### New Capabilities

None. Packaging and liveness both extend capabilities that already own the behavior.

### Modified Capabilities

- `app-runtime`: a distributed desktop build must bundle the interface client and start offline, so
  the runtime guarantees extend from a source run to a shipped artifact.
- `vault-browsing`: the workspace must reflect edits made outside the application instead of showing
  only the last scan, while remaining read-only in the background.
- `note-editing`: an open page must follow an external edit when its draft is clean and raise the
  existing conflict state when the draft holds unsaved work.

The documentation alignment changes no requirement, so it adds no delta. That is deliberate: the
stale text sits in `## Purpose` paragraphs, and the OpenSpec apply step ignores a delta purpose on an
existing spec. The prose is corrected in place and recorded as work in `tasks.md`.

## Impact

- `src/afanes/ui/app.py` (session lifecycle and the refresh loop), `src/afanes/ui/state.py` (snapshot
  freshness, page reload and conflict decisions), `src/afanes/ui/views/` only where a refresh must
  repaint, `src/afanes/ui/strings.py` for any new message.
- `src/afanes/core/vault.py` for a cheap change fingerprint over the scanned files; no parser,
  frontmatter, link, or path-safety rule changes.
- `pyproject.toml` only if the build step needs a dedicated Hatch environment; no runtime dependency
  is added.
- `README.md` for the build commands and platform notes, `AGENTS.md` sections 3.1, 3.2, and 4.10 for
  the layout and data-engine status, and the three capability specs for their purpose paragraphs.
- Reviewers on macOS and Windows must confirm the packaged artifact and the refresh behavior; Linux
  is verified here.

## Open Questions

- `AGENTS.md` describes a SQLite indexer, `cli/index.py`, and `cli/doctor.py` that do not exist; the
  current implementation scans into memory per vault. This proposal aligns the text with reality and
  marks those components as planned. The alternative is to build the index in a separate change
  first. The maintainer decides; the documentation work assumes "mark as planned" until told
  otherwise.
- Code signing and notarization are out of scope for this change. Artifacts are unsigned local
  builds, and the README states that plainly.
- The refresh interval is a proposed default (see `design.md`). It is not a user-facing setting.
