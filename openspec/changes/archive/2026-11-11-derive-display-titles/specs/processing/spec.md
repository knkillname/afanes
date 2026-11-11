# Spec Delta

## ADDED Requirements

### Requirement: Name entry suggests pages by title and identity

When the user assigns people or a project during processing, the input SHALL suggest existing pages by display title or identity. Selecting a suggestion SHALL store that page's identity. Text that matches no page SHALL remain an unresolved identity so the reference can resolve when the page is created.

#### Scenario: Typing a title suggests the page

- **WHEN** a person page has identity `Ada` and display title `Ada, Countess of Lovelace`
- **THEN** typing part of the title suggests that page

#### Scenario: Typing the identity suggests the page

- **WHEN** the user types `Ada` and a person page has identity `Ada`
- **THEN** that page is suggested

#### Scenario: Selecting a suggestion stores the identity

- **WHEN** the user selects the suggestion for a page whose title differs from its identity
- **THEN** the stored reference uses the identity, not the title

#### Scenario: Free text stays unresolved

- **WHEN** the user types a name that matches no person page
- **THEN** the reference is stored with that name and reported as unresolved

#### Scenario: Duplicate titles are distinct suggestions

- **WHEN** two person pages have the same display title
- **THEN** both appear as separate suggestions distinguished by their identities

#### Scenario: The project field follows the same rule

- **WHEN** the user assigns a project whose title differs from its identity
- **THEN** the stored reference uses the project's identity

#### Scenario: Matching ignores case and repeated whitespace

- **WHEN** the user types `ada` or `Ada,   Countess of Lovelace`
- **THEN** the matching page is suggested
