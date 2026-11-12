"""Tests for the pure page draft, label rules, and serialization."""

import asyncio
import datetime
import hashlib
from pathlib import Path

import pytest

import afanes.core.settings
import afanes.core.vault.naming
import afanes.ui.state
from afanes.core.editing import DraftMode, NormalDraft, PageDraftFactory, RawDraft
from afanes.core.errors import InvalidReferenceError, NoteParseError, VaultError
from afanes.core.frontmatter import NoteDocument
from afanes.core.labels import DueDateText
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import PageContent, PageFile, ParsedPage, UnparsedPage
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status

PROJECT_NOTE = """---
type: project
status: waiting
due_date: 2026-01-02
custom: keep
---

# Call Ada
Body.
"""

REFERENCE_NOTE = """---
type: reference
category: person
status: archived
custom: keep
---

# Ada, Countess of Lovelace
Mathematician.
"""


def _normal(text: str) -> NormalDraft:
    draft = PageDraftFactory.from_page(_page(text))
    assert isinstance(draft, NormalDraft)
    return draft


def _page(text: str, *, path: Path = Path("/vault/reference/Ada.md")) -> PageContent:
    file = PageFile(
        path=path,
        relative_path=Path(path.name),
        text=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )
    try:
        parsed = NoteDocument.from_text(text)
    except (NoteParseError, InvalidReferenceError) as exc:
        return UnparsedPage(file=file, failure=str(exc))
    if parsed.note_type is None:
        return UnparsedPage(file=file, failure="Note has no type")
    return ParsedPage(file=file, document=parsed)


class TestDueDateText:
    def test_parses_an_iso_date(self) -> None:
        due = DueDateText.from_text("2026-01-02")

        assert due.text == "2026-01-02"
        assert due.date == datetime.date(2026, 1, 2)
        assert due.error is None

    def test_blank_is_absent(self) -> None:
        due = DueDateText.from_text("   ")

        assert due.date is None
        assert due.error is None

    def test_invalid_text_reports_an_error(self) -> None:
        due = DueDateText.from_text("January 2")

        assert due.date is None
        assert due.error is not None

    def test_raw_date_becomes_iso_text(self) -> None:
        assert DueDateText.from_raw(datetime.date(2026, 1, 2)).text == "2026-01-02"

    def test_raw_datetime_keeps_its_text(self) -> None:
        value = datetime.datetime(2026, 1, 2, 3, 4, tzinfo=datetime.UTC)

        assert DueDateText.from_raw(value).text == value.isoformat()

    def test_raw_string_is_preserved(self) -> None:
        assert DueDateText.from_raw("next week").text == "next week"

    def test_absent_value_is_blank(self) -> None:
        assert DueDateText.from_raw(None).text == ""


class TestNewDraft:
    def test_note_reference_creates_an_uncategorized_reference(self) -> None:
        draft = NormalDraft.new(NoteReference(ReferenceScheme.NOTE, "Quarterly budget"))

        assert draft.mode is DraftMode.NORMAL
        assert draft.is_new
        assert draft.identity == "Quarterly budget"
        assert draft.body == "# Quarterly budget\n\n"
        assert draft.labels is not None
        assert draft.labels.note_type is NoteType.REFERENCE
        assert draft.labels.category is None
        assert draft.labels.scheme is ReferenceScheme.NOTE
        assert not draft.is_dirty

    def test_project_reference_creates_a_project(self) -> None:
        draft = NormalDraft.new(NoteReference(ReferenceScheme.PROJECT, "Release 1.0"))

        assert draft.labels is not None
        assert draft.labels.note_type is NoteType.PROJECT
        assert draft.labels.category is None
        assert draft.labels.scheme is ReferenceScheme.PROJECT

    def test_heading_preserves_the_reference_wording(self) -> None:
        draft = NormalDraft.new(NoteReference(ReferenceScheme.NOTE, "Q1: Planning?"))

        assert draft.body.startswith("# Q1: Planning?")
        assert draft.identity == "Q1 Planning"

    def test_body_change_marks_the_draft_dirty(self) -> None:
        draft = NormalDraft.new(NoteReference(ReferenceScheme.NOTE, "Quarterly budget"))

        assert draft.with_body("# Other\n").is_dirty

    def test_label_change_marks_the_draft_dirty(self) -> None:
        draft = NormalDraft.new(NoteReference(ReferenceScheme.NOTE, "Quarterly budget"))
        labels = draft.labels.with_status(Status.LATER)

        assert draft.with_labels(labels).is_dirty


