# Spec Delta

## ADDED Requirements

### Requirement: Step plan and owners are editable from the page

A step SHALL accept a plan date and an owner list from the page. Setting or clearing a plan SHALL change only `plan`. Adding or removing an owner SHALL change only `owners`. Every edit SHALL rewrite one step line atomically, SHALL preserve `actual`, tags, and unknown metadata keys, and SHALL reject an invalid date.

#### Scenario: A plan date is added

- **WHEN** a step with no plan is given `2026-11-20`
- **THEN** its metadata includes `plan: 2026-11-20`

#### Scenario: A plan date is replaced

- **WHEN** a step with `plan: 2026-11-20` is given `2026-12-01`
- **THEN** its metadata contains `plan: 2026-12-01` and no other plan date

#### Scenario: A plan date is cleared

- **WHEN** a step with a plan date clears it
- **THEN** the `plan` key is removed and every other key is kept

#### Scenario: An owner is added

- **WHEN** `Ada` is added to an ownerless step
- **THEN** the metadata contains `owners: [Ada]`

#### Scenario: An owner is removed

- **WHEN** `Ada` is removed from `owners: [Ada, Grace]`
- **THEN** the metadata contains `owners: [Grace]`

#### Scenario: The last owner is removed

- **WHEN** the last owner is removed from a step
- **THEN** the `owners` key is removed and the step becomes ownerless

#### Scenario: Completion and tags survive an owner edit

- **WHEN** a completed step with tags gains an owner
- **THEN** `actual` and `tags` keep their previous values

#### Scenario: Unknown metadata survives an edit

- **WHEN** a step declares `priority: high` and its plan or owners change
- **THEN** `priority: high` remains in the rewritten comment

#### Scenario: An invalid date is rejected

- **WHEN** a plan date is not a valid calendar date
- **THEN** no file is written and the step keeps its previous metadata

### Requirement: A step metadata edit rewrites only its line

A page step edit SHALL rewrite only the affected task list item line and SHALL leave every other body line and every frontmatter byte unchanged.

#### Scenario: Other steps are untouched

- **WHEN** one step's plan or owners change
- **THEN** every other step line keeps its original bytes

#### Scenario: Failure leaves the file unchanged

- **WHEN** a step metadata write fails
- **THEN** the file's content and modification time are unchanged
