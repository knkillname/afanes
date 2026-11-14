# vault-schema Specification

## Purpose

Defines the vault settings file that records the on-disk schema version, how a vault is validated, adopted, and migrated, and the safety rules for reading and writing that file.

## Requirements

### Requirement: The vault root carries a settings file

A vault SHALL contain `afanes.yaml` at its root, named exactly and stored as a regular UTF-8 file. It MUST NOT be scanned as a note, appear in browser groups, participate in name uniqueness, or resolve as a reference.

#### Scenario: The current settings file is accepted

- **WHEN** a vault contains `afanes.yaml` with `schema_version: 1`
- **THEN** the vault is accepted

#### Scenario: A case variant is not the settings file

- **WHEN** a vault contains only `Afanes.yaml`
- **THEN** it has no settings file

#### Scenario: The settings file is not a note

- **WHEN** a vault contains `afanes.yaml`
- **THEN** the file does not appear in the scanned note set, browser groups, name uniqueness, or reference resolution

#### Scenario: A reference to the file name is unresolved

- **WHEN** a note links to `note:afanes` and the vault contains only `afanes.yaml`
- **THEN** the reference is unresolved

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

### Requirement: Adoption requires the default layout

The application SHALL offer adoption only when an unversioned folder is writable and contains all five default folders: `inbox/`, `trash/`, `reference/`, `projects/`, and `log/`. Folder names SHALL be matched case-insensitively. `templates/` SHALL be optional, and extra folders MUST be allowed.

#### Scenario: All five default folders enable adoption

- **WHEN** an unversioned folder contains all five default folders
- **THEN** the application offers adoption

#### Scenario: A missing default folder prevents adoption

- **WHEN** an unversioned folder is missing any of the five default folders
- **THEN** the application does not offer adoption

#### Scenario: The templates folder is optional

- **WHEN** an unversioned folder contains the five default folders and no `templates/`
- **THEN** the application still offers adoption

#### Scenario: Folder names are matched case-insensitively

- **WHEN** an unversioned folder contains `Inbox/` instead of `inbox/`
- **THEN** the folder counts as having the inbox default folder

#### Scenario: Extra folders are allowed

- **WHEN** an unversioned folder contains the five default folders and additional folders
- **THEN** the application still offers adoption

### Requirement: Adoption is explicit and writes only the settings file

Adoption SHALL write only `afanes.yaml` with the current schema. It MUST NOT create notes, default folders, the guide, or template cards. Opening or scanning a folder MUST NOT adopt it.

#### Scenario: Adoption writes only the settings file

- **WHEN** an adoptable folder is adopted
- **THEN** only `afanes.yaml` is added and no note, folder, guide, or card is created

#### Scenario: Opening does not adopt a folder

- **WHEN** an adoptable folder is opened without confirming adoption
- **THEN** no file is written and the folder is not opened as a vault

#### Scenario: Adoption never overwrites an existing file

- **WHEN** adoption runs for a folder that already has `afanes.yaml`
- **THEN** the existing file is left unchanged

#### Scenario: An adopted folder opens as a normal vault

- **WHEN** adoption succeeds
- **THEN** the folder opens as a versioned vault and scans its notes

#### Scenario: An already versioned folder is not adopted again

- **WHEN** a folder with a valid settings file is selected for adoption
- **THEN** the application reports that it is already a vault and changes nothing

### Requirement: Read-only unversioned folders are refused

An unversioned folder that cannot be written SHALL be refused and MUST NOT be offered adoption. The message SHALL explain that the folder needs `afanes.yaml` or write access.

#### Scenario: A read-only unversioned folder is refused

- **WHEN** a read-only folder has no `afanes.yaml`
- **THEN** the application refuses to open it and does not offer adoption

#### Scenario: No file is created in a read-only folder

- **WHEN** a read-only unversioned folder is opened
- **THEN** no file is created

### Requirement: The schema version is independent of the application version

The schema version SHALL change only when the on-disk vault contract changes. A package release MUST NOT imply a schema version.

#### Scenario: An application release keeps the schema version

- **WHEN** a new application release changes no on-disk behavior
- **THEN** the schema version stays `1`

#### Scenario: A package version does not select a schema

- **WHEN** the application reports its package version
- **THEN** that version is not used as the vault schema version

#### Scenario: A schema change is deliberate

- **WHEN** the on-disk vault contract changes
- **THEN** the schema version changes with it

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