class TestLoadDraft:
    def test_loads_body_and_labels(self) -> None:
        draft = _normal(PROJECT_NOTE)

        assert isinstance(draft, NormalDraft)
        assert draft.labels is not None
        assert draft.labels.note_type is NoteType.PROJECT
        assert draft.labels.status is Status.WAITING
        assert draft.labels.due_date == datetime.date(2026, 1, 2)
        assert draft.body == "\n# Call Ada\nBody.\n"

    def test_loads_a_reference_category(self) -> None:
        draft = _normal(REFERENCE_NOTE)

        assert isinstance(draft, NormalDraft)
        assert draft.labels is not None
        assert draft.labels.category == CategoryLabel("person")
        assert draft.labels.status is Status.ARCHIVED

    def test_loads_a_project_requester(self) -> None:
        draft = _normal("---\ntype: project\nasked_by: Priya Nair\n---\n\nBody\n")

        assert isinstance(draft, NormalDraft)
        assert draft.labels is not None
        assert draft.labels.asked_by_text == "Priya Nair"

    def test_loads_a_note_date(self) -> None:
        draft = _normal("---\ntype: project\ndate: 2025-10-12\n---\n\nBody\n")

        assert isinstance(draft, NormalDraft)
        assert draft.labels is not None
        assert draft.labels.date == NoteDate.from_text("2025-10-12")
        assert draft.labels.date_text == "2025-10-12"

    def test_loads_a_malformed_date_as_text(self) -> None:
        draft = _normal("---\ntype: note\ndate: last Tuesday\n---\n\nBody\n")

        assert isinstance(draft, NormalDraft)
        assert draft.labels is not None
        assert draft.labels.date is None
        assert draft.labels.date_text == "last Tuesday"
        assert draft.labels.date_error is not None

    def test_malformed_note_loads_in_raw_mode(self) -> None:
        draft = PageDraftFactory.from_page(_page("---\ntype: action\n---\n"))

        assert isinstance(draft, RawDraft)
        assert draft.mode is DraftMode.RAW
        assert draft.labels is None

    def test_raw_text_change_marks_the_draft_dirty(self) -> None:
        draft = PageDraftFactory.from_page(_page("---\ntype: action\n---\n"))

        assert isinstance(draft, RawDraft)
        assert draft.with_raw_text("different").is_dirty


