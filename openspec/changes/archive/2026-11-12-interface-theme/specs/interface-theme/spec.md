# Spec Delta

## Purpose

Defines the visual identity of the Afanes interface: how it follows the operating system's light or
dark mode, the palette roles it exposes, how accent and surface depth communicate structure, and
the minimum legibility guarantees in each mode.

## ADDED Requirements

### Requirement: Appearance follows the operating system mode

Afanes SHALL present a light interface when the operating system requests a light appearance and a
dark interface when it requests a dark appearance, without a separate in-app switch.

#### Scenario: Light system appearance

- **WHEN** the interface starts while the operating system requests a light appearance
- **THEN** the interface renders with its light palette

#### Scenario: Dark system appearance

- **WHEN** the interface starts while the operating system requests a dark appearance
- **THEN** the interface renders with its dark palette

#### Scenario: Appearance changes while running

- **WHEN** the operating system appearance changes while the interface is open
- **THEN** the interface updates to the matching palette without restarting

### Requirement: Both modes define a complete, legible palette

Each mode SHALL define values for the page background, layered surfaces, borders, body text, muted
text, accent, and status colors. The palette MUST NOT depend on unset defaults for any role it uses.

#### Scenario: Every role resolves in both modes

- **WHEN** the interface renders in either mode
- **THEN** every role it uses resolves to a defined value for that mode

#### Scenario: Contrast holds in both modes

- **WHEN** body text, muted text, control labels, and focus indicators are rendered in either mode
- **THEN** body text meets a 4.5:1 contrast ratio against its background, and large text, icons, and control boundaries meet 3:1

### Requirement: A restrained accent and action pair

The interface SHALL use one accent color for selected entries and focus indicators, and one action
color for filled primary buttons. It MUST NOT introduce further hues for emphasis, and it MUST NOT
rely on hue alone to signal state.

#### Scenario: Primary actions and selection use their assigned colors

- **WHEN** a primary action is shown and an entry is selected
- **THEN** the action uses the action color and the selection uses the accent color

#### Scenario: Focus is visible independently of hover

- **WHEN** a control receives keyboard focus
- **THEN** it shows a focus indicator using the accent color that does not depend on hover state

#### Scenario: State survives without hue

- **WHEN** the interface is viewed without color perception
- **THEN** selection, focus, and status remain distinguishable through shape, weight, icon, or text

### Requirement: Surfaces separate through boundaries

The page, structural regions such as the sidebar, and content cards SHALL be separated by visible
boundaries. The note canvas SHALL stay the brightest surface in light mode, and a selected list entry
MAY use a neutral fill to mark the selection.

#### Scenario: Structural regions separate from the page

- **WHEN** the workspace renders with its sidebar and content area
- **THEN** a visible boundary separates them from the page background in both modes

#### Scenario: Cards separate from their container

- **WHEN** a card or panel appears inside a structural region
- **THEN** its boundary distinguishes it from the region behind it in both modes

#### Scenario: The note canvas stays white

- **WHEN** a note is open in light mode
- **THEN** the Markdown canvas is the brightest surface in the window

#### Scenario: Selection uses a neutral fill

- **WHEN** a browser entry is selected
- **THEN** its row uses a neutral fill and remains distinguishable from an unselected row without
  relying on hue alone

### Requirement: Browser sections have a redundant identity

Each browser section SHALL be identifiable by its label and icon, with a distinct icon tint and an
active-entry marker. The identity MUST remain understandable without perceiving the tint.

#### Scenario: Section tint differs per section

- **WHEN** the browser lists Inbox, Projects, References, and Review
- **THEN** each section's leading icon uses its own tint

#### Scenario: Active section is marked beyond tint

- **WHEN** a section is active
- **THEN** its entry shows a marker in addition to the tint, such as an accent edge and selected
  state

#### Scenario: Tint is not the only cue

- **WHEN** the section tints are not distinguishable
- **THEN** the label and icon still identify each section

### Requirement: Typographic hierarchy uses one family

Interface text SHALL use a single font family. Hierarchy MUST come from size, weight, spacing, and
color rather than from additional font families or bundled font files.

#### Scenario: Page title outranks body text

- **WHEN** a note page shows its title above rendered body text
- **THEN** the title is visibly larger or heavier than the body text in the same family

#### Scenario: Secondary metadata recedes

- **WHEN** a note shows identity, path, or other metadata beside its title
- **THEN** the metadata uses the muted text role rather than the body text role

#### Scenario: No additional font is required

- **WHEN** the application runs on a machine without additional installed fonts
- **THEN** the interface renders its full hierarchy with the platform font family
