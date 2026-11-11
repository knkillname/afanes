# Spec Delta

## ADDED Requirements

### Requirement: Rename keeps a matching heading in step

When a note is renamed, its first level-1 heading SHALL be updated to the new identity only when that heading's text matches the old identity exactly after trimming surrounding whitespace. Any other heading SHALL be preserved. A note without a level-1 heading SHALL NOT gain one.

#### Scenario: Default heading follows the rename

- **WHEN** a note with identity `Ada` and the first heading `# Ada` is renamed to `Ada King`
- **THEN** the heading becomes `# Ada King`

#### Scenario: Custom heading is preserved

- **WHEN** a note with identity `Ada` and the first heading `# Ada, Countess of Lovelace` is renamed
- **THEN** the heading is unchanged

#### Scenario: Missing heading stays missing

- **WHEN** a note with no level-1 heading is renamed
- **THEN** no heading is added and the display title falls back to the new identity

#### Scenario: Heading in code is not a title

- **WHEN** the only matching line is inside a fenced code block
- **THEN** it is not treated as the display title and is not rewritten

#### Scenario: Heading update is part of the confirmed rename

- **WHEN** the user confirms a previewed rename
- **THEN** the heading update and the reference rewrites are applied by that same confirmed operation

#### Scenario: Cancelled rename changes no heading

- **WHEN** the user cancels at the rename preview
- **THEN** no heading is updated
