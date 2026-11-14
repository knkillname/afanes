# Spec Delta

## ADDED Requirements

### Requirement: The Log date controls share one row

The Log section SHALL place **Today's Entry**, **Entries**, and **Everything** in one control row above the calendar. The controls SHALL use natural widths and SHALL wrap only when the browser cannot fit them in one row.

#### Scenario: Controls share a wide row

- **WHEN** the Log browser is wide enough for all three date controls
- **THEN** Today's Entry, Entries, and Everything appear in one row above the calendar

#### Scenario: Narrow browser wraps the controls

- **WHEN** the browser cannot fit the three date controls in one row
- **THEN** the controls wrap onto additional rows without horizontal scrolling

#### Scenario: Search hides the controls

- **WHEN** a non-empty search query is active
- **THEN** the Log date controls are not shown
