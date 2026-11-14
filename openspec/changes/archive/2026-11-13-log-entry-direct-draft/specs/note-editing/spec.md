# Spec Delta

## MODIFIED Requirements

### Requirement: A new page is written on first content

A new page draft SHALL NOT be written to the vault until it has body or label content. A draft
opened from a reference SHALL use the sanitized reference name as its identity; a log draft SHALL use
its ISO date. The first write SHALL use that exact identity or fail with an explanation, and an
untouched draft SHALL leave the vault unchanged.

#### Scenario: Untouched draft is discarded

- **WHEN** the user leaves a new draft without changing its body or labels
- **THEN** no file is created and no reference is rewritten

#### Scenario: First content writes the page

- **WHEN** the user types body text or changes a label in a new draft
- **THEN** the page is created on the next autosave or commit using the exact identity

#### Scenario: Exact identity is available

- **WHEN** the sanitized identity would collide with an existing file
- **THEN** the first write stops with an explanation and creates no suffixed name

#### Scenario: An untouched log draft writes nothing

- **WHEN** the user opens a log draft and leaves without changing its body or labels
- **THEN** no log file is created

#### Scenario: A log draft writes at its date

- **WHEN** the user types body text in a log draft dated `2025-10-12`
- **THEN** the file is written at `log/2025/10/2025-10-12.md`

#### Scenario: A starter selection is content

- **WHEN** the user chooses a starter card in a new log draft and changes nothing else
- **THEN** the next autosave or commit writes the entry with the starter body

#### Scenario: An occupied date refuses the first log write

- **WHEN** the log date becomes occupied before the draft's first write
- **THEN** no file is written, the draft remains, and the collision is reported
