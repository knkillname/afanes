# Proposal

## Why

`AGENTS.md` section 5.8 and `CHANGELOG.md` both reserve `1.0.0` for "the first
usable MVP: open a vault, capture, clarify, browse, review without hand-editing
files". Every one of those flows is specified, implemented, and shipped at
`0.5.1`, and `README.md` documents them as working. So the project is either
already at the milestone it reserved, or "usable" includes criteria that are
not written down. Both readings are defensible, which means no future change
can say whether it completed the milestone.

The one concrete gap in `README.md` is verification, not capability: the macOS
and Windows packaged build, offline start, capture, and refresh checks are
described as performed by the maintainer on those machines, and the changelog
only records the Linux check. Signing, notarization, auto-update, and a release
pipeline are explicitly out of scope today. Whether any of those block `1.0.0`
has never been decided.

## What Changes

- Write a release-readiness definition for `1.0.0`: the user flows that must
  work without hand-editing a file, the spec requirements that back each flow,
  the platform matrix that must be verified, and the items explicitly excluded.
- Turn the definition into a checklist with evidence: for each item, name the
  spec, the automated test that covers it, and the manual check that cannot be
  automated on this machine.
- Record the outstanding platform work as explicit, owner-assigned checks
  rather than a README caveat: macOS and Windows build, offline start, capture
  byte comparison, and external-edit refresh.
- Set the version path: ship `0.6.0` as the checkpoint that groups the
  remaining work, then `1.0.0` once the checklist is green. Record what each
  step requires and who decides that it is met.
- Point `AGENTS.md` section 5.8, `CHANGELOG.md`, and `README.md` at the one
  definition so the three cannot drift again.

## Capabilities

None. This change writes release criteria and verification records; no
application behavior changes. `skip_specs: true` is declared in
`.openspec.yaml`.

### New Capabilities

- None.

### Modified Capabilities

- None.

## Impact

- New `RELEASE.md` at the repository root, linked from `README.md`.
- `AGENTS.md` section 5.8 and `CHANGELOG.md` point at the same definition.
  Section 5.8 text depends on `reconcile-repository-guide` for final numbering.
- No source, test, dependency, or vault change.
- The checklist references existing specs; it does not modify them.

## Open Questions

None. The maintainer confirmed that `1.0.0` ships unsigned local builds
(signing, notarization, auto-update, and publishing stay out of scope), that
the checklist needs both automated evidence and a fresh-machine walkthrough,
and that `0.6.0` is the checkpoint before `1.0.0`.
