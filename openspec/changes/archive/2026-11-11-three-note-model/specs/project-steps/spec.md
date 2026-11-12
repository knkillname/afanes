# Spec Delta

## Purpose

Defines how a project describes its steps as Markdown checkboxes, how per-step metadata is written and preserved, and how completion, planning, ownership, and tags drive the workspace.

## ADDED Requirements

### Requirement: Steps are checkbox items in a project body

A project's steps SHALL be the task list items in its body. A task list item is a list item whose content begins with `[ ]` or `[x]`. Only notes with `type: project` contribute steps; checkboxes in any other note SHALL be ordinary Markdown.

#### Scenario: Checkbox becomes a step

- **WHEN** a project body contains `- [ ] Call the plumber`
- **THEN** the project has one open step with the text `Call the plumber`

#### Scenario: Checked item is complete

- **WHEN** a project body contains `- [x] Call the plumber`
- **THEN** the step is complete

#### Scenario: Reference checkboxes are inert

- **WHEN** a reference note contains `- [ ] Buy milk`
- **THEN** no step is produced

#### Scenario: No steps is valid

- **WHEN** a project body contains no task list item
- **THEN** the project parses and has no open steps

#### Scenario: Nested items are steps

- **WHEN** a project body contains a checked item with an unchecked child item
- **THEN** both are steps and both are listed, in document order

### Requirement: Step metadata is a trailing comment

Step metadata SHALL be a single HTML comment at the end of the task list item line. The comment content SHALL be a flow-style YAML mapping. If text follows the closing delimiter, the comment SHALL NOT be metadata. A step SHALL have at most one metadata comment.

#### Scenario: Trailing comment is metadata

- **WHEN** a step line ends with `<!-- {plan: 2026-11-20} -->`
- **THEN** the step has the plan date `2026-11-20`

#### Scenario: Text after the comment is prose

- **WHEN** a step line ends with `<!-- {plan: 2026-11-20} --> and more`
- **THEN** the comment is not treated as step metadata

#### Scenario: A comment without a mapping is prose

- **WHEN** a step line ends with `<!-- a note to self -->`
- **THEN** the step has no metadata

### Requirement: Step metadata schema

The metadata object SHALL accept the keys `owners`, `plan`, `actual`, and `tags`. `owners` SHALL be a list of names; `plan` and `actual` SHALL be ISO calendar dates; `tags` SHALL be a list of strings. Every key SHALL be optional.

#### Scenario: Owners are listed

- **WHEN** a step declares `owners: [Ada Lovelace]`
- **THEN** the step is waiting on `Ada Lovelace`

#### Scenario: Plan and actual are kept

- **WHEN** a step declares `plan: 2026-11-20` and `actual: 2026-11-14`
- **THEN** the step records both dates

#### Scenario: Tags are listed

- **WHEN** a step declares `tags: [errands, phone]`
- **THEN** the step carries both tags

#### Scenario: Empty object is valid

- **WHEN** a step declares `<!-- {} -->`
- **THEN** the step has no owners, dates, or tags

### Requirement: Owner names resolve as references

An owner name SHALL resolve against the same catalog as a `note:` reference. An owner that matches no note SHALL remain valid and SHALL be reported as unresolved.

#### Scenario: Owner resolves to a page

- **WHEN** a step declares `owners: [Ada]` and exactly one note is named `Ada`
- **THEN** the owner resolves to that note

#### Scenario: Unknown owner stays valid

- **WHEN** a step declares `owners: [Nobody]` and no note is named `Nobody`
- **THEN** the step keeps the owner and the owner is reported as unresolved

### Requirement: Step owners mean waiting

A step with no owner SHALL be work the user can do. A step with one or more owners SHALL be waiting on those owners and SHALL be excluded from the user's own step list.

#### Scenario: Ownerless step is mine

- **WHEN** a step has no `owners` key
- **THEN** it appears in the user's own step list

#### Scenario: Owned step is waiting

- **WHEN** a step declares `owners: [Ada]`
- **THEN** it appears under waiting and not in the user's own step list

#### Scenario: Multiple owners are allowed

- **WHEN** a step declares `owners: [Ada, Grace]`
- **THEN** the step is waiting on both

### Requirement: Step completion records the actual date

Ticking a step SHALL set `actual` to the current date. Unticking it SHALL remove `actual`. Completion MUST NOT change `plan`.

#### Scenario: Ticking records today

- **WHEN** the user ticks a step on 2026-11-14
- **THEN** the metadata includes `actual: 2026-11-14`

#### Scenario: Plan survives completion

- **WHEN** a step with `plan: 2026-11-20` is ticked on 2026-11-14
- **THEN** the metadata keeps `plan: 2026-11-20` and adds `actual: 2026-11-14`

#### Scenario: Unticking removes the actual date

- **WHEN** the user unticks a completed step
- **THEN** `actual` is removed and `plan` is kept

### Requirement: Tags filter steps

Tags SHALL be free-form labels used to filter the step list. They MUST NOT change ownership, dates, or completion.

#### Scenario: Tag filter shows matching steps

- **WHEN** the user filters by `errands`
- **THEN** only steps carrying that tag are shown

#### Scenario: Tags do not affect waiting

- **WHEN** an ownerless step carries `errands`
- **THEN** it remains in the user's own step list

### Requirement: Unknown metadata keys are preserved

A rewrite of a step's metadata SHALL preserve every key the application does not recognize. Known keys SHALL be updated and unknown keys SHALL be written back unchanged.

#### Scenario: Unknown key survives a tick

- **WHEN** a step declares `priority: high` and is ticked
- **THEN** `priority: high` remains in the rewritten comment

### Requirement: Malformed metadata is partly applied

When a metadata comment is not a valid mapping or a known key has an invalid value, the application SHALL apply the valid keys, ignore the invalid ones, keep the note readable, and report the affected line. It MUST NOT rewrite the comment until the user edits it.

#### Scenario: Invalid date is ignored

- **WHEN** a step declares `plan: 2026-13-40`
- **THEN** the step has no plan date and the note reports the line

#### Scenario: Unknown key does not block

- **WHEN** a step declares `priority: high`
- **THEN** the step remains readable and the key is preserved

#### Scenario: Broken YAML keeps the note readable

- **WHEN** a metadata comment is not valid YAML
- **THEN** the step has no metadata, the note remains readable, and the line is reported
