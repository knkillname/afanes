# Design

## Context

See `proposal.md` - Why. The repository already has behavior specs for every
MVP flow and a build section in `README.md`. The missing artifact is a single
release-readiness record that maps those specs to automated and manual evidence,
and a version path that the guide, changelog, and README all cite.

## Goals / Non-Goals

**Goals:**

- One checked-in definition of `1.0.0` that names the five flows, their specs,
  and the tests that cover them.
- Explicit platform evidence, including the checks that can only run on macOS
  and Windows.
- A version path that separates the `0.6.0` checkpoint from the final `1.0.0`
  confirmation.

**Non-Goals:**

- Changing application behavior, specs, dependencies, or build tooling.
- Adding signing, notarization, auto-update, or a publishing pipeline.
- Claiming macOS or Windows verification that has not happened on those
  machines.

## Decisions

### D1. Put the definition in a root `RELEASE.md`

A dedicated file keeps the checklist readable and gives `AGENTS.md`,
`CHANGELOG.md`, and `README.md` one citation target. Keeping the list in the
guide would mix operating rules with release evidence; keeping it only in the
changelog would bury it after a release.

### D2. Every checklist line cites a spec and evidence

Each flow row names the capability spec, at least one automated test path, and
the manual check when the evidence cannot be produced on this machine. A line
without evidence is not a checklist item; it is a gap.

### D3. Treat exclusions as constraints, not gaps

Unsigned local builds, no notarization, no auto-update, and no publishing
pipeline are confirmed scope. They are recorded as constraints so a future
reader does not reopen them as missing work.

### D4. Use `0.6.0` as a checkpoint, not a release candidate

`0.6.0` groups the remaining platform verification and documentation. `1.0.0`
is declared only when the full checklist is green. The maintainer confirms both
transitions; no automated gate can prove a manual machine check.

## Risks / Trade-offs

- [The checklist goes stale as specs move] -> Every row cites a capability, not
  a line number, and the archive step updates citations when a spec changes.
- [A manual check is mistaken for automated coverage] -> The platform matrix has
  a separate evidence column and names the machine that must run it.
- [The version path drifts again] -> `AGENTS.md`, `CHANGELOG.md`, and `README.md`
  link to `RELEASE.md` instead of restating the definition.
