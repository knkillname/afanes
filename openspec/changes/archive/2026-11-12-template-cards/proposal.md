# Proposal

## Why

Processing a capture into a reference can only create an uncategorized reference. The user cannot say that a capture is about a person, a place, or a process, and nothing helps fill the note afterwards. Reference categories exist, but no creation flow uses them, and the browser has no way to create a reference from a reusable shape.

This change introduces reference template cards: user-editable Markdown files in a vault `templates/` folder that supply a category and a starter body. The Processing Wizard and the browser's References section both offer the cards, plus an Empty option.

## What Changes

- Add a vault `templates/` folder holding reference template cards. It is not a note folder: scans, the browser, name uniqueness, and reference resolution ignore it.
- Define the template card format: a Markdown file with `type: reference`, `category`, `title`, and `description` in frontmatter, plus a starter body that begins at `##`.
- Seed seven editable default cards in every new vault: Person, Team, Organization, Place, Process, Topic, Source.
- Let users add, edit, or delete cards with any text editor. There is no in-app template editor.
- Processing: Reference and Later ask for a template card. The card supplies the category and starter body. Empty creates a `general` reference with no starter body.
- Processing: append the starter body below the capture text, preserve the capture text and unknown keys, and keep the success panel. Processing never opens the page editor.
- Browser: add a New action to the References section. The dialog asks for a name and a template card (or Empty), writes immediately, and opens the note in edit mode.
- Invalid user-added cards are skipped and named in a warning; valid cards remain usable.
- Starter bodies are creation-time content only. Changing a category later moves the note without inserting or repairing a starter body.

## Capabilities

### New Capabilities

- `template-cards`: the vault `templates/` folder, the card format, the seeded defaults, validation, the card picker, and the creation rules shared by processing and the browser.

### Modified Capabilities

- `processing`: Reference and Later accept a template card; the card supplies the category and starter body; Empty uses `general` with no starter body; processing finishes without opening the page editor.
- `vault-browsing`: the References section offers a New action, its dialog, immediate creation, and opening the new note in edit mode.
- `vault-layout`: `templates/` is a reserved, non-note folder excluded from scans, the browser, name uniqueness, and reference resolution.
- `vault-templates`: vault creation seeds the seven template cards alongside the guide note and the chosen starter content.

## Impact

- Core: a template card catalog and validator, vault creation seeding, scan exclusion, and processing plan changes.
- UI: Processing Wizard template picker and preview; References New action and dialog; navigation creation command; no new `AppState` field.
- Vault: a new `templates/` convention and seven seeded files. **BREAKING**: an existing vault that already uses a `templates/` folder for ordinary notes will stop showing those notes in the browser.
- Docs: processing, references, vault layout, vault templates, and a new template cards reference page.
- Tests: card parsing and validation, seeding, scan exclusion, processing plans and views, browser creation flow, and documentation style.
- Dependencies: none. No network, telemetry, or cloud behavior.
