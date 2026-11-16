# Spec Delta

## ADDED Requirements

### Requirement: The application icon follows the GNOME app-icon template

The packaged application icon SHALL be drawn on the GNOME Human Interface Guidelines 128×128
app-icon template, use its 2 px grid and bottom baseline, keep the artwork inside the template's
safe area, show a front profile darker than the top surface, and use only GNOME palette colors. It
SHALL remain recognizable at 32 px on light and dark backgrounds.

#### Scenario: The icon uses the template canvas

- **WHEN** the SVG icon is inspected
- **THEN** its viewBox is 128×128 and its artwork stays inside the template's safe area and baseline

#### Scenario: The icon keeps the template's visual weight

- **WHEN** the filled geometry is measured
- **THEN** no single filled shape spans the full canvas edge to edge

#### Scenario: The icon has depth

- **WHEN** the icon is rendered
- **THEN** the front profile is darker than the top surface

#### Scenario: The icon uses palette colors

- **WHEN** every fill and stroke is inspected
- **THEN** each color is one of the GNOME palette colors

#### Scenario: The icon survives 32 px

- **WHEN** the icon is rendered at 32 px on light and dark backgrounds
- **THEN** the page silhouette, fold, and check remain visible
