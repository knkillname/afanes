# Spec Delta

## MODIFIED Requirements

### Requirement: The browser groups every parsed note

The browser SHALL expose every parsed note under Inbox, Projects, References, Log, Needs attention,
or Unreadable notes. A note SHALL appear in exactly one group in normal browsing: log notes under
Log, and every other note under its type group. References SHALL be grouped by their category label.
Captures under `inbox/` SHALL appear only under Inbox, and notes under `trash/` SHALL NOT appear. The
Log's Everything mode SHALL be an additional date lens that may show a note alongside its type group.

#### Scenario: Project appears under Projects

- **WHEN** the vault contains a parsed `type: project` note
- **THEN** the browser lists it under Projects

#### Scenario: A person reference groups by its label

- **WHEN** the vault contains a reference with `category: person`
- **THEN** the browser groups it under the `person` label

#### Scenario: Categorized references group by label

- **WHEN** the vault contains references with `category: person` and `category: place`
- **THEN** the browser groups each under its own label

#### Scenario: Uncategorized reference appears under References

- **WHEN** the vault contains a reference with no category
- **THEN** the browser lists it under References

#### Scenario: Capture appears only under Inbox

- **WHEN** a note is under `inbox/`
- **THEN** it appears under Inbox and in no other group

#### Scenario: Misplaced note needs attention

- **WHEN** a parsed `type: note` exists outside `inbox/`
- **THEN** the browser lists it under Needs attention

#### Scenario: Trashed note is absent

- **WHEN** a note is under `trash/`
- **THEN** it appears in no browser group

#### Scenario: Inbox capture becomes a project

- **WHEN** a capture is processed into a project
- **THEN** it leaves the Inbox group and appears under Projects

#### Scenario: A log entry appears under Log

- **WHEN** the vault contains a parsed `type: log` note
- **THEN** the browser lists it under Log and in no other type group

#### Scenario: A log entry is not a reference

- **WHEN** the vault contains a log entry and a reference with the same name
- **THEN** the Log lists the log entry and References lists only the reference

#### Scenario: Everything is a lens

- **WHEN** the Log is in Everything mode and the vault contains a project
- **THEN** the project appears under Projects and in the Log date lens

#### Scenario: Entries is not a lens

- **WHEN** the Log is in Entries mode and the vault contains a project
- **THEN** the project appears only under Projects
