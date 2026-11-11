# Spec Delta

## MODIFIED Requirements

### Requirement: The filename comes from the first non-blank line

The filename stem SHALL be the first non-blank line of the captured text, processed by the vault's cross-platform name policy. That line SHALL become a level-1 heading at the start of the note body. The body SHALL be the captured text with `# ` inserted at the start of that line, unless the line already begins with `#`. All other captured text SHALL remain unchanged.

#### Scenario: First line becomes the name

- **WHEN** the user captures `Call Ada` followed by `about the invoice`
- **THEN** the note is named `Call Ada.md`

#### Scenario: Leading blank lines are skipped

- **WHEN** the captured text begins with blank lines
- **THEN** the first non-blank line becomes the name and receives the heading marker

#### Scenario: First line becomes the heading

- **WHEN** the user captures `Call Ada` followed by `about the invoice`
- **THEN** the body is `# Call Ada` followed by `about the invoice` on the next line

#### Scenario: Original wording is preserved in the heading

- **WHEN** the user captures `Q1: Planning?`
- **THEN** the identity is `Q1 Planning` and the body heading reads `# Q1: Planning?`

#### Scenario: An existing heading is not doubled

- **WHEN** the first non-blank line already begins with `#`
- **THEN** the body keeps that line as typed and adds no second heading marker

#### Scenario: The whole text is preserved

- **WHEN** the note is created
- **THEN** the body contains the complete captured text with `# ` inserted before the first non-blank line

#### Scenario: Unsafe characters are sanitized

- **WHEN** the first line contains characters forbidden in filenames
- **THEN** the derived filename applies the vault's cross-platform policy

#### Scenario: Repeated captures get distinct names

- **WHEN** the same text is captured twice
- **THEN** both notes exist with distinct names

### Requirement: The preview is read-only

Selecting a note SHALL show its display title and its Markdown body rendered read-only. The preview MUST NOT display raw frontmatter as body text, write to the note, or launch or navigate any link.

#### Scenario: Body is rendered

- **WHEN** the user selects a note
- **THEN** the preview shows the rendered Markdown body

#### Scenario: Title comes from the heading

- **WHEN** the user selects a note whose body starts with `# Call Ada`
- **THEN** the preview header shows `Call Ada`

#### Scenario: Title falls back to the identity

- **WHEN** the user selects a note with no level-1 heading
- **THEN** the preview header shows the note's identity

#### Scenario: Preview performs no write

- **WHEN** a note is previewed
- **THEN** the file's content and modification time are unchanged

#### Scenario: Link taps are inert

- **WHEN** the user taps a link in the preview
- **THEN** no note is changed, no navigation occurs, and no external program is launched

#### Scenario: Frontmatter is not body text

- **WHEN** the user selects a note with frontmatter
- **THEN** the preview shows the body without the raw frontmatter block

## ADDED Requirements

### Requirement: Inbox entries show the display title

Each Inbox entry SHALL show the note's display title as its primary text and its vault-relative path as the secondary text. Notes with the same display title SHALL remain distinguishable by that path.

#### Scenario: Entry uses the heading

- **WHEN** `inbox/Call Ada.md` has a body starting with `# Call Ada`
- **THEN** its Inbox entry shows `Call Ada`

#### Scenario: Entry falls back to the identity

- **WHEN** an Inbox note has no level-1 heading
- **THEN** its entry shows the note's identity

#### Scenario: Duplicate titles are distinguishable

- **WHEN** two Inbox notes both display the title `Buy milk`
- **THEN** each entry also shows its own vault-relative path
