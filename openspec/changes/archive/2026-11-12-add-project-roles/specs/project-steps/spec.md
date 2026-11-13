# Spec Delta

## MODIFIED Requirements

### Requirement: Owner names resolve as references

An owner name SHALL resolve against the same catalog as a `note:` reference, as a metadata
reference. An owner that matches no note SHALL remain valid and SHALL be reported as unresolved. A
rename of the named note SHALL rewrite the owner name, and trashing the named note SHALL leave the
owner name in place and make its connection unresolved.

#### Scenario: Owner resolves to a page

- **WHEN** a step declares `owners: [Ada]` and exactly one note is named `Ada`
- **THEN** the owner resolves to that note

#### Scenario: Unknown owner stays valid

- **WHEN** a step declares `owners: [Nobody]` and no note is named `Nobody`
- **THEN** the step keeps the owner and the owner is reported as unresolved

#### Scenario: Ambiguous owner contributes no connection

- **WHEN** two notes are named `Ada`
- **THEN** the step keeps the owner and neither page lists it under `Owned steps`

#### Scenario: Renaming the owner rewrites the step

- **WHEN** a step declares `owners: [Ada]` and the note named `Ada` is renamed to `Ada King`
- **THEN** the step metadata becomes `owners: [Ada King]`

#### Scenario: Trashing the owner leaves the step unchanged

- **WHEN** the note named `Ada` is moved to trash
- **THEN** the step keeps `owners: [Ada]` and the owned-step connection disappears

#### Scenario: Multiple owners update independently

- **WHEN** a step declares `owners: [Ada, Grace]` and only `Ada` is renamed
- **THEN** the step keeps `Grace` and rewrites only `Ada`
