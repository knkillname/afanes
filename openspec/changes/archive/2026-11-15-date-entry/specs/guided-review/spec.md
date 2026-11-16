# Spec Delta

## MODIFIED Requirements

### Requirement: A due step can be done, postponed, or delegated

Each due or overdue own step SHALL offer do it now, postpone, delegate, open project, and skip. Do it now SHALL check the step and record the actual date. Postpone SHALL replace or add the plan date. The postpone form SHALL offer the shared day-only date picker. Delegate SHALL add an owner and move the step to waiting.

#### Scenario: Do it now checks the step

- **WHEN** the user chooses do it now for a due step
- **THEN** the step is checked and its metadata records the current date as `actual`

#### Scenario: Postpone changes the plan

- **WHEN** the user postpones a due step to a later date
- **THEN** the step's `plan` becomes the new date and `actual` is absent

#### Scenario: Delegate moves the step to waiting

- **WHEN** the user delegates a due step to a person
- **THEN** the step's `owners` gains that name and the step leaves the user's own list

#### Scenario: Open project keeps the session

- **WHEN** the user chooses open project for a step
- **THEN** the project page opens and the session position is unchanged

#### Scenario: Skip changes nothing

- **WHEN** the user skips a due step
- **THEN** the step is unchanged

#### Scenario: The postpone form offers the day-only picker

- **WHEN** the user opens the postpone form
- **THEN** the plan date field embeds the calendar action and the shared picker offers day precision
  only

#### Scenario: A picked postpone date fills the form

- **WHEN** the user confirms a day from the postpone picker
- **THEN** the plan date field receives that ISO day and the user can submit the form

#### Scenario: A typed postpone date remains valid

- **WHEN** the user types a valid ISO day into the postpone form
- **THEN** the existing validation and submit path runs without opening the picker

#### Scenario: Cancelling the postpone picker writes nothing

- **WHEN** the user cancels the postpone picker
- **THEN** the plan date field and the step are unchanged
