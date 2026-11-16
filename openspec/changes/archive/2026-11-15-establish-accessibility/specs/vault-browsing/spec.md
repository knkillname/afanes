# Spec Delta

## MODIFIED Requirements

### Requirement: The workspace exposes the vault and its primary menu

The workspace SHALL show the vault identity in the navigation region and SHALL offer a primary menu above the navigation list. The menu SHALL provide Change Vault…, Create Vault…, Close Vault, Keyboard Shortcuts…, and About Afanes. The workspace MUST NOT show a separate status bar for the vault path or vault actions.

#### Scenario: Vault identity is visible

- **WHEN** a vault is open
- **THEN** the navigation region names the vault and its full path is available without a status bar

#### Scenario: The primary menu offers the app and vault actions

- **WHEN** the user opens the primary menu
- **THEN** Change Vault…, Create Vault…, Close Vault, Keyboard Shortcuts…, and About Afanes are available

#### Scenario: Change Vault uses the existing flow

- **WHEN** the user chooses Change Vault…
- **THEN** the existing vault chooser is shown

#### Scenario: Create Vault uses the existing flow

- **WHEN** the user chooses Create Vault…
- **THEN** the existing new-vault flow is shown

#### Scenario: Close Vault returns to the welcome state

- **WHEN** the user chooses Close Vault
- **THEN** the workspace closes and the welcome state is shown

#### Scenario: Keyboard Shortcuts opens the sheet

- **WHEN** the user chooses Keyboard Shortcuts…
- **THEN** the shortcut sheet opens over the workspace

#### Scenario: About names the application

- **WHEN** the user chooses About Afanes
- **THEN** a dialog names the application and its version

#### Scenario: No status bar remains

- **WHEN** the workspace renders
- **THEN** no status bar shows the vault path or duplicates the vault actions

### Requirement: Review shows its snapshot queue in the browser

While Review is active, the browser SHALL show the session's snapshot queue in review order as selectable cards and SHALL mark the current item. Selecting a card SHALL make that item current in the detail without reviewing, skipping, or reordering any item. Each card SHALL be reachable by keyboard and SHALL show a visible focus indicator. Showing the queue MUST NOT reorder it, add new work to it, or change review records.

#### Scenario: The queue is shown in order

- **WHEN** a review session starts with Inbox items, due steps, and projects
- **THEN** the browser lists them as cards in the session's order

#### Scenario: The current item is marked

- **WHEN** the review session advances
- **THEN** the browser marks the new current card

#### Scenario: Selecting a card shows that item

- **WHEN** the user selects a card in the browser queue
- **THEN** the detail shows that item and its actions

#### Scenario: Selecting a card changes no review record

- **WHEN** the user selects a card in the browser queue
- **THEN** no item is reviewed or skipped and the queue order is unchanged

#### Scenario: A card is reachable by keyboard

- **WHEN** the user tabs through the Review browser
- **THEN** every queue card receives focus in queue order and shows a visible focus indicator

#### Scenario: Keyboard activation selects the card

- **WHEN** a focused queue card is activated from the keyboard
- **THEN** the detail shows that item and no review record changes

#### Scenario: New work waits for the next session

- **WHEN** a note is created during the session
- **THEN** the browser queue does not show it

#### Scenario: Viewing the queue changes no review state

- **WHEN** the user views the browser queue without selecting a card
- **THEN** no item is reviewed, skipped, or reordered

#### Scenario: A completed session shows its outcome

- **WHEN** every queue item has been passed
- **THEN** the browser no longer marks an active card and the detail shows the completion summary

## ADDED Requirements

### Requirement: Focus returns to the browser after trashing a page

When a page is moved to trash, focus SHALL move to the next visible note row in the browser's current
order, or to the previous row when none follows. If no note row remains, focus SHALL move to the
search field. The move MUST NOT change the active destination or clear an active query.

#### Scenario: Focus moves to the next row

- **WHEN** a page is trashed and another note row follows it in the browser
- **THEN** keyboard focus moves to that next row

#### Scenario: Focus falls back to the previous row

- **WHEN** a page is trashed and no note row follows it
- **THEN** keyboard focus moves to the previous row

#### Scenario: An empty browser focuses search

- **WHEN** a page is trashed and no note row remains
- **THEN** keyboard focus moves to the search field

#### Scenario: The destination and query survive

- **WHEN** a page is trashed while a destination or search query is active
- **THEN** the active destination and query remain unchanged and focus stays in the browser

#### Scenario: Trashing writes only the move

- **WHEN** focus returns to the browser after a trash
- **THEN** no note other than the trashed page is created, changed, or removed
