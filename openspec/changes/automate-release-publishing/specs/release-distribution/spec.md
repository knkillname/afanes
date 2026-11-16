# Spec Delta

## Purpose

Defines how a release tag becomes a published GitHub release: which artifacts
Afanes ships, the agreement between tag, version, and changelog, the gates that
must pass, and the guarantees for checksums, failure, and immutability.

## ADDED Requirements

### Requirement: A release tag starts the release pipeline

Pushing a tag that matches `v<major>.<minor>.<patch>` SHALL build and publish a
GitHub release for that tag with no manual attachment step. A manual dispatch
SHALL remain available for dry runs and SHALL NOT publish.

#### Scenario: A pushed tag publishes a release

- **WHEN** a maintainer pushes the tag `v1.0.0` and every pipeline stage passes
- **THEN** a GitHub release named for `1.0.0` is published with its artifacts

#### Scenario: A manual dispatch publishes nothing

- **WHEN** the workflow is dispatched by hand for a dry run
- **THEN** it builds and stores the artifacts for inspection and creates no release

### Requirement: Routine changes do not create releases

Archiving a change SHALL NOT bump the version, tag the repository, or publish a
release. Entries SHALL accumulate under `Unreleased` in `CHANGELOG.md` until a
maintainer cuts a release deliberately.

#### Scenario: An archived change leaves no release

- **WHEN** a change is archived without a release decision
- **THEN** the version is unchanged, no tag is pushed, the new entry stays under `Unreleased`, and no release appears

#### Scenario: A release is a deliberate act

- **WHEN** a maintainer decides to release
- **THEN** they bump the version, move the `Unreleased` entries under the released heading, and push the tag that publishes it

### Requirement: Tag, project version, and changelog agree

The pipeline SHALL verify that the tag number equals the project version and
that `CHANGELOG.md` has a released section for that version. On any mismatch it
SHALL fail before building and publish nothing.

#### Scenario: The tag and version disagree

- **WHEN** tag `v1.0.1` is pushed while the project version is `1.0.0`
- **THEN** the pipeline fails, names both values, and publishes nothing

#### Scenario: The changelog has no released section

- **WHEN** the tag matches the project version but the changelog lists that version only under `Unreleased`
- **THEN** the pipeline fails and publishes nothing

### Requirement: Automated gates pass before publication

The pipeline SHALL run the project's lint, format, type, and test gates on the
tagged commit, and SHALL publish only when every gate passes.

#### Scenario: A failing gate blocks the release

- **WHEN** any automated gate fails for the tagged commit
- **THEN** the pipeline stops, reports the failing gate, and publishes nothing

### Requirement: A release carries both supported artifacts

Every release SHALL publish the Linux native bundle as a `.tar.gz` and the
platform-independent Python wheel, both built from the tagged commit.

#### Scenario: Both artifacts are attached

- **WHEN** a release is published
- **THEN** the release lists the Linux bundle and the wheel as downloadable assets

#### Scenario: The wheel supports both presentations

- **WHEN** the published wheel is installed with its browser extra
- **THEN** it provides the `afanes --web` browser path documented for macOS and Windows

### Requirement: Checksums accompany every artifact

A release SHALL include a checksum file with a SHA-256 entry for each published
artifact, and the release notes SHALL reproduce those checksums.

#### Scenario: A downloaded artifact is verified

- **WHEN** a user downloads an artifact and the published checksum file
- **THEN** the artifact's SHA-256 matches its entry

### Requirement: Release notes identify the build

The release notes SHALL name the version, the tagged commit, the workflow run,
the runner image, and each artifact's checksum.

#### Scenario: A user traces an artifact to its build

- **WHEN** a user reads a release's notes
- **THEN** the notes identify the commit, the run, and the checksum that produced each asset

### Requirement: A failed publication leaves no public release

If any build, gate, packaging, or upload step fails, the pipeline SHALL leave no
public release and SHALL NOT leave a partial release visible.

#### Scenario: An asset upload fails

- **WHEN** publishing creates the release but an asset upload fails
- **THEN** the pipeline removes the unpublished release it created and reports the failure

### Requirement: A published release is immutable

Re-running the pipeline for a tag that already has a published release SHALL NOT
overwrite or delete its assets. The pipeline SHALL fail and name the existing
release.

#### Scenario: A re-run does not replace published bytes

- **WHEN** the pipeline runs again for a tag whose release already exists
- **THEN** it fails, names the existing release, and changes no published asset

### Requirement: The first release records packaged desktop evidence

Before `v1.0.0` is pushed, the packaged manual gate SHALL run on an artifact
built from the same version and commit, and its results SHALL be recorded in
`RELEASE.md`.

#### Scenario: MVP evidence exists before the tag

- **WHEN** the maintainer prepares `v1.0.0`
- **THEN** the recorded evidence names the run, commit, runner image, checksum, and manual results for that version
