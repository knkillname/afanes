# Spec Delta

## MODIFIED Requirements

### Requirement: A log date change renames, moves, and rewrites references

Changing a log entry's `date` SHALL rename the file, move it to the new date's folder, and rewrite
every inbound `log:` reference. The change SHALL NOT ask for confirmation. The level-1 heading
SHALL follow the date only when it equals a generated default title in any supported locale;
otherwise it SHALL be preserved. Failures SHALL be reported and the operation SHALL be safe to
re-run.

#### Scenario: A date change renames the file

- **WHEN** an entry dated `2025-10-12` is changed to `2025-10-13`
- **THEN** the file becomes `2025-10-13.md`

#### Scenario: A date change moves the file

- **WHEN** an entry dated `2025-10-12` is changed to `2025-11-02`
- **THEN** the file moves from `log/2025/10/` to `log/2025/11/`

#### Scenario: Inbound references are rewritten

- **WHEN** a note links to `log:2025-10-12` and the entry moves to `2025-10-13`
- **THEN** the referring destination becomes `log:2025-10-13`

#### Scenario: No confirmation is required

- **WHEN** the user changes a log entry's date
- **THEN** the rename, move, and rewrites run without a preview dialog

#### Scenario: The generated heading follows the date

- **WHEN** an entry titled `October 12, 2025` changes to `2025-10-13` under English
- **THEN** its heading becomes `October 13, 2025`

#### Scenario: The generated Spanish heading follows the date

- **WHEN** an entry titled `12 de octubre de 2025` changes to `2025-10-13` under Spanish
- **THEN** its heading becomes `13 de octubre de 2025`

#### Scenario: A generated heading from another locale follows the date

- **WHEN** an entry titled `October 12, 2025` changes to `2025-10-13` under Spanish
- **THEN** its heading becomes `13 de octubre de 2025`

#### Scenario: A Spanish generated heading follows the date under English

- **WHEN** an entry titled `12 de octubre de 2025` changes to `2025-10-13` under English
- **THEN** its heading becomes `October 13, 2025`

#### Scenario: The generated heading follows a precision change

- **WHEN** an entry titled `October 2025` changes to `2025`
- **THEN** its heading becomes `2025`

#### Scenario: The heading is kept

- **WHEN** an entry titled `A quiet Tuesday` changes date
- **THEN** its heading remains `A quiet Tuesday`

#### Scenario: A custom heading in another language is kept

- **WHEN** an entry titled `Un martes tranquilo` changes date
- **THEN** its heading remains `Un martes tranquilo`

#### Scenario: A date-shaped custom heading is kept

- **WHEN** an entry titled `2025-10-12` changes date
- **THEN** its heading remains `2025-10-12`

#### Scenario: A failed rewrite is reported

- **WHEN** one referring file changed on disk after the scan
- **THEN** that file is skipped, the entry still moves, and the skipped file is reported
