# Spec Delta

## ADDED Requirements

### Requirement: The Log calendar is keyboard accessible

The Log calendar SHALL place focus on a day cell and support the same day-view keys as the date
picker: arrows move by day or week, Page Up/Page Down move by month, Home/End move to the week
bounds, and Enter activates the focused day exactly like a pointer click. Tab SHALL leave the grid
without being trapped, and the visible month SHALL follow a move across a month boundary.

#### Scenario: Arrows move by day and week

- **WHEN** a day cell has focus and the user presses an arrow key
- **THEN** focus moves one day horizontally or one week vertically

#### Scenario: Page keys move by month

- **WHEN** a day cell has focus and the user presses Page Up or Page Down
- **THEN** the visible month changes and focus moves to the corresponding day in that month

#### Scenario: Home and End reach the week bounds

- **WHEN** a day cell has focus and the user presses Home or End
- **THEN** focus moves to the first or last day of the visible week

#### Scenario: Enter activates the focused day

- **WHEN** a day cell has focus and the user presses Enter
- **THEN** the day follows the same open, draft, or expand behavior as a pointer click

#### Scenario: Focus follows a month change

- **WHEN** a keyboard move crosses a month boundary
- **THEN** the calendar renders that month and focus remains on the selected day

#### Scenario: Tab leaves the grid

- **WHEN** the user presses Tab while a day cell has focus
- **THEN** focus leaves the calendar without being trapped

#### Scenario: The focus ring stays visible

- **WHEN** a day cell has keyboard focus
- **THEN** the accent focus ring marks that cell and is not hidden by selection or today marks
