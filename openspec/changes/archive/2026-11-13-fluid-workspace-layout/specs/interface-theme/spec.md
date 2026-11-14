# Spec Delta

## REMOVED Requirements

### Requirement: Workspace columns use bounded widths

**Reason**: The browser and content maximum widths leave unused space on wide windows and conflict with the fluid layout; the browser and detail now share every remaining pixel above their minimum widths.

**Migration**: Use the added requirement **Workspace columns fill the available width**. Minimum widths, breakpoints, and the fixed navigation width remain unchanged.

## ADDED Requirements

### Requirement: Workspace columns fill the available width

The navigation, browser, and detail regions SHALL fill the window width. Navigation SHALL keep a fixed width. The browser and detail SHALL share the remaining width above their minimum widths and MUST NOT impose a maximum width. The detail SHALL fill its region with page content; long-form text and forms MUST NOT be constrained to a maximum content width.

#### Scenario: The browser has a minimum width

- **WHEN** the browser region is shown
- **THEN** its width is at least the browser minimum token

#### Scenario: The browser grows with the window

- **WHEN** the window is wider than the sum of the navigation and both minimum widths
- **THEN** the browser and detail share the remaining width and the browser does not stop at a maximum width

#### Scenario: The note text fills the detail on a large window

- **WHEN** a note is open in a very wide window
- **THEN** its prose and form controls use the width the detail region gives them rather than stopping at a maximum content width

#### Scenario: The detail keeps its minimum

- **WHEN** the browser is at its minimum width
- **THEN** the detail region is not narrower than its minimum content width

#### Scenario: The detail content fills the card

- **WHEN** the detail card is wider than the page minimum width
- **THEN** the page content grows with the card and leaves no lateral gutter beyond the card padding

#### Scenario: No control clips at the minimum window

- **WHEN** the workspace renders at 1024x600 in either mode
- **THEN** no navigation, browser, toolbar, or detail control clips horizontally or vertically
