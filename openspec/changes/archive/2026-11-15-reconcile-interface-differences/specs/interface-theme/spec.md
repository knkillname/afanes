# Spec Delta

## MODIFIED Requirements

### Requirement: Differences from the reference language are bounded

Afanes SHALL conform to the reference language except where the Flet toolkit cannot express a
guideline mechanism. The interface standard's bounded-differences table SHALL be the single list of
those differences. The platform typeface is guideline-required, not a difference. Each difference
MUST be recorded in that table, and removing one SHALL require its own change.

#### Scenario: A new difference requires a spec change

- **WHEN** a change proposes a visual behavior outside the reference language
- **THEN** it records the difference in the interface standard's table and updates the affected
  requirements rather than adding it silently

#### Scenario: The recorded list matches the implementation

- **WHEN** the interface standard's table is compared with the application
- **THEN** every declared toolkit limitation appears in the table, and the table contains no
  difference the application does not ship

#### Scenario: The platform typeface is not a difference

- **WHEN** the differences are listed
- **THEN** the platform typeface is described as the guideline-required choice rather than as a
  deviation

#### Scenario: The limiting toolkit is named

- **WHEN** a toolkit limitation is documented
- **THEN** it names the Flet API that is missing rather than a broader framework

#### Scenario: The title bar stays native

- **WHEN** the application runs on a desktop platform
- **THEN** the operating-system title bar is used as provided and the workspace toolbar is the
  in-window equivalent of the reference header bar
