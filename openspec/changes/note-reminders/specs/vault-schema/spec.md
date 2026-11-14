# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Version 1 is the current schema`
- TO: `### Requirement: Version 2 is the current schema`

## MODIFIED Requirements

### Requirement: Version 2 is the current schema

The settings file SHALL contain a YAML mapping with exactly one key, `schema_version`, whose value is
the integer `2`. Extra keys, malformed YAML, a missing key, and a non-integer value SHALL make the
file invalid.

#### Scenario: The current schema is valid

- **WHEN** the file contains exactly `schema_version: 2`
- **THEN** the file is valid

#### Scenario: An extra key makes the file invalid

- **WHEN** the file contains `schema_version: 2` and another key
- **THEN** the file is invalid

#### Scenario: Malformed YAML makes the file invalid

- **WHEN** the file is not valid YAML
- **THEN** the file is invalid

#### Scenario: A missing schema version makes the file invalid

- **WHEN** the file contains no `schema_version` key
- **THEN** the file is invalid

#### Scenario: A non-integer schema version makes the file invalid

- **WHEN** `schema_version` is a string, boolean, or other non-integer value
- **THEN** the file is invalid

### Requirement: A vault requires a valid settings file

Opening a folder without `afanes.yaml` SHALL be refused. Opening MUST NOT create the file. A vault
with a valid file SHALL pass schema validation without modifying any vault file, including when the
vault is read-only. After validation, a writable schema `1` vault MAY be upgraded before scanning by
rewriting only `afanes.yaml`.

#### Scenario: A missing settings file is refused

- **WHEN** a folder has no `afanes.yaml`
- **THEN** the application refuses to open it as a vault

#### Scenario: Opening does not create the file

- **WHEN** an unversioned folder is opened
- **THEN** no `afanes.yaml` is created

#### Scenario: Opening a valid vault writes nothing

- **WHEN** a vault with a valid settings file passes schema validation
- **THEN** validation creates, modifies, or deletes no vault file

#### Scenario: Scanning writes nothing

- **WHEN** a versioned vault is scanned or refreshed
- **THEN** no vault file is created, modified, or deleted

#### Scenario: A read-only vault with a valid file opens

- **WHEN** a read-only folder contains a valid `afanes.yaml`
- **THEN** the vault opens for browsing

#### Scenario: A read-only vault without a file is refused

- **WHEN** a read-only folder has no `afanes.yaml`
- **THEN** the application refuses to open it as a vault

#### Scenario: A writable old vault is upgraded after validation

- **WHEN** validation accepts a writable schema `1` file
- **THEN** the file may be upgraded before scanning and validation still writes nothing

### Requirement: New vaults are created versioned

Vault creation SHALL write `afanes.yaml` with the current schema before writing starter content. A
creation that fails while writing notes SHALL leave a valid settings file so the partially created
folder remains openable as a vault.

#### Scenario: A new vault contains the settings file

- **WHEN** a vault is created
- **THEN** `afanes.yaml` exists at its root with `schema_version: 2`

#### Scenario: The settings file is written before starter content

- **WHEN** vault creation writes the settings file and then starter content
- **THEN** a starter-content failure leaves the settings file in place

#### Scenario: A created vault reports the settings file

- **WHEN** vault creation succeeds
- **THEN** the report names the settings file and its schema version

### Requirement: Settings file access is contained and atomic

The settings file SHALL be read and written only inside the vault root. A path that is a symlink, a
directory, or resolves outside the vault SHALL be refused. Writes SHALL be atomic. Creation and
adoption MUST NOT overwrite an existing settings file; a schema `1` upgrade MAY replace only a valid
schema `1` file with schema `2`.

#### Scenario: A symlink is refused

- **WHEN** `afanes.yaml` is a symbolic link
- **THEN** the application refuses to use it

#### Scenario: A directory is refused

- **WHEN** `afanes.yaml` is a directory
- **THEN** the application refuses to use it

#### Scenario: A failed write leaves the previous file intact

- **WHEN** writing the settings file fails partway
- **THEN** any previous settings file remains readable and unchanged

#### Scenario: An upgrade replaces only a valid older file

- **WHEN** a schema `1` file is upgraded
- **THEN** only that file is replaced, atomically, with schema `2`

#### Scenario: An upgrade does not replace a newer file

- **WHEN** the file declares schema `2` or newer
- **THEN** no upgrade write occurs

## REMOVED Requirements

### Requirement: Unsupported schemas are refused and preserved

**Reason**: Schema `1` is now a valid older format that is upgraded when writable or opened read-only
with reminders off; a blanket refusal is no longer correct.

**Migration**: Use “Newer and invalid schemas are refused and preserved” for newer or invalid files,
and the schema `1` compatibility requirements for older files.

