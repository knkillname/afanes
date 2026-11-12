# Spec Delta

## ADDED Requirements

### Requirement: Review step text is rendered Markdown

Every step text shown in a review card SHALL be rendered as inline Markdown. This includes the due or
waiting step card, the project card's next step, and the project card's other open steps. Raw Markdown
source MUST NOT appear in the card. Metadata comments remain hidden.

#### Scenario: A link in a due step card is rendered

- **WHEN** a due step's text contains `[Incident notes](<note:Incident notes>)`
- **THEN** the card shows `Incident notes` and not the raw destination syntax

#### Scenario: Emphasis in a due step card is rendered

- **WHEN** a due step's text contains `**Bold** step`
- **THEN** the card shows `Bold step` with emphasis and not the asterisks

#### Scenario: A waiting step card is rendered

- **WHEN** a waiting step's text contains Markdown
- **THEN** the card renders it with the same rule

#### Scenario: A project card's next step is rendered

- **WHEN** a project card's next step contains a link or emphasis
- **THEN** the next-step line renders it and does not show raw syntax

#### Scenario: Other open steps are rendered

- **WHEN** a project card lists other open steps with Markdown
- **THEN** each line renders its Markdown

#### Scenario: Showing a card writes nothing

- **WHEN** a review card is shown
- **THEN** no project or step file changes

#### Scenario: Summary links do not navigate

- **WHEN** a step link in a review card is tapped
- **THEN** the card remains on the current review item and opening the project remains an explicit action
