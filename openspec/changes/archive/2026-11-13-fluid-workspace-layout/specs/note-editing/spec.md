# Spec Delta

## ADDED Requirements

### Requirement: The label form flows and fills the page pane

Edit mode SHALL lay out every visible label control, including the **Starter** control of a new log draft, in one adaptive flow. Visible controls SHALL share the available row width and grow to fill it. Controls SHALL wrap onto another row only when the pane cannot fit their minimum widths, without horizontal scrolling. The body field SHALL fill the remaining width and height below the label flow.

#### Scenario: Wide pane shares one row

- **WHEN** a new log draft is edited on a pane wide enough for three controls
- **THEN** Type, Date, and Starter share one row and grow to fill its width

#### Scenario: Starter keeps its guidance

- **WHEN** a new log draft shows the Starter control in the label flow
- **THEN** the selected card description and any invalid-card warning appear below the label flow

#### Scenario: Project labels share rows

- **WHEN** a project with every workflow label visible is edited on a wide pane
- **THEN** the visible label controls flow across the available rows and fill each row without fixed field widths

#### Scenario: Narrow pane wraps the flow

- **WHEN** the page pane cannot fit the visible label controls at their minimum widths
- **THEN** the remaining controls wrap onto another row without horizontal scrolling

#### Scenario: Body fills the detail width

- **WHEN** the edit form is shown in a detail card wider than the label minimums
- **THEN** the body field spans the full form width and extends to the bottom of the available pane