class TestLabelRules:
    def test_switching_to_note_clears_category_status_and_due_date(self) -> None:
        draft = _normal(PROJECT_NOTE)
        labels = draft.labels.with_type(NoteType.NOTE)

        assert labels.category is None
        assert labels.status is None
        assert labels.due_date_text == ""
        assert labels.asked_by_text == ""

    def test_switching_to_reference_clears_an_invalid_status_and_due_date(self) -> None:
        draft = _normal(PROJECT_NOTE)
        labels = draft.labels.with_type(NoteType.REFERENCE)

        assert labels.status is None
        assert labels.due_date_text == ""
        assert labels.asked_by_text == ""

    def test_switching_between_project_and_reference_keeps_a_valid_status(self) -> None:
        draft = _normal(REFERENCE_NOTE)
        labels = draft.labels.with_type(NoteType.PROJECT)

        assert labels.status is Status.ARCHIVED
        assert labels.category is None

    def test_invalid_status_for_the_type_is_rejected(self) -> None:
        draft = _normal(REFERENCE_NOTE)

        with pytest.raises(NoteParseError):
            draft.labels.with_status(Status.ACTIVE)

    def test_category_is_ignored_for_a_non_reference(self) -> None:
        draft = _normal(PROJECT_NOTE)
        labels = draft.labels.with_category(CategoryLabel("place"))

        assert labels.category is None

    def test_due_date_is_ignored_for_a_non_project(self) -> None:
        draft = _normal(REFERENCE_NOTE)
        labels = draft.labels.with_due_date_text("2026-01-02")

        assert labels.due_date_text == ""

    def test_invalid_due_date_reports_an_error(self) -> None:
        draft = _normal(PROJECT_NOTE)
        labels = draft.labels.with_due_date_text("January 2")

        assert labels.due_date is None
        assert labels.due_date_error is not None

    def test_requester_text_is_kept_for_projects(self) -> None:
        draft = _normal(PROJECT_NOTE)
        labels = draft.labels.with_asked_by_text("Priya Nair")

        assert labels.asked_by_text == "Priya Nair"

    def test_requester_is_ignored_for_a_non_project(self) -> None:
        draft = _normal(REFERENCE_NOTE)
        labels = draft.labels.with_asked_by_text("Priya Nair")

        assert labels.asked_by_text == ""

    def test_date_is_kept_when_the_type_changes(self) -> None:
        draft = _normal("---\ntype: project\ndate: 2025-10\n---\n\nBody\n")
        labels = draft.labels.with_type(NoteType.NOTE)

        assert labels.date_text == "2025-10"
        assert labels.date == NoteDate.from_text("2025-10")

    def test_date_is_offered_for_every_type(self) -> None:
        draft = _normal(REFERENCE_NOTE)
        labels = draft.labels.with_date_text("2025")

        assert labels.date_text == "2025"

    def test_invalid_date_reports_an_error(self) -> None:
        draft = _normal(PROJECT_NOTE)
        labels = draft.labels.with_date_text("January 2")

        assert labels.date is None
        assert labels.date_error is not None

    def test_switching_to_log_clears_workflow_labels(self) -> None:
        draft = _normal("---\ntype: project\ndate: 2025-10-12\nstatus: active\nasked_by: Priya Nair\n---\n\nBody\n")
        labels = draft.labels.with_type(NoteType.LOG)

        assert labels.note_type is NoteType.LOG
        assert labels.category is None
        assert labels.status is None
        assert labels.due_date_text == ""
        assert labels.asked_by_text == ""
        assert labels.date_text == "2025-10-12"

    def test_switching_from_log_keeps_the_date(self) -> None:
        draft = _normal("---\ntype: log\ndate: 2025-10-12\n---\n\nBody\n")
        labels = draft.labels.with_type(NoteType.REFERENCE)

        assert labels.date_text == "2025-10-12"
        assert labels.category is None


