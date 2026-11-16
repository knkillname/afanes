# Spec Delta

## ADDED Requirements

### Requirement: The date picker dialog is a recorded difference

The date picker SHALL be a dialog because Flet exposes no anchored popover or anchor geometry. The
difference SHALL be recorded in the interface standard and removed only by a change that provides an
anchored picker. The dialog SHALL still follow the focus, Esc, and action-order rules.

#### Scenario: The difference is recorded

- **WHEN** the interface standard lists the bounded differences
- **THEN** it includes the date-picker dialog that stands in for an anchored calendar popover

#### Scenario: The missing API is named

- **WHEN** the date-picker difference is documented
- **THEN** it names Flet's missing anchored popover and anchor geometry rather than a broader
  framework

#### Scenario: The dialog still follows the reference rules

- **WHEN** the date picker opens
- **THEN** initial focus reaches the selected cell, Esc cancels, and Cancel appears before Select

#### Scenario: Removing the difference takes a change

- **WHEN** a future change anchors the picker to its field
- **THEN** that change updates the interface standard and this requirement
