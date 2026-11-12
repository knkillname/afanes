# Spec Delta

## ADDED Requirements

### Requirement: A distributed desktop build bundles the interface client

A desktop build produced for distribution SHALL include the interface client inside the artifact, so the application starts with no network access. Starting a packaged build MUST NOT download a client, check for updates, or contact any remote origin.

#### Scenario: Packaged build starts offline

- **WHEN** a packaged desktop build starts on a machine with no network access
- **THEN** the window opens and the workspace is usable

#### Scenario: First run downloads nothing

- **WHEN** a packaged desktop build starts for the first time
- **THEN** no client download occurs and no remote request is made

#### Scenario: Artifact carries the project version

- **WHEN** a packaged desktop build is produced
- **THEN** the artifact metadata reports the project version from the package metadata

#### Scenario: Packaged behavior matches a source run

- **WHEN** a packaged desktop build opens a vault, captures, and processes a note
- **THEN** the same files and frontmatter are written as in a source run

### Requirement: A failed build reports the missing prerequisite

When a packaging step cannot run, it SHALL report the missing prerequisite and the command that supplies it, and MUST NOT leave an artifact that appears installable.

#### Scenario: Missing toolchain is named

- **WHEN** the build toolchain required by the packaging step is unavailable
- **THEN** the build stops with a message naming the missing toolchain and no artifact is written

#### Scenario: Failed build leaves no installable artifact

- **WHEN** a packaging step fails partway through
- **THEN** no partial artifact is presented as installable