### Requirement: Schema migrations are forward-only

**Reason**: The pre-1.0 policy now includes a courtesy upgrade for a writable schema `1` vault and
read-only browsing for a read-only one, so the old blanket-refusal wording no longer describes the
behavior.

**Migration**: Use “Schema compatibility is forward-only”.

## ADDED Requirements

### Requirement: Newer and invalid schemas are refused and preserved

A file that declares a schema newer than the current one, or is invalid, SHALL be refused, left
unchanged, and reported. It MUST NOT be repaired, rewritten, deleted, or replaced. A schema `1` file
SHALL be accepted only for the upgrade or read-only behavior defined by the older-schema
requirements.

#### Scenario: A newer schema is refused

- **WHEN** the file declares `schema_version: 3`
- **THEN** the application refuses to open the vault and tells the user to update Afanes

#### Scenario: An invalid file is preserved

- **WHEN** the settings file is malformed, contains an extra key, or has an unsupported value
- **THEN** the file is left byte-for-byte unchanged

#### Scenario: An invalid file is not adopted

- **WHEN** an unversioned-looking folder contains an invalid `afanes.yaml`
- **THEN** the application does not offer adoption and does not overwrite the file

#### Scenario: A schema 1 file is not invalid

- **WHEN** the file declares exactly `schema_version: 1`
- **THEN** the file is treated as an older valid schema, not as a malformed file

### Requirement: Schema compatibility is forward-only

Before 1.0, a schema change MAY accept, migrate, or refuse an old vault. This change upgrades a
writable schema `1` vault and opens a read-only one with reminders off. From 1.0 onward, a schema bump
SHALL ship with a forward migration. A newer schema SHALL always be refused by an older application,
and downgrades SHALL NOT be supported.

#### Scenario: A pre-1.0 schema change may accept an old vault

- **WHEN** a writable vault uses schema `1`
- **THEN** the vault is upgraded to schema `2`

#### Scenario: A read-only old vault may open with a feature off

- **WHEN** a read-only vault uses schema `1`
- **THEN** it opens for browsing with reminders off

#### Scenario: A post-1.0 schema change migrates old vaults

- **WHEN** the schema changes after 1.0
- **THEN** an older vault is migrated to the new schema

#### Scenario: A newer schema is refused by an older application

- **WHEN** an older application opens a vault written with a newer schema
- **THEN** it refuses to open the vault

#### Scenario: A downgrade is not performed

- **WHEN** a vault uses a newer schema than the application supports
- **THEN** the application does not rewrite it to an older schema

### Requirement: A writable schema 1 vault is upgraded

When a schema `1` file is writable, the application SHALL rewrite only `afanes.yaml` with
`schema_version: 2` after validation and before scanning, using an atomic write. A failed write SHALL
leave the previous file intact and SHALL NOT produce a partially upgraded vault. The upgrade SHALL be
reported once to the user.

#### Scenario: A writable old vault becomes version 2

- **WHEN** a writable schema `1` vault opens
- **THEN** `afanes.yaml` contains `schema_version: 2`

#### Scenario: Only the settings file changes

- **WHEN** a schema `1` vault is upgraded
- **THEN** no note, folder, guide, or card is created, changed, or removed

#### Scenario: A failed upgrade leaves version 1

- **WHEN** the upgrade write fails
- **THEN** the previous schema `1` file remains readable and unchanged

#### Scenario: The upgrade is reported once

- **WHEN** the upgrade succeeds
- **THEN** a one-time notice reports the new vault format

#### Scenario: An already current vault is not upgraded

- **WHEN** a schema `2` vault opens
- **THEN** no upgrade write occurs

### Requirement: A read-only schema 1 vault opens with reminders off

A schema `1` vault whose settings file cannot be rewritten SHALL open for browsing with the reminder
capability disabled. It MUST NOT write any vault file and SHALL report the read-only old format.

#### Scenario: A read-only old vault opens

- **WHEN** a read-only folder contains a schema `1` `afanes.yaml`
- **THEN** the vault opens for browsing

#### Scenario: A read-only old vault is not upgraded

- **WHEN** a read-only schema `1` vault opens
- **THEN** `afanes.yaml` remains at schema `1`

#### Scenario: Reminders are off in a read-only old vault

- **WHEN** a read-only schema `1` vault is open
- **THEN** reminders are not shown, counted, or offered

#### Scenario: The read-only old format is reported

- **WHEN** a read-only schema `1` vault is open
- **THEN** a persistent notice explains that the vault must be writable to upgrade

#### Scenario: A later writable open upgrades

- **WHEN** the same vault becomes writable and opens again
- **THEN** it is upgraded to schema `2` and reminders become available
