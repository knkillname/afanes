# Spec Delta

## ADDED Requirements

### Requirement: The browser searches titles, identities, and bodies

The browser SHALL provide a search field that filters entries by display title, identity, prose body text, and step text. Matching SHALL ignore case, Unicode form, and repeated whitespace. Step metadata comments SHALL NOT be searched.

#### Scenario: Title match is listed

- **WHEN** the user types part of a page's display title
- **THEN** that page is listed

#### Scenario: Identity match is listed

- **WHEN** the user types part of a page's identity
- **THEN** that page is listed

#### Scenario: Body match is listed

- **WHEN** a search term appears only in a note's prose body
- **THEN** that note is listed

#### Scenario: Step text match names the project

- **WHEN** a search term appears in a step
- **THEN** the project is listed and the matching step is shown with its project

#### Scenario: Metadata is not searched

- **WHEN** a term appears only inside a step's metadata comment
- **THEN** no result is produced for that term

#### Scenario: Matching ignores case and repeated whitespace

- **WHEN** the user types `ada` or `Ada,   Countess of Lovelace`
- **THEN** the matching page is listed

### Requirement: The browser groups every parsed note

The browser SHALL expose every parsed note under Inbox, Projects, References, Needs attention, or Unreadable notes. A note SHALL appear in exactly one group. References SHALL be grouped by their category label. Captures under `inbox/` SHALL appear only under Inbox, and notes under `trash/` SHALL NOT appear.

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

## REMOVED Requirements

### Requirement: The browser searches titles and identities

**Reason**: Search now covers bodies and steps, not only titles and identities.

**Migration**: None. The same search field returns a larger result set.

### Requirement: The browser groups every parsed note by type

**Reason**: Actions, People, and Notes sections no longer exist, and references group by free-form label. It is restated under the new grouping requirement.

**Migration**: None. Notes appear under their new group.
