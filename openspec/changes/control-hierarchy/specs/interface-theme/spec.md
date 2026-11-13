# Spec Delta

## ADDED Requirements

### Requirement: Unavailable actions are insensitive

An action whose current input cannot succeed SHALL be insensitive. Its availability SHALL update as
the input changes. A command SHALL still validate its input when called directly and MUST NOT write
on invalid input.

#### Scenario: Blank capture disables the action

- **WHEN** the composer is empty or contains only whitespace
- **THEN** the Capture action is insensitive

#### Scenario: Blank required text disables the action

- **WHEN** a name, step, or other required text field is empty or contains only whitespace
- **THEN** the Create, Rename, and Add Step actions that depend on it are insensitive

#### Scenario: Missing outcome disables preview

- **WHEN** no processing outcome is selected, or a required project or date is missing or invalid
- **THEN** the Preview action is insensitive

#### Scenario: Valid input enables the action

- **WHEN** the input becomes valid
- **THEN** the action becomes sensitive without another command

#### Scenario: A direct invalid call still writes nothing

- **WHEN** an invalid value reaches a command without passing through the interface
- **THEN** the command rejects it, writes nothing, and reports the problem

### Requirement: Confirmations put Cancel first

A confirmation surface SHALL place Cancel before the affirmative action in reading order. The
affirmative action SHALL name the operation. Cancel MUST leave the note and the vault unchanged.

#### Scenario: A trash confirmation puts Cancel first

- **WHEN** the page offers moving a note to trash
- **THEN** Cancel appears before the affirmative action

#### Scenario: A type change puts Cancel first

- **WHEN** the page offers changing a note's type
- **THEN** Cancel appears before the affirmative action

#### Scenario: A category move puts Cancel first

- **WHEN** the page offers moving a note to a category folder
- **THEN** Cancel appears before the affirmative action

#### Scenario: A rename puts Cancel first

- **WHEN** the page offers renaming a note
- **THEN** Cancel appears before the affirmative action

#### Scenario: Cancel changes nothing

- **WHEN** the user cancels any confirmation
- **THEN** no note is written, renamed, moved, or removed

### Requirement: List rows use the standard height

List rows SHALL use the standard list-row height and vertical padding. A row MUST NOT shrink below
that height to fit more content.

#### Scenario: Project rows keep the standard height

- **WHEN** the Projects list renders
- **THEN** every row uses the standard list-row height

#### Scenario: Log rows keep the standard height

- **WHEN** the Log tree renders
- **THEN** every row uses the standard list-row height

#### Scenario: Picker rows keep the standard height

- **WHEN** a template or outcome picker renders
- **THEN** every row uses the standard list-row height

#### Scenario: A dense row is not offered

- **WHEN** a list row is added
- **THEN** it does not reduce its height to fit more rows

## MODIFIED Requirements

### Requirement: A view has at most one suggested or destructive action

A rendered view SHALL show at most one control using either the suggested style (accent-filled) or
the destructive style at the same time. A dialog or a transient panel is its own surface and is
counted with that surface, not with the view behind it. Views enumerated in the conformance baseline
are tracked exceptions until they are migrated, and a new or modified view MUST conform.

#### Scenario: A new view conforms

- **WHEN** a view is added
- **THEN** it contains no more than one suggested-or-destructive-style control

#### Scenario: A view does not combine both styles

- **WHEN** a view shows a suggested action
- **THEN** it does not also show a destructive action in the same view

#### Scenario: A dialog is measured on its own

- **WHEN** a dialog opens over a view that already shows a suggested action
- **THEN** the dialog and the view behind it are counted as separate surfaces

#### Scenario: An existing exception is tracked

- **WHEN** an unmigrated view exceeds the limit
- **THEN** its file is listed in the conformance baseline and the gate passes

### Requirement: Buttons carry an icon or a label, not both

Outside a header bar, a sidebar, or a view switcher, a button SHALL contain either an icon or a
label. A header bar button MAY combine an icon and a label. Views enumerated in the conformance
baseline are tracked exceptions until they are migrated, and a new or modified view MUST conform.

#### Scenario: A new button chooses one

- **WHEN** a button outside a header bar, sidebar, or view switcher is added
- **THEN** it shows either an icon or a label, not both

#### Scenario: The sidebar exception is allowed

- **WHEN** a sidebar row shows an icon and a label
- **THEN** the combination is allowed

#### Scenario: A header action combines both

- **WHEN** a header bar shows an action with an icon and a label
- **THEN** the combination is allowed

#### Scenario: A dialog action chooses one

- **WHEN** a dialog shows a button
- **THEN** it shows either an icon or a label, not both

#### Scenario: An existing exception is tracked

- **WHEN** an unmigrated button shows both
- **THEN** its file is listed in the conformance baseline and the gate passes
