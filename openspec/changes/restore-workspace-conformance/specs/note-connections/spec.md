# Spec Delta

## MODIFIED Requirements

### Requirement: Connections are ordered by relationship

The Connections section SHALL present `Linked from`, `Owned projects`, `Owned steps`, and
`Requested projects` in that order. A section SHALL be omitted when it has no visible item. The
completed views SHALL NOT change the section order.

#### Scenario: All sections are ordered

- **WHEN** a page has every kind of connection
- **THEN** the sections appear in the fixed order

#### Scenario: An empty section is omitted

- **WHEN** a page has no owned steps
- **THEN** the Owned steps section is absent

#### Scenario: An empty section does not reorder the others

- **WHEN** a page has no owned steps
- **THEN** the remaining sections keep their relative order

#### Scenario: A hidden-only section is omitted

- **WHEN** a page has a finished project and no visible owned project
- **THEN** the Owned projects section is absent until the finished-project view is enabled

#### Scenario: Toggling completed items does not reorder sections

- **WHEN** the reader enables or hides a completed view
- **THEN** the section order is unchanged

### Requirement: Completed connections are opt-in

The completed view SHALL be presented separately for `Owned steps` and for finished projects. The
finished-project view SHALL reveal both finished owned projects and finished requested projects. Both
views SHALL start hidden when a page opens, and each SHALL reveal only its own completed or finished
items. The reveal controls SHALL remain available when a view has only hidden items. Changing the open
page SHALL return both views to hidden.

#### Scenario: Both views start hidden

- **WHEN** a page with completed steps and finished projects opens
- **THEN** neither completed item is visible

#### Scenario: Each view is independent

- **WHEN** the reader enables the completed view for steps
- **THEN** finished projects remain hidden

#### Scenario: The finished-project view covers both roles

- **WHEN** the reader enables the finished-project view
- **THEN** both finished owned projects and finished requested projects are revealed

#### Scenario: A hidden-only view stays available

- **WHEN** a page's only finished item is a finished owned project
- **THEN** the finished-project view control is available and enabling it shows the project

#### Scenario: A new page resets the views

- **WHEN** the reader opens another page
- **THEN** both completed views are hidden again
