# Proposal

## Why

The capture loop works, but a capture cannot yet become anything else. The vault also treats `person` as a peer of `reference`, has no storage model for processed work, and has no recoverable deletion path. That makes the next feature guess at the layout and type model instead of extending one that already protects the product's invariants.

This change defines the processing model and the default vault layout together, so later work on the Processing Wizard, views, indexing, and packaging starts from one agreed structure.

## What Changes

- Define a default vault layout: `inbox/`, `trash/`, `reference/` with category folders, `projects/`, and `actions/`.
- Define the processing decision model and its outcomes: Trash, Later, Reference, Action, and Project.
- **BREAKING** Remove `person` as a standalone note type. People become `type: reference` with `category: person`; future categories such as places use the same mechanism. The `person` scheme resolves to reference notes with category `person`, and the `note` scheme covers `note`, `action`, and uncategorized `reference`. One note belongs to exactly one scheme.
- Add the `category` frontmatter key for references and validate it.
- Define project steps as action notes linked by the `project` key. Projects remain flat files; no project subdirectories.
- Add `trash/` as a recoverable deletion location. Trashed notes are excluded from scans, name uniqueness, and reference resolution.
- Define statuses for actions, projects, and references. Remove `inbox` as a status; an unprocessed capture has no status.
- Keep link-driven page creation, the general note editor, processed-note views, the indexer, and packaging out of this change. They are recorded as follow-up phases in the design.

## Capabilities

### New Capabilities

- `processing`: the explicit decision model that turns an inbox capture into a trash, later, reference, action, or project note, including metadata, confirmation, and atomic apply.
- `vault-layout`: the default storage folders, reference category folders, project and action placement, case-insensitive layout resolution, and trash exclusion.
- `reference-categories`: the reference category model, the `category` key, category validation, and the mapping from category to reference scheme.

### Modified Capabilities

- `note-references`: the target rules for the `person` and `note` schemes and the behavior of reference resolution when a category changes.
- `note-identity`: trashed notes are excluded from identity, name uniqueness, and resolution.

## Impact

- **Models:** remove `NoteType.PERSON`; add `ReferenceCategory` and `Status`; parse and validate `category` and `status`.
- **Core:** update scheme mapping, `NameCatalog`, `VaultNote`, scan, and `Vault` creation, move, processing, and trash operations; add processing plan/apply and layout constants.
- **UI:** add the Processing Wizard view and state commands, plus a process action in the Inbox. No processed-note view or indexer yet.
- **Vault format:** breaking. Existing `type: person` notes must become `type: reference` with `category: person`. `status: inbox` is no longer valid because the folder is the queue. The application is source-run only, so no automatic conversion is included; unreadable legacy notes are reported by the scan.
- **Docs:** update `AGENTS.md`, `README.md`, and the affected main specifications.
- **Dependencies and platform:** no new dependencies, no network access, and no platform-specific behavior. Folder matching and trash exclusion follow the existing case-insensitive cross-platform policy.
