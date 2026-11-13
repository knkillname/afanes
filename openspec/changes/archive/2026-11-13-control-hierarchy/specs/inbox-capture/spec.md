# Spec Delta

## MODIFIED Requirements

### Requirement: Capture writes a note into the inbox

Capturing text SHALL create a Markdown note under the vault's `inbox/` directory, creating the
directory when missing. The note SHALL declare `type: note` and today's `date` in ISO form, and MUST
NOT declare `status`. A successful capture SHALL clear the composer for the next thought.

#### Scenario: Capture creates a note

- **WHEN** the user captures `Buy milk`
- **THEN** `inbox/Buy milk.md` exists with `type: note` and today's date

#### Scenario: No status is written

- **WHEN** a captured note is created
- **THEN** its frontmatter has no `status` key

#### Scenario: Inbox directory is created on demand

- **WHEN** the vault has no `inbox/` directory and the user captures
- **THEN** the directory is created and the note is written

#### Scenario: The capture action is insensitive while blank

- **WHEN** the composer is empty or contains only whitespace
- **THEN** the Capture action is insensitive and no file is created

#### Scenario: Empty capture is rejected

- **WHEN** a blank capture reaches the command without passing through the interface
- **THEN** no file is created and the error is reported

#### Scenario: Successful capture clears the composer

- **WHEN** the capture is written
- **THEN** the composer is empty and ready for another thought

#### Scenario: The capture date is today

- **WHEN** the user captures on 12 October 2025
- **THEN** the note declares `date: 2025-10-12`
