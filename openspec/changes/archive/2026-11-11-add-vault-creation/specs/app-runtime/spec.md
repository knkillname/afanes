# Spec Delta

## MODIFIED Requirements

### Requirement: An installed launch command starts the application

Installing the package SHALL provide an `afanes` console command that starts the same application as
`python -m afanes`, accepts the same options, keeps the desktop presentation as the default, and
dispatches a recognized subcommand to the headless command surface instead of starting the
interface.

#### Scenario: Console command starts the default presentation

- **WHEN** a user runs `afanes` with no options and the desktop runtime is available
- **THEN** the interface opens in a desktop window

#### Scenario: Console command accepts launch options

- **WHEN** a user runs `afanes --web` or passes `--vault` or `--port`
- **THEN** the command applies the same presentation, vault, and port behavior as `python -m afanes`

#### Scenario: Console command dispatches a subcommand

- **WHEN** a user runs `afanes` with a recognized subcommand
- **THEN** the subcommand runs headlessly and no interface starts

#### Scenario: Module form keeps working

- **WHEN** a user runs `python -m afanes` after installing the package
- **THEN** the application starts with the same behavior as the console command