class TestSerialize:
    def test_preserves_unknown_keys_and_updates_owned_labels(self) -> None:
        draft = _normal(PROJECT_NOTE)
        labels = draft.labels.with_status(Status.ACTIVE).with_due_date_text("2027-03-04")
        document = NoteDocument.from_text(draft.with_labels(labels).to_text())

        assert document.note_type is NoteType.PROJECT
        assert document.status is Status.ACTIVE
        assert document.due_date == datetime.date(2027, 3, 4)
        assert document.raw["custom"] == "keep"

    def test_clearing_labels_removes_the_keys(self) -> None:
        draft = _normal(REFERENCE_NOTE)
        labels = draft.labels.with_type(NoteType.NOTE).with_category(None)
        document = NoteDocument.from_text(draft.with_labels(labels).to_text())

        assert "category" not in document.raw
        assert "status" not in document.raw
        assert "due_date" not in document.raw

    def test_writes_and_trims_a_project_requester(self) -> None:
        draft = _normal(PROJECT_NOTE)
        labels = draft.labels.with_asked_by_text("  Priya Nair  ")
        document = NoteDocument.from_text(draft.with_labels(labels).to_text())

        assert document.asked_by == "Priya Nair"
        assert document.raw["asked_by"] == "Priya Nair"
        assert document.raw["custom"] == "keep"
        assert document.body == draft.body

    def test_clearing_the_requester_removes_the_key(self) -> None:
        draft = _normal("---\ntype: project\nasked_by: Priya Nair\ncustom: keep\n---\n\nBody\n")
        labels = draft.labels.with_asked_by_text("")
        document = NoteDocument.from_text(draft.with_labels(labels).to_text())

        assert "asked_by" not in document.raw
        assert document.raw["custom"] == "keep"

    def test_type_change_removes_the_requester(self) -> None:
        draft = _normal("---\ntype: project\nasked_by: Priya Nair\n---\n\nBody\n")
        labels = draft.labels.with_type(NoteType.REFERENCE)
        document = NoteDocument.from_text(draft.with_labels(labels).to_text())

        assert "asked_by" not in document.raw

    def test_requester_write_preserves_crlf(self) -> None:
        text = "---\r\ntype: project\r\n---\r\n\r\n# Call\r\n"
        draft = PageDraftFactory.from_page(_page(text))

        assert isinstance(draft, NormalDraft)
        labels = draft.labels.with_asked_by_text("Priya Nair")
        written = draft.with_labels(labels).to_text()

        assert "asked_by: Priya Nair\r\n" in written
        assert "\n" not in written.replace("\r\n", "")

    def test_invalid_due_date_blocks_serialization(self) -> None:
        draft = _normal(PROJECT_NOTE)

        with pytest.raises(NoteParseError):
            draft.with_labels(draft.labels.with_due_date_text("January 2")).to_text()

    def test_writes_and_removes_the_note_date(self) -> None:
        draft = _normal(PROJECT_NOTE)
        labels = draft.labels.with_date_text("2025-10")
        document = NoteDocument.from_text(draft.with_labels(labels).to_text())

        assert document.date == NoteDate.from_text("2025-10")
        assert document.raw["date"] == "2025-10"

        cleared = draft.with_labels(labels.with_date_text("")).to_text()
        reparsed = NoteDocument.from_text(cleared)
        assert "date" not in reparsed.raw

    def test_invalid_date_blocks_serialization(self) -> None:
        draft = _normal(PROJECT_NOTE)

        with pytest.raises(NoteParseError):
            draft.with_labels(draft.labels.with_date_text("January 2")).to_text()

    def test_preserves_crlf_newlines(self) -> None:
        text = "---\r\ntype: project\r\n---\r\n\r\n# Call\r\n"
        draft = PageDraftFactory.from_page(_page(text))

        assert isinstance(draft, NormalDraft)
        assert "\r\n" in draft.to_text()
        assert "\n" not in draft.to_text().replace("\r\n", "")

    def test_raw_mode_returns_the_text_unchanged(self) -> None:
        text = "---\ntype: action\n---\n# Old\n"
        draft = PageDraftFactory.from_page(_page(text))

        assert isinstance(draft, RawDraft)
        assert draft.to_text() == text

    def test_raw_mode_has_no_labels(self) -> None:
        draft = PageDraftFactory.from_page(_page("---\ntype: action\n---\n"))

        assert draft.labels is None


class TestAfterWrite:
    def test_normal_save_resets_the_baseline(self) -> None:
        draft = _normal(PROJECT_NOTE)
        assert isinstance(draft, NormalDraft)
        edited = draft.with_body("# New\n")
        written = edited.to_text()

        saved = edited.after_write(written, content_hash="hash")

        assert not saved.is_dirty
        assert saved.baseline_hash == "hash"

    def test_display_title_follows_the_body(self) -> None:
        draft = _normal(PROJECT_NOTE)

        assert draft.with_body("# New title\n").display_title == "New title"

    def test_raw_draft_display_title_is_the_identity(self) -> None:
        draft = PageDraftFactory.from_page(_page("---\ntype: action\n---\n"))

        assert draft.display_title == "Ada"

    def test_as_new_clears_the_saved_baseline(self) -> None:
        draft = _normal(PROJECT_NOTE)

        fresh = draft.as_new()

        assert fresh.is_new
        assert fresh.path is None

    def test_new_draft_adopts_its_path(self) -> None:
        draft = NormalDraft.new(NoteReference(ReferenceScheme.PROJECT, "Release 1.0"))
        text = draft.to_text()

        saved = draft.after_write(text, content_hash="hash", path=Path("/vault/projects/Release 1.0.md"))

        assert saved.path == Path("/vault/projects/Release 1.0.md")

    def test_raw_save_that_still_fails_stays_raw(self) -> None:
        draft = PageDraftFactory.from_page(_page("---\ntype: action\n---\n"))
        assert isinstance(draft, RawDraft)

        saved = draft.after_write("---\ntype: action\n---\n", content_hash="hash")

        assert isinstance(saved, RawDraft)

    def test_raw_save_that_parses_upgrades_to_normal(self) -> None:
        draft = PageDraftFactory.from_page(_page("---\ntype: action\n---\n"))
        assert isinstance(draft, RawDraft)

        saved = draft.after_write("---\ntype: project\n---\n# Call\n", content_hash="hash")

        assert isinstance(saved, NormalDraft)
        assert saved.labels is not None
        assert saved.labels.note_type is NoteType.PROJECT

    def test_raw_save_without_a_type_stays_raw(self) -> None:
        draft = PageDraftFactory.from_page(_page("---\ntype: action\n---\n"))
        assert isinstance(draft, RawDraft)

        saved = draft.after_write("# No frontmatter\n", content_hash="hash")

        assert isinstance(saved, RawDraft)


