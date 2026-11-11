# Spec Delta

## MODIFIED Requirements

### Requirement: The preview is read-only

Selecting a note SHALL open it in the page read mode with its display title and Markdown body rendered read-only. The preview MUST NOT display raw frontmatter as body text or write to the note. Internal link taps SHALL navigate as defined by the `note-editing` capability; external, attachment, and unsafe destinations SHALL remain inert.

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

- **WHEN** the user taps an external, attachment, or unsafe destination in the preview
- **THEN** no note is changed, no navigation occurs, and no external program is launched

#### Scenario: Internal link navigates

- **WHEN** the user taps an internal reference in the preview
- **THEN** the page pane resolves it as defined by the `note-editing` capability

#### Scenario: Frontmatter is not body text

- **WHEN** the user selects a note with frontmatter
- **THEN** the preview shows the body without the raw frontmatter block
