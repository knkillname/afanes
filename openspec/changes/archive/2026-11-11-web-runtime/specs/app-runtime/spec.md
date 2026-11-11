# Spec Delta

## Purpose

Defines how Afanes starts, which presentation it serves, and the offline, network-binding, and
session guarantees each presentation must hold.

## ADDED Requirements

### Requirement: Desktop presentation is the default

Starting Afanes without options SHALL present the interface in a desktop window when the desktop
runtime is available. The browser presentation SHALL be requested explicitly with `--web` and SHALL
NOT be entered automatically.

#### Scenario: Default launch opens the desktop window

- **WHEN** the application starts with no options and the desktop runtime is available
- **THEN** it presents the interface in a desktop window

#### Scenario: Web option serves a browser session

- **WHEN** the application starts with `--web`
- **THEN** it serves the interface over a local web server and reports the address to open

#### Scenario: Desktop failure does not switch presentation

- **WHEN** the desktop client cannot start
- **THEN** the application reports the failure and does not start a web server instead

### Requirement: A missing runtime is reported, never installed

When the runtime package for the requested presentation is unavailable, Afanes SHALL name the
missing component and the install command, then exit with a non-zero status. It MUST NOT install
packages, download a client, or contact the network while starting.

#### Scenario: Web runtime package is absent

- **WHEN** the application starts with `--web` and the web runtime package is not installed
- **THEN** it reports that the web runtime is missing, names the install command, and exits non-zero

#### Scenario: Desktop client is absent or blocked

- **WHEN** the application starts without `--web` and the desktop client is missing or fails to launch
- **THEN** it reports the failure, names `--web` as the alternative presentation, and exits non-zero

#### Scenario: No installation is attempted

- **WHEN** a required runtime package is absent
- **THEN** no package manager process runs and no network request is made

### Requirement: Web presentation binds the loopback interface only

The browser presentation SHALL serve the interface on the loopback interface only. It SHALL NOT
expose the vault or the interface on a network interface, and it SHALL NOT provide authentication.

#### Scenario: Server listens on loopback

- **WHEN** the application starts with `--web`
- **THEN** the server accepts connections from the local host only

#### Scenario: Remote access is refused

- **WHEN** a request arrives from another host
- **THEN** the server refuses it and the vault remains unreachable

#### Scenario: Port is reported

- **WHEN** the web server starts on an automatically chosen port
- **THEN** the application reports the full local address including that port

### Requirement: Web presentation loads all client assets locally

The browser presentation SHALL serve every script, font, and rendering asset from the local
installation. It MUST NOT request any asset from a remote origin, so the interface remains usable
with no network access after installation.

#### Scenario: Interface works without networking

- **WHEN** the browser presentation starts on a machine with no network access
- **THEN** the interface renders fully and remains interactive

#### Scenario: No remote asset requests

- **WHEN** a browser session loads and uses the interface
- **THEN** every requested asset resolves to the local server

### Requirement: One active workspace session per process

A process SHALL allow at most one active workspace session. A second session SHALL NOT scan, read,
or modify the vault and SHALL explain that another session is active. The active session SHALL be
released when it disconnects.

#### Scenario: Second browser session is blocked

- **WHEN** a second browser session connects while a workspace session is active
- **THEN** it explains that another session is active and does not open the workspace

#### Scenario: Disconnect releases the session

- **WHEN** the active browser session disconnects
- **THEN** a new session can open the workspace

#### Scenario: Desktop window is unaffected

- **WHEN** the desktop presentation is running
- **THEN** the single window is the only session and no notice appears

### Requirement: Presentations share one workspace contract

The browser presentation SHALL provide the same inbox, browsing, editing, processing, projects, and
review behavior as the desktop window. The only permitted difference is a selection action that
requires a native dialog.

#### Scenario: Capture and processing work in a browser session

- **WHEN** the user captures a note and processes it in a browser session
- **THEN** the same files and frontmatter are written as in the desktop window

#### Scenario: Native dialog is the only divergent action

- **WHEN** an action requires a native directory dialog in a browser session
- **THEN** the vault selection action is the only action that behaves differently
