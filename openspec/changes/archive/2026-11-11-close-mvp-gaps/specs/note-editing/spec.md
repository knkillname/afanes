# Spec Delta

## ADDED Requirements

### Requirement: An open page follows an external edit

While a page is open, a change made to its file outside the application SHALL be detected without a manual refresh. A page with no unsaved changes SHALL reload the new content; a page with unsaved edits SHALL raise the existing conflict state instead of replacing the draft.

#### Scenario: A clean page reloads

- **WHEN** the open page's file changes on disk and the draft has no unsaved changes
- **THEN** the page shows the current file content without the user asking for a reload

#### Scenario: A dirty draft is kept

- **WHEN** the open page's file changes on disk while the draft has unsaved edits
- **THEN** the draft is kept and the reload, overwrite, or discard choice is offered

#### Scenario: A deleted page is reported

- **WHEN** the open page's file is removed outside the application
- **THEN** the page reports that the file is missing and offers to recreate it or discard the draft

#### Scenario: The application's own write does not conflict

- **WHEN** the application writes the open page itself
- **THEN** no conflict is raised and the page shows the written content

#### Scenario: Resolution keeps its meaning

- **WHEN** the user resolves a conflict raised by an external edit
- **THEN** the reload, overwrite, recreate, and discard actions behave as before
