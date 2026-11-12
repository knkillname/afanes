# Spec Delta

## MODIFIED Requirements

### Requirement: The browser reflects vault changes

After a capture, processing apply, page save, rename, trash, or explicit refresh, and after an edit made outside the application, the browser SHALL reflect the resulting vault state from the latest scan. An external change SHALL be reflected without a manual refresh.

#### Scenario: Processing moves the entry

- **WHEN** a capture is processed into a project
- **THEN** it disappears from Inbox and appears under Projects

#### Scenario: Rename updates the entry

- **WHEN** a page is renamed
- **THEN** the browser shows the new identity and title

#### Scenario: Trash removes the entry

- **WHEN** a page is moved to trash
- **THEN** it disappears from the browser

#### Scenario: An external creation appears

- **WHEN** a note is created outside the application
- **THEN** it appears in the browser without the user asking for a refresh

#### Scenario: An external edit updates the row

- **WHEN** a project file changes outside the application
- **THEN** its row shows the new open-step count and next step

#### Scenario: An external trash removes the entry

- **WHEN** a note is moved under `trash/` outside the application
- **THEN** it disappears from the browser without the user asking for a refresh

## ADDED Requirements

### Requirement: A background refresh does not interrupt work

A refresh triggered by an external change SHALL be read-only. It MUST NOT write a note file, clear a message the user can see, discard an open draft, or end a processing or review flow, and it SHALL stop when no vault is open.

#### Scenario: A visible message survives

- **WHEN** a background refresh completes while a message from a user command is shown
- **THEN** the message remains visible

#### Scenario: An open draft survives

- **WHEN** a background refresh detects a change while a page draft is open
- **THEN** the draft text and its labels are unchanged

#### Scenario: A focused flow keeps its note

- **WHEN** a background refresh runs during processing or review
- **THEN** the flow remains on the same note

#### Scenario: Background work writes nothing

- **WHEN** a background refresh runs
- **THEN** no note file is created, changed, or removed

#### Scenario: No vault means no scanning

- **WHEN** no vault is open, or the vault was closed
- **THEN** no scan runs in the background