class TestCategoryMoveAndTypeChange:
    def _reference(self, root: Path, relative: str = "reference/Ada.md", category: str | None = None) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["---", "type: reference"]
        if category is not None:
            lines.append(f"category: {category}")
        lines.extend(["---", "", "# Ada"])
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_adding_a_category_moves_the_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = self._reference(root)
        vault = Vault(root)

        preview = afanes.core.vault.naming.VaultNaming(vault).plan_category_move(path, CategoryLabel("place"))
        target = afanes.core.vault.naming.VaultNaming(vault).apply_category_move(preview, confirm=True)

        assert preview.target_path == root / "reference" / "place" / "Ada.md"
        assert target == root / "reference" / "place" / "Ada.md"
        assert target.is_file()
        assert not path.exists()
        assert "category: place" in target.read_text(encoding="utf-8")

    def test_removing_a_category_moves_back_to_the_root(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = self._reference(root, "reference/place/Ada.md", category="place")
        vault = Vault(root)

        preview = afanes.core.vault.naming.VaultNaming(vault).plan_category_move(path, None)
        target = afanes.core.vault.naming.VaultNaming(vault).apply_category_move(preview, confirm=True)

        assert target == root / "reference" / "Ada.md"
        assert "category:" not in target.read_text(encoding="utf-8")

    def test_cancelling_a_category_change_leaves_everything_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = self._reference(root)
        before = path.read_bytes()
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> None:
            await state.workspace.choose_vault(root)
            await state.navigation.open_page(path)
            await state.dialogs.set_page_category(CategoryLabel("place"))
            await state.dialogs.cancel_category_move()

        try:
            asyncio.run(scenario())
        finally:
            state.reset()

        assert path.read_bytes() == before
        assert not (root / "reference" / "place").exists()

    def test_a_failed_move_keeps_the_new_category_in_the_old_folder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = self._reference(root)
        vault = Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_category_move(path, CategoryLabel("place"))

        original_replace = Path.replace

        def fail_replace(self_path: Path, target: Path) -> Path:
            if self_path == path:
                message = "busy"
                raise OSError(message)
            return original_replace(self_path, target)

        monkeypatch.setattr(Path, "replace", fail_replace)
        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(vault).apply_category_move(preview, confirm=True)

        assert path.is_file()
        assert "category: place" in path.read_text(encoding="utf-8")
        assert not (root / "reference" / "place" / "Ada.md").exists()

    def test_type_change_previews_and_cancels_between_project_and_note(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        reference = self._reference(root)
        referrer = root / "notes" / "Ref.md"
        referrer.parent.mkdir()
        referrer.write_text("---\ntype: note\n---\n[Ada](<note:Ada>)\n", encoding="utf-8")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> tuple[bool, bool]:
            await state.workspace.choose_vault(root)
            await state.navigation.open_page(reference)
            applied = await state.dialogs.set_page_type(NoteType.PROJECT)
            pending = state.dialogs.pending_labels is not None
            await state.dialogs.cancel_type_change()
            return applied, pending

        try:
            applied, pending = asyncio.run(scenario())
        finally:
            state.reset()

        assert applied is False
        assert pending is True

    def test_same_scheme_type_change_needs_no_confirmation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        reference = self._reference(root)
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> bool:
            await state.workspace.choose_vault(root)
            await state.navigation.open_page(reference)
            return await state.dialogs.set_page_type(NoteType.NOTE)

        try:
            applied = asyncio.run(scenario())
        finally:
            state.reset()

        assert applied is True
