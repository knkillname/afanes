# Spec Delta

## ADDED Requirements

### Requirement: Bundled cards follow the active locale

The eight bundled template cards SHALL be selected for the active locale, with English as the
fallback when a locale set is missing. Card identifiers, types, categories, and count SHALL remain
stable across locales. The seeded cards SHALL contain localized titles, descriptions, and starter
bodies.

#### Scenario: A Spanish vault seeds Spanish cards

- **WHEN** a vault is created under Spanish
- **THEN** `templates/` contains the eight cards with Spanish titles, descriptions, and starter bodies

#### Scenario: A missing Spanish set falls back to English

- **WHEN** the Spanish card set is missing
- **THEN** the eight English cards are seeded and creation succeeds

#### Scenario: Card identity stays stable

- **WHEN** the English and Spanish card sets are compared
- **THEN** each card keeps its filename, type, and category

#### Scenario: The Daily entry card remains a log card

- **WHEN** a Spanish vault is created
- **THEN** `templates/daily.md` declares `type: log`, no category, and a Spanish reflection body

#### Scenario: Eight cards are always seeded

- **WHEN** a vault is created under either locale
- **THEN** exactly eight template cards are written

#### Scenario: An invalid localized card is refused

- **WHEN** a Spanish card is malformed
- **THEN** creation is refused before any card is written and the invalid card is named

#### Scenario: User edits are never overwritten

- **WHEN** the user edits a seeded card and reopens the vault
- **THEN** the edited card remains in place and is not replaced by the bundled translation
