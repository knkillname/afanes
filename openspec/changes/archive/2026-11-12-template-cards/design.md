# Design

## Context

See `proposal.md` for motivation. Two existing behaviors shape this design:

- Processing already writes a classified note and then moves it out of `inbox/`. Reference and Later are the only outcomes that create a `type: reference` note, and the current plan has no category.
- The browser is read-only. Pages are created only by following a missing link, which opens an unsaved draft. There is no New action.

The vault layout already reserves `trash/` as a non-note folder and matches it case-insensitively. The scanner has no persistent index; every scan walks the vault. The `AppState` facade is at its ten-field limit, so the new flow must live in existing controllers.

## Goals / Non-Goals

**Goals:**

- Reference template cards are visible, portable Markdown files in the vault.
- Users add, edit, or delete cards with any text editor.
- Processing and the browser share one card picker, with Empty as the no-card choice.
- Processing stays a queue flow: it writes the card content and ends in the success state.
- Browser creation writes immediately and opens the new note in edit mode.
- The card catalog is read without a vault where possible, and no index or marker is added.

**Non-Goals:**

- An in-app template editor or a persistent template gallery.
- CLI commands for listing or creating cards.
- Nested template folders.
- Localized default cards.
- Seeding cards into existing vaults or restoring deleted ones.
- Applying cards on category changes, link-created drafts, or note opening.
- Changing the Personal/Work/Study starter-template catalog.

## Decisions

### Vault folder: `templates/` at the vault root

The cards live in a visible `templates/` folder at the vault root. The folder is excluded from scans, the browser, name uniqueness, and reference resolution, and its name is matched case-insensitively like `trash/`.

Alternatives considered:

- `reference/templates/` would make cards ordinary references, pollute the reference name space, and appear in the browser.
- A hidden `.afanes/templates/` folder would be portable but hard to find; the user chose a visible folder.
- Keeping the cards bundled only would prevent user-defined cards.

The chosen name comes with a real hazard: a vault that already uses `templates/` for ordinary notes will stop showing those notes. This is recorded as a breaking change in the proposal and must be called out in the release notes and docs.

`Vault` gains a `templates_directory()` lookup that reuses the existing case-insensitive directory helper and never creates the folder. The scanner skips the folder through a new `TEMPLATES_DIRECTORY` constant in `core/vault/snapshot.py`, next to the existing directory constants.

### Card format: a reference note with metadata and a body fragment

A card is a Markdown file whose frontmatter declares `type: reference` and `category`, and may declare `title` and `description`. The Markdown after the frontmatter is the starter body.

```markdown
---
type: reference
category: person
title: Person
description: A contact, colleague, or someone you deal with.
---

## Contact

- Email:
- Phone:
```

The parser reuses `NoteDocument.from_text`:

- `type` and `category` are validated by the existing note model.
- `title` and `description` are unknown keys and are read from the raw mapping.
- `title` falls back to the file stem and `description` may be empty.
- `status` and `due_date` are refused to keep the card from carrying workflow state.
- The body must not contain a level-1 heading; the new note's title is supplied by the user.
- The body may be empty. An empty body is a categorized reference with no starter content.
- Task-list items are allowed in a reference body and remain plain Markdown; they do not create review work.

Alternatives considered:

- Filename plus first heading would mix picker metadata into the note body and require stripping the heading and description.
- A sidecar YAML file would be more explicit but adds a second file to keep in sync.
- A custom parser that does not reuse the note model would duplicate category and type validation.

The new `core/template_cards.py` module owns a `TemplateCard` value object, a `TemplateCardIssue` value object, and a `TemplateCardCatalog` service. The catalog reads either a `Traversable` root (the bundled cards) or a filesystem folder (the vault cards). It returns valid cards plus issues; it does not raise for one bad user card. The bundled defaults are validated strictly and raise a domain error before any write.

Cards are ordered by title and then by relative path, so the picker is deterministic and duplicate titles stay distinguishable.

### Seeded defaults: seven cards written at vault creation

Every new vault receives seven cards: Person, Team, Organization, Place, Process, Topic, and Source. The contents are bundled under `src/afanes/template_cards/` and copied into the vault by `Vault.create_directory`. They are ordinary files afterwards; deleting or editing one is never undone.

| File | Category | Title | Description |
| --- | --- | --- | --- |
| `person.md` | `person` | Person | A contact, colleague, or someone you deal with. |
| `team.md` | `team` | Team | A group you work with, and the people in it. |
| `organization.md` | `organization` | Organization | A company, institution, or other body you deal with. |
| `place.md` | `place` | Place | A physical location, with the details you need to visit. |
| `process.md` | `process` | Process | A repeatable procedure, kept as a reference. |
| `topic.md` | `topic` | Topic | A subject you are tracking, learning, or thinking about. |
| `source.md` | `source` | Source | A book, article, course, or other material you refer back to. |

Starter bodies:

```markdown
<!-- person.md -->
## Contact

- Email:
- Phone:
```

```markdown
<!-- team.md -->
## Contact

- Email:
- Chat:

## Members
```

```markdown
<!-- organization.md -->
## Contact

- Website:
- Email:
- Phone:

## Address
```

```markdown
<!-- place.md -->
## Address

## Hours

## Access
```

```markdown
<!-- process.md -->
## Steps
```

```markdown
<!-- topic.md -->
## Key points

## Open questions
```

```markdown
<!-- source.md -->
## Citation

## Link

## Key points
```

The bundled catalog is read and validated before the vault directory is created, following the existing rule for bundled starter content. Cards are written after the guide and the chosen starter template's notes, so a card failure leaves the earlier content and reports the failing card and the cards already written. `VaultCreation` gains `written_cards`; it remains distinct from `written_notes`.

