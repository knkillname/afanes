# Spec Delta

## MODIFIED Requirements

### Requirement: No required layout

The application SHALL continue to accept notes anywhere in a versioned vault. The default layout MUST NOT become a requirement for opening or scanning a versioned vault. The five default folders are used only as a compatibility hint when offering adoption to an unversioned folder.

#### Scenario: Note in a custom folder resolves

- **WHEN** a reference note with `category: person` lives in `work/Ada.md`
- **THEN** `person:Ada` resolves to it

#### Scenario: Custom vault structure opens

- **WHEN** a versioned vault contains only custom directories
- **THEN** it opens and scans without requiring a default folder

#### Scenario: No marker is created

- **WHEN** a vault is opened or scanned
- **THEN** no default folder, layout marker, or other layout file is created

#### Scenario: Adoption uses the default folders as a hint

- **WHEN** an unversioned folder contains all five default folders
- **THEN** the application may offer adoption

#### Scenario: A versioned custom vault is not treated as unversioned

- **WHEN** a versioned vault lacks one or more default folders
- **THEN** it opens normally and is not offered adoption
