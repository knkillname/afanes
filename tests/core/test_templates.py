"""Tests for bundled starter content, its catalog, and its validation."""

import datetime
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.frontmatter
import afanes.core.links
import afanes.core.search
import afanes.core.steps
import afanes.core.templates
import afanes.core.vault
from afanes.core.errors import TemplateContentError, TemplateWriteError, UnknownTemplateError
from afanes.models.note import NoteType, Status

GUIDE_TEXT = "---\ntype: reference\n---\n\n# Getting started\n\nA guide.\n"
PROJECT_TEXT = "---\ntype: project\nstatus: active\n---\n\n# Home\n\n- [ ] Ask [Sam](<note:Sam>)\n"
PERSON_TEXT = "---\ntype: reference\ncategory: person\n---\n\n# Sam\n"
PLACE_TEXT = "---\ntype: reference\ncategory: place\n---\n\n# Garage\n"
CATALOG_SIZE = 3
PERSONAL_NOTE_COUNT = 3
FAILING_WRITE_CALL = 4
CLOSED_STATUSES = frozenset({Status.DONE, Status.CANCELLED, Status.ARCHIVED})


def _write(root: Path, relative: Path, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _guide(root: Path, locale: str = "en") -> None:
    _write(root, Path("_guide") / locale / "reference" / "Getting started.md", GUIDE_TEXT)


def _personal(root: Path, locale: str = "en") -> None:
    base = Path("personal") / locale
    _write(root, base / "projects" / "Home.md", PROJECT_TEXT)
    _write(root, base / "reference" / "person" / "Sam.md", PERSON_TEXT)
    _write(root, base / "reference" / "place" / "Garage.md", PLACE_TEXT)


def _catalog(root: Path) -> afanes.core.templates.TemplateCatalog:
    _guide(root)
    _personal(root)
    return afanes.core.templates.TemplateCatalog.from_root(root)


def _bundle_categories(bundle: afanes.core.templates.TemplateBundle) -> set[str]:
    return {note.category.value.casefold() for note in bundle.notes if note.category is not None}


def _shape(notes: tuple[afanes.core.templates.TemplateNote, ...]) -> tuple[int, int, tuple[int, ...]]:
    projects = [note for note in notes if note.note_type is NoteType.PROJECT]
    references = [note for note in notes if note.note_type is NoteType.REFERENCE]
    steps = tuple(sorted(len(afanes.core.steps.StepDocument(note.document.body).steps) for note in projects))
    return (len(projects), len(references), steps)


def _note_violations(note: afanes.core.templates.TemplateNote) -> list[str]:
    violations: list[str] = []
    if note.note_type is NoteType.NOTE:
        violations.append(f"{note.stem}: capture")
    if note.relative_path.parts[0].casefold() == "inbox":
        violations.append(f"{note.stem}: stored in inbox")
    if note.document.due_date is not None:
        violations.append(f"{note.stem}: due date")
    return violations


def _step_violations(note: afanes.core.templates.TemplateNote) -> list[str]:
    if note.note_type is not NoteType.PROJECT:
        return []
    steps = afanes.core.steps.StepDocument(note.document.body).steps
    violations: list[str] = []
    for step in steps:
        if step.plan is not None:
            violations.append(f"{note.stem}: plan date")
        if step.actual is not None:
            violations.append(f"{note.stem}: actual date")
        if step.owners:
            violations.append(f"{note.stem}: owners")
    status = note.document.status
    if status not in CLOSED_STATUSES and not any(not step.checked for step in steps):
        violations.append(f"{note.stem}: no open step")
    return violations


def _inert_violations(notes: tuple[afanes.core.templates.TemplateNote, ...]) -> list[str]:
    violations: list[str] = []
    for note in notes:
        violations.extend(_note_violations(note))
        violations.extend(_step_violations(note))
    return violations


class TestBundledCatalog:
    def test_catalog_reports_three_templates_in_order(self) -> None:
        catalog = afanes.core.templates.TemplateCatalog.bundled()

        assert catalog.identifiers == ("personal", "work", "study")

    def test_every_entry_carries_a_label_and_description(self) -> None:
        catalog = afanes.core.templates.TemplateCatalog.bundled()

        assert all(template.label for template in catalog.templates)
        assert all(template.description.endswith(".") for template in catalog.templates)

    def test_summaries_report_a_non_zero_note_count(self) -> None:
        summaries = afanes.core.templates.TemplateCatalog.bundled().summaries()

        assert [summary.identifier for summary in summaries] == ["personal", "work", "study"]
        assert all(summary.note_count > 0 for summary in summaries)

    def test_summary_reading_writes_no_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        package = Path(afanes.core.templates.__file__).resolve().parent
        before = sorted(path.as_posix() for path in (package / "templates").rglob("*"))
        monkeypatch.chdir(tmp_path)

        afanes.core.templates.TemplateCatalog.bundled().summaries()

        after = sorted(path.as_posix() for path in (package / "templates").rglob("*"))
        assert after == before
        assert list(tmp_path.iterdir()) == []

    def test_catalog_needs_no_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        summaries = afanes.core.templates.TemplateCatalog.bundled().summaries()

        assert len(summaries) == CATALOG_SIZE

    def test_unknown_identifier_names_the_valid_ones(self) -> None:
        catalog = afanes.core.templates.TemplateCatalog.bundled()

        with pytest.raises(UnknownTemplateError) as info:
            catalog.find("mystery")

        message = str(info.value)
        assert "mystery" in message
        assert "personal" in message
        assert "work" in message
        assert "study" in message


class TestLocaleResolution:
    def test_present_locale_is_preferred(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _guide(root)
        _personal(root)
        _write(root, Path("personal/es/projects/Casa.md"), PROJECT_TEXT.replace("Sam", "Samuel"))
        _write(root, Path("personal/es/reference/person/Samuel.md"), PERSON_TEXT)
        _write(root, Path("personal/es/reference/place/Garaje.md"), PLACE_TEXT)
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        bundle = catalog.bundle("personal", "es")

        assert bundle.locale == "es"
        assert "Casa" in {note.stem for note in bundle.notes}

    def test_missing_locale_falls_back_to_the_base(self, tmp_path: Path) -> None:
        catalog = _catalog(tmp_path / "templates")

        bundle = catalog.bundle("personal", "fr")

        assert bundle.locale == "en"
        assert "Home" in {note.stem for note in bundle.notes}

    def test_identifier_survives_translation(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        catalog = _catalog(root)
        _write(root, Path("personal/es/projects/Casa.md"), PROJECT_TEXT.replace("Sam", "Samuel"))
        _write(root, Path("personal/es/reference/person/Samuel.md"), PERSON_TEXT)
        _write(root, Path("personal/es/reference/place/Garaje.md"), PLACE_TEXT)

        assert catalog.identifiers == ("personal", "work", "study")

    def test_matching_locale_shapes_are_accepted(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        catalog = _catalog(root)
        _write(root, Path("personal/es/projects/Casa.md"), PROJECT_TEXT.replace("Sam", "Samuel"))
        _write(root, Path("personal/es/reference/person/Samuel.md"), PERSON_TEXT)
        _write(root, Path("personal/es/reference/place/Garaje.md"), PLACE_TEXT)

        bundle = catalog.bundle("personal", "en")

        assert len(bundle.notes) == PERSONAL_NOTE_COUNT


class TestBundledTreeValidation:
    def test_malformed_note_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        catalog = _catalog(root)
        _write(root, Path("personal/en/projects/Broken.md"), "---\ntype: project\n")
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "Broken.md" in str(info.value)

    def test_duplicate_stem_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _catalog(root)
        _write(root, Path("personal/en/reference/place/Sam.md"), PLACE_TEXT)
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "share the name" in str(info.value)

    def test_note_without_a_type_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _catalog(root)
        _write(root, Path("personal/en/reference/person/Untyped.md"), "# Untyped\n")
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "declares no type" in str(info.value)

    def test_unsafe_filename_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _catalog(root)
        _write(root, Path("personal/en/projects/Bad: Name.md"), PROJECT_TEXT)
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "cross-platform filename" in str(info.value)

    def test_unresolved_reference_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _catalog(root)
        _write(
            root,
            Path("personal/en/projects/Missing.md"),
            "---\ntype: project\nstatus: active\n---\n\n# Missing\n\n- [ ] Ask [Nobody](<note:Nobody>)\n",
        )
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "Nobody" in str(info.value)

    def test_misplaced_note_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _catalog(root)
        _write(
            root,
            Path("personal/en/reference/person/Misplaced.md"),
            "---\ntype: project\nstatus: active\n---\n\n# Misplaced\n\n- [ ] Call\n",
        )
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "belongs in projects/" in str(info.value)

    def test_capture_in_the_inbox_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _catalog(root)
        _write(root, Path("personal/en/inbox/Capture.md"), GUIDE_TEXT)
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "stored under inbox/" in str(info.value)

    def test_note_under_trash_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _catalog(root)
        _write(root, Path("personal/en/trash/Old.md"), PERSON_TEXT)
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "stored under trash/" in str(info.value)

    def test_capture_note_type_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _catalog(root)
        _write(root, Path("personal/en/projects/Capture.md"), "---\ntype: note\n---\n\n# Capture\n")
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "is a capture" in str(info.value)

    def test_reserved_guide_name_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _catalog(root)
        _write(root, Path("personal/en/reference/Getting started.md"), GUIDE_TEXT)
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "reserved guide name" in str(info.value)

    def test_locale_with_a_missing_project_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        catalog = _catalog(root)
        _write(root, Path("personal/es/reference/person/Samuel.md"), PERSON_TEXT)
        _write(root, Path("personal/es/reference/place/Garaje.md"), PLACE_TEXT)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "does not match the shape" in str(info.value)

    def test_locale_with_a_missing_step_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        catalog = _catalog(root)
        _write(
            root,
            Path("personal/es/projects/Casa.md"),
            "---\ntype: project\nstatus: active\n---\n\n# Casa\n",
        )
        _write(root, Path("personal/es/reference/person/Samuel.md"), PERSON_TEXT)
        _write(root, Path("personal/es/reference/place/Garaje.md"), PLACE_TEXT)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal")

        assert "does not match the shape" in str(info.value)

    def test_guide_without_the_canonical_path_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _write(root, Path("_guide/en/reference/Introduction.md"), GUIDE_TEXT)
        _personal(root)
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle(None)

        assert "Getting started.md" in str(info.value)


class TestBundledContent:
    def test_labels_are_distinct_per_template(self) -> None:
        catalog = afanes.core.templates.TemplateCatalog.bundled()

        assert _bundle_categories(catalog.bundle("personal")) == {"person", "place"}
        assert _bundle_categories(catalog.bundle("work")) == {"team", "process"}
        assert _bundle_categories(catalog.bundle("study")) == {"topic", "source"}

    def test_project_shapes_are_distinct(self) -> None:
        catalog = afanes.core.templates.TemplateCatalog.bundled()

        shapes = {_shape(catalog.bundle(identifier).notes) for identifier in catalog.identifiers}

        assert len(shapes) == CATALOG_SIZE

    def test_guide_is_one_uncategorized_reference(self) -> None:
        bundle = afanes.core.templates.TemplateCatalog.bundled().bundle(None)

        assert len(bundle.guide) == 1
        guide = bundle.guide[0]
        assert guide.relative_path == afanes.core.templates.GUIDE_RELATIVE_PATH
        assert guide.note_type is NoteType.REFERENCE
        assert guide.category is None
        assert guide.document.status is None

    def test_guide_examples_are_not_live_references(self) -> None:
        guide = afanes.core.templates.TemplateCatalog.bundled().bundle(None).guide[0]

        assert afanes.core.links.ReferenceReader().extract(guide.document.body) == []

    @pytest.mark.parametrize(
        "note_text",
        [
            "---\ntype: project\nstatus: active\n---\n\n# Home\n\n- [ ] Call <!-- {plan: 2026-01-05} -->\n",
            "---\ntype: project\nstatus: active\n---\n\n# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n",
            "---\ntype: project\nstatus: active\ndue_date: 2026-01-05\n---\n\n# Home\n\n- [ ] Call\n",
        ],
    )
    def test_inert_helper_detects_a_date_or_an_owner(self, note_text: str) -> None:
        note = afanes.core.templates.TemplateNote(
            relative_path=Path("projects/Home.md"),
            text=note_text,
            document=afanes.core.frontmatter.NoteDocument.from_text(note_text),
        )

        assert _inert_violations((note,)) != []

    @pytest.mark.parametrize("identifier", ["personal", "work", "study"])
    def test_starter_content_creates_no_pending_work(self, identifier: str, tmp_path: Path) -> None:
        creation = afanes.core.vault.Vault.create_directory(tmp_path / "vault", template=identifier)
        snapshot = creation.vault.scan()

        planner = afanes.core.search.ReviewPlanner(snapshot, today=datetime.date(2026, 1, 1))
        assert snapshot.failures == ()
        assert planner.pending_count() == 0

    @pytest.mark.parametrize("identifier", ["personal", "work", "study"])
    def test_starter_content_is_inert(self, identifier: str) -> None:
        catalog = afanes.core.templates.TemplateCatalog.bundled()
        template_root = catalog.root.joinpath(identifier)
        locales = tuple(sorted(child.name for child in template_root.iterdir() if child.is_dir()))
        if not locales:
            locales = (afanes.core.templates.BASE_LOCALE,)

        for locale in locales:
            bundle = catalog.bundle(identifier, locale)
            assert _inert_violations(bundle.ordered_notes) == []


class TestCreationWritesBundledContent:
    def test_blank_creation_writes_only_the_guide(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        creation = afanes.core.vault.Vault.create_directory(root)

        files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
        assert files == ["reference/Getting started.md"]
        assert creation.template is None
        assert creation.written_notes == (root.resolve() / "reference/Getting started.md",)

    def test_templated_creation_writes_the_guide_first(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        creation = afanes.core.vault.Vault.create_directory(root, template="personal")

        relative = [path.relative_to(root).as_posix() for path in creation.written_notes]
        assert creation.template == "personal"
        assert relative[0] == "reference/Getting started.md"
        assert relative[1:] == sorted(relative[1:])

    def test_nested_category_notes_land_in_their_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        afanes.core.vault.Vault.create_directory(root, template="personal")

        assert (root / "reference" / "person" / "Sam Rivera.md").is_file()
        assert (root / "reference" / "place" / "The corner garage.md").is_file()

    def test_written_notes_stay_inside_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        creation = afanes.core.vault.Vault.create_directory(root, template="study")

        assert all(path.is_relative_to(creation.vault.root) for path in creation.written_notes)

    def test_missing_locale_still_creates_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        creation = afanes.core.vault.Vault.create_directory(root, template="work", locale="fr")

        assert creation.template == "work"
        assert (root / "reference" / "Getting started.md").is_file()

    def test_invalid_tree_writes_nothing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        templates_root = tmp_path / "templates"
        _guide(templates_root)
        _write(templates_root, Path("personal/en/projects/Broken.md"), "---\ntype: project\n")
        catalog = afanes.core.templates.TemplateCatalog.from_root(templates_root)
        monkeypatch.setattr(
            afanes.core.templates.TemplateCatalog,
            "bundled",
            classmethod(lambda _cls: catalog),
        )
        target = tmp_path / "vault"

        with pytest.raises(TemplateContentError):
            afanes.core.vault.Vault.create_directory(target, template="personal")

        assert not target.exists()

    def test_invalid_tree_leaves_an_empty_directory_empty(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        templates_root = tmp_path / "templates"
        _guide(templates_root)
        _write(templates_root, Path("personal/en/projects/Broken.md"), "---\ntype: project\n")
        catalog = afanes.core.templates.TemplateCatalog.from_root(templates_root)
        monkeypatch.setattr(
            afanes.core.templates.TemplateCatalog,
            "bundled",
            classmethod(lambda _cls: catalog),
        )
        target = tmp_path / "vault"
        target.mkdir()

        with pytest.raises(TemplateContentError):
            afanes.core.vault.Vault.create_directory(target, template="personal")

        assert list(target.iterdir()) == []

    def test_mid_write_failure_names_the_note_and_the_written_notes(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        original = afanes.core.atomic.write_text_atomic
        calls: list[Path] = []

        def fail_on_fourth(path: Path, text: str) -> None:
            calls.append(path)
            if len(calls) == FAILING_WRITE_CALL:
                message = "disk full"
                raise OSError(message)
            original(path, text)

        monkeypatch.setattr(afanes.core.atomic, "write_text_atomic", fail_on_fourth)
        root = tmp_path / "vault"

        with pytest.raises(TemplateWriteError) as info:
            afanes.core.vault.Vault.create_directory(root, template="personal")

        message = str(info.value)
        assert calls[3].name == "Tax documents.md"
        assert "Tax documents.md" in message
        assert "reference/Getting started.md" in message
        assert (root / "reference" / "Getting started.md").is_file()
        assert (root / "projects" / "Car service.md").is_file()
        assert not (root / "projects" / "Tax documents.md").exists()
