# Spec Delta

## MODIFIED Requirements

### Requirement: Surfaces separate through boundaries

The window, navigation region, browser region, note view, and secondary containers SHALL resolve to four distinct surface values in each mode. Navigation SHALL use the sidebar surface and the browser SHALL use the window surface. Separation MAY combine a value step with a border. The note view SHALL be the brightest surface in light mode and darker than the window and navigation in dark mode. A selected entry SHALL use a neutral selected-row fill.

#### Scenario: The four roles differ

- **WHEN** the interface renders in either mode
- **THEN** the window, sidebar, note view, and secondary-container surfaces resolve to four different values

#### Scenario: Structural regions separate from the page

- **WHEN** the workspace renders with its navigation, browser, and detail regions
- **THEN** a value step or a visible boundary separates each region from the window background in both modes

#### Scenario: The browser shares the window surface

- **WHEN** the workspace renders its browser region
- **THEN** the browser uses the window surface and does not add a fifth surface role

#### Scenario: Cards separate from their container

- **WHEN** a view or panel appears inside a structural region
- **THEN** its surface or boundary distinguishes it from the region behind it in both modes

#### Scenario: The note canvas stays white

- **WHEN** a note is open in light mode
- **THEN** the Markdown view is the brightest surface in the window

#### Scenario: The note canvas is darker than the chrome in dark mode

- **WHEN** a note is open in dark mode
- **THEN** the Markdown view is darker than the window and navigation region

#### Scenario: Selection uses a neutral fill

- **WHEN** a navigation or browser entry is selected
- **THEN** its row uses the neutral selected-row token with no accent tint or accent edge, and remains distinguishable from an unselected row without relying on hue alone

### Requirement: Differences from the reference language are bounded

Afanes SHALL conform to the reference language except where the Flet toolkit cannot express a guideline mechanism: the Material interface icon set (asset-free), the toolkit's widget rendering, the absent access-key mnemonics, the absent high-contrast input, and the native title bar that cannot host application controls. The platform typeface is guideline-required, not a difference. Each difference MUST be recorded in the interface standard, and removing one SHALL require its own change.

#### Scenario: A new difference requires a spec change

- **WHEN** a change proposes a visual behavior outside the reference language
- **THEN** it records the difference and updates this requirement rather than adding it silently

#### Scenario: The recorded list matches the implementation

- **WHEN** the interface standard lists differences
- **THEN** that list matches the icon, widget-rendering, access-key, high-contrast, and native-title-bar behavior the application actually ships

#### Scenario: The platform typeface is not a difference

- **WHEN** the differences are listed
- **THEN** the platform typeface is described as the guideline-required choice rather than as a deviation

#### Scenario: The limiting toolkit is named

- **WHEN** a toolkit limitation is documented
- **THEN** it names the Flet API that is missing rather than a broader framework

#### Scenario: The title bar stays native

- **WHEN** the application runs on a desktop platform
- **THEN** the operating-system title bar is used as provided and the workspace toolbar is the in-window equivalent of the reference header bar

### Requirement: Control values come from the interface tokens

Every color, corner radius, spacing, dimension, icon size, column width, maximum content width, and minimum window value SHALL come from the interface token module. The minimum window SHALL be 1024x600. The build SHALL fail when a view or component introduces a value outside those tokens, except for entries enumerated in a conformance baseline that may only shrink.

#### Scenario: A literal fails the build

- **WHEN** a view or component introduces a color, radius, spacing, dimension, icon size, column width, content width, or minimum-window literal that is not in the token module
- **THEN** the conformance gate fails and names the file and value

#### Scenario: The baseline may only shrink

- **WHEN** a change removes a baseline entry by migrating the offending code
- **THEN** the same change deletes that entry, and a baseline entry that no longer matches a violation also fails the gate

#### Scenario: The smallest window fits the reference desktop size

- **WHEN** the application opens at its minimum window size
- **THEN** the window is 1024x600 and no control clips

#### Scenario: Column widths come from tokens

- **WHEN** the workspace lays out its navigation, browser, and detail regions
- **THEN** every width and breakpoint comes from a named token rather than a literal in a view

#### Scenario: Strict visual rules are gated

- **WHEN** a view introduces a Material text-role name, an arbitrary icon size, or an accent selection
- **THEN** the conformance gate fails

## ADDED Requirements

### Requirement: Workspace columns use bounded widths

The navigation, browser, and detail regions SHALL have widths that support adaptive scaling. Navigation SHALL keep a fixed width. The browser SHALL have a minimum and maximum width. The detail SHALL keep at least its minimum content width and SHALL constrain long-form text and forms to a maximum content width on large windows.

#### Scenario: The browser has a minimum width

- **WHEN** the browser region is shown
- **THEN** its width is at least the browser minimum token

#### Scenario: The browser has a maximum width

- **WHEN** the window is wider than the sum of the three regions
- **THEN** the browser does not grow past its maximum token

#### Scenario: The note text is bounded on a large window

- **WHEN** a note is open in a very wide window
- **THEN** its prose and form controls stay within the maximum content width rather than spanning the whole window

#### Scenario: The detail keeps its minimum

- **WHEN** the browser is at its maximum width
- **THEN** the detail region is not narrower than its minimum content width

#### Scenario: No control clips at the minimum window

- **WHEN** the workspace renders at 1024x600 in either mode
- **THEN** no navigation, browser, toolbar, or detail control clips horizontally or vertically
