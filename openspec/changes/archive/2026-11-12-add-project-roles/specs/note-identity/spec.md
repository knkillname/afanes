# Spec Delta

## ADDED Requirements

### Requirement: Metadata role rewrites preserve surrounding data

A rewrite of a metadata role reference SHALL change only the matching value. Frontmatter unknown
keys, body text, newline style, and every other step metadata key SHALL be preserved. The file SHALL
be written atomically, and a failed rewrite SHALL leave the file unchanged.

#### Scenario: Frontmatter keys survive an owner rewrite

- **WHEN** a project with `owner: Sam Rivera` and an unknown `priority: high` key is rewritten
- **THEN** only the owner value changes and `priority: high` remains

#### Scenario: Step metadata survives an owner rewrite

- **WHEN** a step declares `owners: [Sam Rivera]`, `plan`, `actual`, `tags`, and an unknown key
- **THEN** only the owner name changes and every other metadata key is preserved

#### Scenario: Newlines survive a rewrite

- **WHEN** a CRLF note contains a role reference and the referenced note is renamed
- **THEN** the rewritten note keeps CRLF line endings

#### Scenario: A failed rewrite leaves the file unchanged

- **WHEN** a metadata role rewrite fails
- **THEN** the file's content and modification time are unchanged

## MODIFIED Requirements

### Requirement: Renames maintain references

A rename SHALL change the filename and SHALL update affected references, including metadata role
references. The application SHALL show the affected count and require explicit confirmation before
writing. Each affected file SHALL be written atomically. Failures and skipped files SHALL be
reported, and the operation SHALL be safe to re-run. No reference SHALL be rewritten silently.

#### Scenario: Rename is previewed

- **WHEN** the user requests a rename
- **THEN** the application reports how many references in how many notes would change before asking
  for confirmation

#### Scenario: Confirmed rename updates destinations

- **WHEN** the user confirms renaming `Ada Lovelace` to `Ada King`
- **THEN** every resolving `note:Ada Lovelace` destination becomes `note:Ada King`

#### Scenario: Cancelled rename changes nothing

- **WHEN** the user cancels at the preview
- **THEN** no file is renamed and no reference is rewritten

#### Scenario: Custom label is preserved

- **WHEN** a reference label differs from the old name
- **THEN** the rewrite updates the destination and leaves the custom label intact

#### Scenario: Changed file is skipped

- **WHEN** a referring note changed on disk after the preview
- **THEN** that note is skipped and reported rather than overwritten

#### Scenario: Partial failure is reported

- **WHEN** a rewrite fails for one referring note
- **THEN** the application reports which notes were updated and which were not

#### Scenario: Re-run completes the update

- **WHEN** the rename is run again after a partial failure
- **THEN** remaining old-name references are found and updated without duplicating prior work

#### Scenario: Project role names are rewritten

- **WHEN** a project declares `owner: Sam Rivera` or `asked_by: Sam Rivera` and the note named
  `Sam Rivera` is renamed
- **THEN** both matching values are rewritten to the new name

#### Scenario: Step owner names are rewritten

- **WHEN** a step declares `owners: [Sam Rivera, Ada]` and the note named `Sam Rivera` is renamed
- **THEN** only `Sam Rivera` changes and `Ada` remains

#### Scenario: Metadata rewrite is counted in the preview

- **WHEN** the only reference to `Sam Rivera` is a project owner value
- **THEN** the rename preview reports that project as an affected note

### Requirement: Deletion reports inbound references

Before deleting a note, the application SHALL report how many references point to it, including
metadata role references. After deletion, those references SHALL become unresolved. Deletion MUST
NOT rewrite or remove references.

#### Scenario: Inbound count is shown

- **WHEN** the user requests deletion of a referenced note
- **THEN** the application reports the number of inbound references before confirmation

#### Scenario: References remain unresolved

- **WHEN** a referenced note is deleted
- **THEN** its inbound references are reported as unresolved and remain in the referring notes

#### Scenario: Deletion removes no reference text

- **WHEN** a referenced note is deleted
- **THEN** no referring note is modified

#### Scenario: Role names count as inbound references

- **WHEN** a note is named only as a project owner, requester, or step owner
- **THEN** deletion reports it as an inbound reference

#### Scenario: Role values remain after deletion

- **WHEN** a note named as an owner or requester is deleted
- **THEN** the project keeps the plain-text value and the connection becomes unresolved
