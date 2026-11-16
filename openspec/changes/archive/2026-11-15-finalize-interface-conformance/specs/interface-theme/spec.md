# Spec Delta

## ADDED Requirements

### Requirement: The application carries one original identity icon

The packaged application SHALL carry one original SVG application icon. The icon SHALL contain no
text, script, external reference, or embedded raster image, and MUST remain legible on light and dark
desktops from 16 to 256 pixels. It is an identity asset, not an interface icon.

#### Scenario: The package carries the icon

- **WHEN** a desktop artifact is built
- **THEN** it uses the application icon from the source assets

#### Scenario: The icon is self-contained

- **WHEN** the SVG icon is inspected
- **THEN** it contains no text, script, external reference, or embedded raster image

#### Scenario: The icon scales

- **WHEN** the icon is rendered at small and large sizes
- **THEN** its silhouette remains recognizable and its colors remain legible on light and dark
  desktops

#### Scenario: Interface icons stay separate

- **WHEN** the application icon is added
- **THEN** the interface continues to use the toolkit's monochrome symbolic glyphs

### Requirement: Empty views use a symbolic placeholder page

A browser destination that has no rows, a search with no matches, and the detail region with no open
page SHALL show a symbolic placeholder page. The page SHALL carry one monochrome icon, a heading, an
optional guidance line, and at most one suggested action. It MUST NOT replace a focused flow, an open
page, or a persistent banner.

#### Scenario: An empty destination shows guidance

- **WHEN** a browser destination has no rows
- **THEN** the browser shows a symbolic placeholder page with a heading and guidance for that
  destination

#### Scenario: A search without matches shows guidance

- **WHEN** a search returns no notes
- **THEN** the browser shows a symbolic placeholder page that names the empty result and suggests a
  different search

#### Scenario: Empty Trash shows guidance

- **WHEN** Trash has no managed entries
- **THEN** the browser shows a symbolic placeholder page and offers no destructive action

#### Scenario: No page open shows guidance

- **WHEN** the detail region has no page or focused flow
- **THEN** it shows a symbolic placeholder page that asks the user to select a note

#### Scenario: Placeholder actions are optional

- **WHEN** a placeholder page offers an action
- **THEN** it offers at most one suggested action and no duplicate browser-header action

#### Scenario: The placeholder is announced correctly

- **WHEN** a placeholder page renders
- **THEN** its heading and guidance supply the accessible name and its icon is decorative

#### Scenario: Flows and banners take precedence

- **WHEN** a page, focused flow, or persistent banner is present
- **THEN** the placeholder page is not shown in the affected region

### Requirement: High contrast follows the platform preference

When the platform reports its high-contrast accessibility feature, the interface SHALL use a
high-contrast light or dark palette. The application SHALL read the report at startup and when it
resumes. Body text MUST keep at least 7:1 contrast, boundaries and focus MUST remain visible, and
state MUST NOT rely on hue alone.

#### Scenario: High contrast in light appearance

- **WHEN** the platform reports high contrast while the light appearance is active
- **THEN** the interface uses the high-contrast light palette

#### Scenario: High contrast in dark appearance

- **WHEN** the platform reports high contrast while the dark appearance is active
- **THEN** the interface uses the high-contrast dark palette

#### Scenario: Standard contrast is preserved

- **WHEN** the platform reports no high contrast
- **THEN** the interface uses the standard light or dark palette

#### Scenario: The preference is re-read on resume

- **WHEN** the high-contrast setting changes while the application is suspended
- **THEN** the new palette applies when the application resumes without a manual rebuild of the vault
  state

#### Scenario: Body contrast holds

- **WHEN** either high-contrast palette is active
- **THEN** body text meets at least 7:1 contrast on its page, card, and region surfaces

#### Scenario: Boundaries and focus remain visible

- **WHEN** either high-contrast palette is active
- **THEN** borders, separators, and the focus ring remain visible against adjacent surfaces

#### Scenario: State survives without hue

- **WHEN** either high-contrast palette is active
- **THEN** selection, focus, and destructive intent remain distinguishable without relying on color
  alone
