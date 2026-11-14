# Spec Delta

## ADDED Requirements

### Requirement: Command-line copy follows the active locale

Help, success reports, usage errors, and operational failures SHALL use the same locale resolution
as the interface. The template listing SHALL report localized labels and descriptions. A headless
command MUST NOT import the interface, open a display, or write a file to resolve the locale.

#### Scenario: Spanish help is reported

- **WHEN** a headless command runs with `--help` under Spanish
- **THEN** its help text is Spanish

#### Scenario: A Spanish success report is printed

- **WHEN** a vault is created under Spanish
- **THEN** standard output names the path, folders, settings file, template, notes, and remembered status in Spanish

#### Scenario: A Spanish usage error is printed

- **WHEN** a headless command receives invalid arguments under Spanish
- **THEN** standard error carries the Spanish usage error and the command exits `2`

#### Scenario: A Spanish operational failure is printed

- **WHEN** a headless command fails for an expected reason under Spanish
- **THEN** standard error carries one Spanish message and the command exits `1`

#### Scenario: The template listing is localized

- **WHEN** the template catalog is listed under Spanish
- **THEN** labels and descriptions are Spanish and the identifiers `personal`, `work`, and `study` are unchanged

#### Scenario: No display or interface import is needed

- **WHEN** a headless command resolves its locale
- **THEN** no interface module is imported and no display server is required

#### Scenario: Resolution stays offline

- **WHEN** a headless command resolves its locale
- **THEN** no network request is made

#### Scenario: Exit codes do not depend on locale

- **WHEN** the same command succeeds or fails under either locale
- **THEN** its exit status is the same as under the other locale
