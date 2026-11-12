# Spec Delta

## ADDED Requirements

### Requirement: The workspace stays interactive across refreshes

After any workspace refresh — a section switch, search, explicit refresh, page command, processing or review update, or
background scan — every sidebar entry, count, search field, action, and the main area SHALL remain usable. A refresh
MUST NOT raise a control-lifecycle error or leave the workspace partially updated.

#### Scenario: A section switch follows startup

- **WHEN** the workspace has rendered and the reader selects another browser section
- **THEN** the active entry and its accent edge update and no error is shown

#### Scenario: A section switch follows a background scan

- **WHEN** a background refresh has applied a changed scan
- **THEN** selecting another section still updates the sidebar

#### Scenario: An immutable section entry is recovered

- **WHEN** the presentation toolkit has marked a sidebar entry as immutable
- **THEN** the next refresh restores the entry's usability and the reader can switch sections

#### Scenario: Refreshing controls writes nothing

- **WHEN** the workspace refreshes its controls
- **THEN** no note file is created, changed, moved, or removed
