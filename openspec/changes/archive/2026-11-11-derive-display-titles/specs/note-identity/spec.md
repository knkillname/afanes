# Spec Delta

## MODIFIED Requirements

### Requirement: Filename determines name and title

A note's filename stem SHALL be its name and identity. The directory and the `.md` extension SHALL NOT be part of the name. No stored `id` or `title` key SHALL participate in identity. The display title SHALL be derived from the body as defined by "Display title comes from the first level-1 heading".

#### Scenario: Title is the stem

- **WHEN** `people/Ada Lovelace.md` has no level-1 heading
- **THEN** its display title and reference name are `Ada Lovelace`

#### Scenario: Directory is not part of the name

- **WHEN** a note moves from `work/` to `people/`
- **THEN** its name and identity are unchanged

#### Scenario: Stored id is ignored

- **WHEN** a note's frontmatter contains an `id` key
- **THEN** the key is preserved as unknown data and is not used for identity

#### Scenario: Stored title is ignored

- **WHEN** a note's frontmatter contains a `title` key
- **THEN** the key is preserved as unknown data and does not override the heading-derived display title

#### Scenario: Display preserves case

- **WHEN** a note is named `Turing Machine.md` and has no level-1 heading
- **THEN** its title is displayed as `Turing Machine` and not lowercased

### Requirement: Cross-platform name sanitization

When creating or renaming a note, the application SHALL derive a filename safe on macOS, Linux, and Windows: replace forbidden characters, avoid reserved device names, remove trailing dots and spaces, remove leading dots, enforce a 200-byte UTF-8 limit, and write NFC. The sanitized stem SHALL become the note's identity and reference name. It SHALL NOT replace the display title.

#### Scenario: Forbidden characters are replaced

- **WHEN** a title source is `Q1: Planning?`
- **THEN** the derived identity is `Q1 Planning`

#### Scenario: Sanitization preserves the display title

- **WHEN** a page is created from `Q1: Planning?`
- **THEN** its identity is `Q1 Planning` and its body heading still reads `# Q1: Planning?`

#### Scenario: Reserved device name is avoided

- **WHEN** a title source is `CON`
- **THEN** the derived identity is `CON-note`

#### Scenario: Trailing dot or space is removed

- **WHEN** a title source ends with a dot or a space
- **THEN** the derived identity does not

#### Scenario: Leading dot is removed

- **WHEN** a title source begins with a dot
- **THEN** the derived identity does not begin with a dot

#### Scenario: Length is bounded

- **WHEN** a title source exceeds the byte limit
- **THEN** the derived identity is truncated to fit and remains unique

#### Scenario: Empty result has a fallback

- **WHEN** a title source sanitizes to an empty identity
- **THEN** the derived identity is `Untitled`

## ADDED Requirements

### Requirement: Display title comes from the first level-1 heading

The display title of a note SHALL be the text of the first level-1 Markdown heading in its body. When the body has no level-1 heading, or its first level-1 heading has blank text, the display title SHALL be the note's identity. The display title SHALL NOT participate in identity, uniqueness, or reference resolution.

#### Scenario: Heading becomes the title

- **WHEN** a note with identity `Ada` has a body starting with `# Ada, Countess of Lovelace`
- **THEN** the application displays `Ada, Countess of Lovelace` as its title

#### Scenario: Missing heading falls back

- **WHEN** a note has no level-1 heading
- **THEN** the application displays its identity as the title

#### Scenario: First heading wins

- **WHEN** a body has two level-1 headings
- **THEN** the first one is the display title

#### Scenario: Heading after introductory text

- **WHEN** a body begins with a paragraph and later has a level-1 heading
- **THEN** that heading is still the display title

#### Scenario: Heading in a code block is ignored

- **WHEN** the only line beginning with `#` is inside a fenced code block
- **THEN** the note falls back to its identity as the title

#### Scenario: Title edit changes no reference

- **WHEN** a note's level-1 heading is edited from `Ada` to `Ada, Countess of Lovelace`
- **THEN** `person:Ada` still resolves to the note and no reference is rewritten

#### Scenario: Duplicate titles are allowed

- **WHEN** two notes have the same level-1 heading
- **THEN** both keep that title and remain distinct by identity
