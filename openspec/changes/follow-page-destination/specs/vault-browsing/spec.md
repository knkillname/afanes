# Spec Delta

## ADDED Requirements

### Requirement: Page navigation selects the note's browser destination

Opening a page through a body link, role name, connection entry, ambiguous-reference candidate, search result, Back, or a reference created from a missing role name SHALL select the browser destination that owns the note. The browser SHALL show that destination's normal content while the page remains open in the detail region. Selecting a destination in the navigation SHALL keep the open page. A note the scan could not parse SHALL leave the destination unchanged.

#### Scenario: A role name opens a reference

- **WHEN** a project is open under Projects and the reader selects an owner name that resolves to a reference
- **THEN** References becomes the active destination, the browser lists references, and the reference page is open

#### Scenario: A body link opens a project

- **WHEN** a reference page is open under References and the reader follows a body link that resolves to a project
- **THEN** Projects becomes the active destination, the browser lists projects, and the project page is open

#### Scenario: A connection entry opens its destination

- **WHEN** the reader selects a connection entry for a note in another destination
- **THEN** that note's destination becomes active and the note opens

#### Scenario: An ambiguous reference choice opens its destination

- **WHEN** the reader chooses one candidate from an ambiguous reference
- **THEN** the chosen note's destination becomes active and the note opens

#### Scenario: Back restores the previous destination

- **WHEN** the reader opens a reference from a project and then chooses Back
- **THEN** the project page returns and Projects becomes the active destination

#### Scenario: A search result leaves search

- **WHEN** a search query is active and the reader selects a result under References
- **THEN** the query clears, References becomes the active destination, and the reference page is open

#### Scenario: A manual destination keeps the page

- **WHEN** a reference page is open and the reader selects Projects in the navigation
- **THEN** Projects becomes the active destination, the browser lists projects, and the reference page remains open

#### Scenario: A trashed page selects Trash

- **WHEN** the reader opens a managed trashed note from search
- **THEN** Trash becomes the active destination and the note opens read-only

#### Scenario: An unreadable note keeps the destination

- **WHEN** the reader opens a note the scan could not parse
- **THEN** the active destination stays unchanged and the file opens in raw rescue mode

#### Scenario: A created role reference selects References

- **WHEN** the reader confirms the missing-role-name flow for a project role
- **THEN** References becomes the active destination and the new reference opens in edit mode
