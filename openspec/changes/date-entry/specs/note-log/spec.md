# Spec Delta

## MODIFIED Requirements

### Requirement: Log entries are not renamed directly

The page for a log entry SHALL NOT offer the Rename action. Its date SHALL be changed through the
Date field, which performs the rename and move. The Date field SHALL offer the shared
precision-aware calendar action. The entry's level-1 heading SHALL be updated only when it equals
the generated date title for its old date, as defined by `note-identity`.

#### Scenario: Rename is absent

- **WHEN** a log entry is open
- **THEN** the page offers no Rename action

#### Scenario: A date change keeps the heading

- **WHEN** a log entry titled `A quiet Tuesday` is changed from `2025-10-12` to `2025-10-13`
- **THEN** the heading remains `A quiet Tuesday`

#### Scenario: Trash remains available

- **WHEN** a log entry is open
- **THEN** the page still offers the Trash action

#### Scenario: The Date field offers the precision-aware picker

- **WHEN** a log entry is edited
- **THEN** the Date field embeds the calendar action and the shared picker offers day, month, and
  year precision

#### Scenario: A month selection renames and moves the entry

- **WHEN** the user confirms a month value such as `2025-10` from the Date picker
- **THEN** the entry's `date` becomes `2025-10`, the file moves to `log/2025/`, and the heading
  follows the generated month title only when it still matches the old generated title

#### Scenario: A year selection renames and moves the entry

- **WHEN** the user confirms a year value such as `2025` from the Date picker
- **THEN** the entry's `date` becomes `2025`, the file moves to `log/2025/`, and the heading follows
  the generated year title only when it still matches the old generated title

#### Scenario: A custom heading survives a coarse date change

- **WHEN** a log entry with a custom heading changes to a month or year value
- **THEN** the custom heading is preserved

#### Scenario: Typed ISO remains valid

- **WHEN** the user types a valid day, month, or year value into the Date field
- **THEN** the same validation, rename, and move path runs without opening the picker