Default cards are English only. Unlike the vault starter templates, they have no locale tree. Users who want another language edit or add cards. This keeps the first version small and the folder fully user-controlled.

### Shared picker: one catalog, two presentation flows

`VaultSession` gains an async command that reads `Vault.templates_directory()` in a worker thread and returns the valid cards and issues. A missing folder returns no cards and no issues. An unreadable folder returns an issue and no cards.

- **Processing:** `ProcessingState.begin` loads the catalog and retains the summaries. The wizard shows a Template dropdown with the valid cards and Empty, a description line, and a category/starter-body preview. `build_plan` passes the selected `TemplateCard` or `None` to the core.
- **Browser:** the References section gets a New button. `AfanesApp` reads the same catalog and shows a dialog with a name field, the Template dropdown, a description, and an invalid-card warning. Create calls `PageNavigator.create_reference`.

The picker shows the card title and description. When two cards share a title, the relative path is shown as the subtitle. The Empty option is always present and always the last option.

### Processing plan: category and scaffold are captured in the plan

`ProcessingPlan` gains `category: CategoryLabel | None` and `scaffold: str | None`. `VaultProcessing.plan_processing` accepts an optional `TemplateCard`.

- Reference and Later always receive a category: the card's category or `general` for Empty.
- The scaffold is the card's body when it is non-empty; Empty has no scaffold.
- Project, Done now, Trash, and Append step reject a card and carry no category or scaffold.
- The destination uses `Vault.directory_for(NoteType.REFERENCE, category)`, so the category folder is reused case-insensitively.
- The existing name-scheme and destination collision checks are unchanged.
- `processed_text` sets `category` in the frontmatter and appends the scaffold after the capture text. The scaffold is normalized to the document's newline style; the capture text remains a prefix. The processed hash covers the final text.
- The plan captures the card content it previewed. A card edited or deleted after planning does not change the plan; the user confirms the snapshot. A card that cannot be read at plan time aborts before any write.

Processing apply is otherwise unchanged. It has no page navigation and no edit-mode call. The success panel stays, and the review flow can record the item and advance.

### Browser creation: write immediately, then edit

`PageNavigator` gains `create_reference(name, category, scaffold)`:

1. Commit the open page, using the same guard as opening a new draft.
2. Build the body from the display name and the scaffold, and call `VaultPages.create_page(name, NoteType.REFERENCE, category, body=body)` in a worker thread. This uses the exact name and the atomic write, and it rejects collisions without adding a suffix.
3. Scan the vault, apply the snapshot, and clear the browser query.
4. Load the new page with `PageEditorState.load(path, editing=True)` and push the previous page onto the history.

`PageEditorState.load` gains an `editing` flag defaulting to `False`, so existing callers keep their behavior. The new note opens in edit mode, ready for the starter body.

The dialog lives in the app shell as a local form, following the existing New vault dialog pattern. It holds no new `AppState` field. The New button is built by `WorkspaceView` in the References section and disabled while a command is running.

If the write succeeds but the scan or page load fails, the note remains. The dialog closes and the app reports the refresh or open failure; the user can refresh and open the note manually.

### Invalid cards: report, do not hide

A user card that cannot be read, parsed, or validated becomes a `TemplateCardIssue` with its relative path and a short message. The catalog returns the valid cards and every issue. Both pickers name the invalid files in a warning and keep the valid cards usable. The files are never modified automatically.

A bundled default card that is invalid is a packaging failure: vault creation refuses before creating the directory. This matches the existing treatment of broken vault starter content.

### Spec boundaries

`template-cards` owns the folder, format, seeded defaults, validation, picker, Empty semantics, and creation rules. `processing` owns how the wizard uses a card. `vault-browsing` owns the New action and immediate creation. `vault-layout` owns the scan exclusion. `vault-templates` owns the fact that creation also writes the cards. The card concept is not added to `vault-templates`, because that capability is about whole-vault starter content, not per-note shapes.

## Risks / Trade-offs

- **An existing `templates/` folder with notes becomes invisible** → call it out as a breaking change in the release notes and docs; the picker reports those files as invalid cards, which surfaces the mistake. A future startup warning could improve this, but it is not part of this change.
- **Users put ordinary notes in `templates/`** → the folder is documented as reserved, and invalid files are named by the picker.
- **No in-app editor** → the folder is visible and portable; users edit with any text editor. A template editor remains a future capability.
- **Default cards are English only** → users can edit them or add localized cards; a locale-scoped card set is a future extension.
- **A card can change after planning** → the plan keeps the previewed snapshot. This is deliberate: the preview is the confirmation, and revalidating the card at apply would add a second moving part to a flow that must stay quick.
- **Processing does not open the note** → the starter body is written but the user must open it later. This is intentional: finishing the queue and review flow has priority, and the preview already shows what was added.
- **The `AppState` field limit** → no new facade field is introduced; the catalog read lives on `VaultSession`, the creation command on `PageNavigator`, and the picker summaries on `ProcessingState`.
- **Template-card file names are not identity** → the picker identifies a card by its relative path, not its title. Duplicate titles are allowed and distinguishable.

## Migration Plan

- Existing vaults are not seeded and are not modified on open. Their pickers offer Empty until the user adds cards. The docs explain how to copy the seven defaults from a new vault or create a card by hand.
- Upgrading is breaking only for a vault that already has a `templates/` folder with ordinary notes; those notes leave the browser because the folder is now reserved. The release notes and docs must state this clearly.
- Rollback is file-only: remove the exclusion and the picker code, and the cards remain ordinary files. No index, database, or settings migration exists.
- No network, telemetry, or new dependency is involved.

## Open Questions

None that change the specs, the approach, or the task breakdown. Deferrable items are listed as non-goals: an in-app editor or gallery, CLI commands, nested folders, localized defaults, and seeding existing vaults.
