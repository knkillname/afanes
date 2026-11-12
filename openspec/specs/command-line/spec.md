# command-line Specification

## Purpose

Defines the installed command surface: how it separates a graphical launch from headless
subcommands, and the exit codes, output streams, and display-free guarantees every command holds.

## Requirements

### Requirement: The installed command dispatches headless subcommands

The `afanes` command SHALL start the interface when its first argument is not a recognized
subcommand, and SHALL run the named subcommand without starting the interface. A subcommand MUST NOT
import the graphical toolkit, open a window, or require a display server. A first argument that is
neither a recognized subcommand nor a recognized launch option SHALL be reported as a usage error.

#### Scenario: No subcommand starts the interface

- **WHEN** a user runs `afanes` with no arguments or with only launch options
- **THEN** the interface starts with the presentation those options select

#### Scenario: Recognized subcommand runs without the interface

- **WHEN** a user runs `afanes` with a recognized subcommand
- **THEN** the subcommand runs and no window or browser session opens

#### Scenario: Unknown argument is a usage error

- **WHEN** a user runs `afanes` with an argument that is neither a subcommand nor a launch option
- **THEN** the command reports the usage error and exits without starting the interface

#### Scenario: Launch options keep their meaning

- **WHEN** a user runs `afanes --web`, `afanes --vault DIR`, or `afanes --port N`
- **THEN** the option behaves exactly as it does without subcommand dispatch

### Requirement: A vault can be created from the command line

`afanes vault create DIR` SHALL create and seed a vault at the given path, report the created vault,
any parent folders it created, the seeded folders, and whether the vault was remembered, then exit
with status `0`. It SHALL remember the created vault unless `--no-remember` is supplied. A rejected
path MUST leave the filesystem and the preferences unchanged.

#### Scenario: Missing path is created

- **WHEN** a user creates a vault at a path that does not exist
- **THEN** the directory is created, the default folders are seeded, and the command exits `0`

#### Scenario: Empty directory is seeded

- **WHEN** a user creates a vault at an existing empty directory
- **THEN** that directory is seeded and the command exits `0`

#### Scenario: Success output names what was created

- **WHEN** creation succeeds
- **THEN** standard output names the vault path, any parent folders created, the seeded folders, and
  whether the vault was remembered

#### Scenario: Existing non-empty directory is refused

- **WHEN** a user creates a vault at a directory that already contains entries
- **THEN** the command reports that the path is not empty, creates nothing, and exits `1`

#### Scenario: File path is refused

- **WHEN** the path names an existing file
- **THEN** the command reports that a vault must be a directory and exits `1`

#### Scenario: Missing intermediate folders are created

- **WHEN** the path contains intermediate folders that do not exist
- **THEN** those folders and the vault are created, every created directory is reported, and the
  command exits `0`

#### Scenario: Created vault is remembered by default

- **WHEN** a user creates a vault without `--no-remember`
- **THEN** the next launch opens that vault as the remembered one

#### Scenario: no-remember leaves preferences unchanged

- **WHEN** a user creates a vault with `--no-remember`
- **THEN** the preferences file still names the previously remembered vault

#### Scenario: Created vault cannot be remembered

- **WHEN** the vault is created but the preferences file cannot be written
- **THEN** the command reports that the vault was created but not remembered and exits `1`

### Requirement: Headless failures are reported without a traceback

A headless command SHALL write expected operational failures to standard error and exit with
status `1`, SHALL write usage errors to standard error and exit with status `2`, and MUST NOT print
a traceback or start the interface. Success and progress output SHALL go to standard output.

#### Scenario: Expected failure returns one

- **WHEN** a headless command cannot complete for an expected reason
- **THEN** it writes one actionable message to standard error and exits `1`

#### Scenario: Usage error returns two

- **WHEN** a headless command receives invalid arguments
- **THEN** it writes the usage error to standard error and exits `2`

#### Scenario: No traceback is printed

- **WHEN** a headless command fails for any reason
- **THEN** standard error carries a message rather than a traceback

#### Scenario: Success output goes to standard output

- **WHEN** a headless command succeeds
- **THEN** its report appears on standard output and standard error stays empty
