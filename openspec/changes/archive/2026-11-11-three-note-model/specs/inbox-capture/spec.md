# Spec Delta

## ADDED Requirements

### Requirement: The note type means unclarified

A captured note's `type: note` SHALL mean that the note has not been clarified. Non-actionable documents SHALL be references. A `type: note` outside `inbox/` SHALL be reported as misplaced and MUST NOT be processed.

#### Scenario: Capture is unclarified

- **WHEN** a note is captured
- **THEN** its `type: note` means it is pending clarification

#### Scenario: A document is a reference

- **WHEN** the user keeps a long document that is not work
- **THEN** it is a reference and not a `type: note`

#### Scenario: Misplaced note is reported

- **WHEN** a parsed `type: note` exists outside `inbox/`
- **THEN** the application reports it as misplaced and leaves the file unchanged

#### Scenario: Misplaced note is not queued

- **WHEN** a `type: note` outside `inbox/` is reported
- **THEN** it does not appear in the Inbox or the processing queue
