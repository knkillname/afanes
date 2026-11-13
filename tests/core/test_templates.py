"""Tests for bundled starter content, its catalog, and its validation."""

import datetime
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.frontmatter
import afanes.core.links
import afanes.core.search
import afanes.core.steps
import afanes.core.template_cards
import afanes.core.templates
import afanes.core.vault.service
from afanes.core.errors import (
    TemplateCardContentError,
    TemplateCardWriteError,
    TemplateContentError,
    TemplateWriteError,
    UnknownTemplateError,
)
from afanes.models.note import NoteDate, NoteType, Status
from tests.support import constant

GUIDE_TEXT = "---\ntype: reference\n---\n\n# Getting started\n\nA guide.\n"
PROJECT_TEXT = "---\ntype: project\nstatus: active\n---\n\n# Home\n\n- [ ] Ask [Sam](<note:Sam>)\n"
PERSON_TEXT = "---\ntype: reference\ncategory: person\n---\n\n# Sam\n"
PLACE_TEXT = "---\ntype: reference\ncategory: place\n---\n\n# Garage\n"
CATALOG_SIZE = 3
PERSONAL_NOTE_COUNT = 3
FAILING_WRITE_CALL = 4
CARD_COUNT = 8
CLOSED_STATUSES = frozenset({Status.DONE, Status.CANCELLED, Status.ARCHIVED})
TODAY = datetime.date(2026, 1, 1)


@pytest.fixture
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> datetime.date:
    monkeypatch.setattr(
        afanes.core.templates.TemplateCatalog,
        "today",
        classmethod(constant(TODAY)),
    )
    return TODAY


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


def _project_text(*, frontmatter: str = "", step: str = "- [ ] Call") -> str:
    return f"---\ntype: project\nstatus: active\n{frontmatter}---\n\n# Home\n\n{step}\n"


def _bundle_categories(bundle: afanes.core.templates.TemplateBundle) -> set[str]:
    return {note.category.value.casefold() for note in bundle.notes if note.category is not None}


def _shape(notes: tuple[afanes.core.templates.TemplateNote, ...]) -> tuple[int, int, tuple[int, ...]]:
    projects = [note for note in notes if note.note_type is NoteType.PROJECT]
    references = [note for note in notes if note.note_type is NoteType.REFERENCE]
    steps = tuple(sorted(len(afanes.core.steps.StepDocument(note.document.body).steps) for note in projects))
    return (len(projects), len(references), steps)


def _note_violations(note: afanes.core.templates.TemplateNote, today: datetime.date) -> list[str]:
    violations: list[str] = []
    if note.note_type is NoteType.NOTE:
        violations.append(f"{note.stem}: capture")
    if note.relative_path.parts[0].casefold() == "inbox":
        violations.append(f"{note.stem}: stored in inbox")
    due_date = note.document.due_date
    if due_date is not None and due_date <= today:
        violations.append(f"{note.stem}: due date not in the future")
    return violations


def _step_violations(note: afanes.core.templates.TemplateNote, today: datetime.date) -> list[str]:
    if note.note_type is not NoteType.PROJECT:
        return []
    steps = afanes.core.steps.StepDocument(note.document.body).steps
    violations: list[str] = []
    for step in steps:
        if step.owners:
            violations.append(f"{note.stem}: owners")
        if step.checked:
            if step.actual is not None and step.actual > today:
                violations.append(f"{note.stem}: actual date not in the past")
            continue
        if step.actual is not None:
            violations.append(f"{note.stem}: actual date on an open step")
        if step.plan is not None and step.plan <= today:
            violations.append(f"{note.stem}: plan date not in the future")
    status = note.document.status
    if status not in CLOSED_STATUSES and not any(not step.checked for step in steps):
        violations.append(f"{note.stem}: no open step")
    return violations


def _inert_violations(
    notes: tuple[afanes.core.templates.TemplateNote, ...],
    today: datetime.date,
) -> list[str]:
    violations: list[str] = []
    for note in notes:
        violations.extend(_note_violations(note, today))
        violations.extend(_step_violations(note, today))
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

    def test_bundled_notes_carry_the_creation_date(self, fixed_today: datetime.date) -> None:
        bundle = afanes.core.templates.TemplateCatalog.bundled().bundle(
            "personal",
            today=fixed_today,
        )

        assert all(note.document.date == NoteDate.from_date(fixed_today) for note in bundle.ordered_notes)
        assert all(f"date: {fixed_today.isoformat()}" in note.text for note in bundle.ordered_notes)

    def test_guide_examples_are_not_live_references(self) -> None:
        guide = afanes.core.templates.TemplateCatalog.bundled().bundle(None).guide[0]

        assert afanes.core.links.ReferenceReader().extract(guide.document.body) == []

    def test_guide_explains_the_log_type(self) -> None:
        guide = afanes.core.templates.TemplateCatalog.bundled().bundle(None).guide[0]

        assert "Log entries" in guide.document.body
        assert "log:2025-10-12" in guide.document.body

    @pytest.mark.parametrize(
        "note_text",
        [
            _project_text(frontmatter=f"due_date: {(TODAY - datetime.timedelta(days=1)).isoformat()}\n"),
            _project_text(step=f"- [ ] Call <!-- {{plan: {(TODAY - datetime.timedelta(days=1)).isoformat()}}} -->"),
            _project_text(step=f"- [x] Call <!-- {{actual: {(TODAY + datetime.timedelta(days=1)).isoformat()}}} -->"),
            _project_text(step=f"- [ ] Call <!-- {{actual: {TODAY.isoformat()}}} -->"),
            _project_text(step="- [ ] Call <!-- {owners: [Ada]} -->"),
        ],
    )
    def test_inert_helper_detects_a_violation(self, note_text: str) -> None:
        note = afanes.core.templates.TemplateNote(
            relative_path=Path("projects/Home.md"),
            text=note_text,
            document=afanes.core.frontmatter.NoteDocument.from_text(note_text),
        )

        assert _inert_violations((note,), TODAY) != []

    @pytest.mark.parametrize("identifier", ["personal", "work", "study"])
    def test_starter_content_creates_no_pending_work(
        self,
        identifier: str,
        tmp_path: Path,
        fixed_today: datetime.date,
    ) -> None:
        creation = afanes.core.vault.service.Vault.create_directory(tmp_path / "vault", template=identifier)
        snapshot = creation.vault.scan()

        planner = afanes.core.search.ReviewPlanner(snapshot, today=fixed_today)
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
            bundle = catalog.bundle(identifier, locale, today=TODAY)
            assert _inert_violations(bundle.ordered_notes, TODAY) == []

    @pytest.mark.parametrize("identifier", ["personal", "work", "study"])
    def test_created_notes_contain_no_placeholder(
        self,
        identifier: str,
        tmp_path: Path,
        fixed_today: datetime.date,
    ) -> None:
        assert fixed_today == TODAY
        root = tmp_path / "vault"

        afanes.core.vault.service.Vault.create_directory(root, template=identifier)

        for path in root.rglob("*.md"):
            assert "{{" not in path.read_text(encoding="utf-8"), path

    def test_created_dates_are_concrete_and_future(
        self,
        tmp_path: Path,
        fixed_today: datetime.date,
    ) -> None:
        root = tmp_path / "vault"

        afanes.core.vault.service.Vault.create_directory(root, template="personal")

        document = afanes.core.frontmatter.NoteDocument.from_text(
            (root / "projects" / "Home insurance.md").read_text(encoding="utf-8"),
        )
        assert document.due_date == fixed_today + datetime.timedelta(days=21)
        steps = afanes.core.steps.StepDocument(document.body).steps
        assert steps[1].plan == fixed_today + datetime.timedelta(days=7)
        assert steps[0].actual == fixed_today - datetime.timedelta(days=14)


class TestDateRendering:
    def test_positive_offset_is_applied(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _guide(root)
        _write(
            root,
            Path("personal/en/projects/Home.md"),
            _project_text(
                frontmatter='due_date: "{{ date:+14d }}"\n',
                step='- [ ] Call <!-- {plan: "{{ date:+2d }}"} -->',
            ),
        )
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        bundle = catalog.bundle("personal", today=TODAY)

        note = next(note for note in bundle.notes if note.stem == "Home")
        assert note.document.due_date == TODAY + datetime.timedelta(days=14)
        assert afanes.core.steps.StepDocument(note.document.body).steps[0].plan == TODAY + datetime.timedelta(days=2)

    def test_negative_offset_is_applied(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _guide(root)
        _write(
            root,
            Path("personal/en/projects/Home.md"),
            _project_text(step='- [x] Call <!-- {actual: "{{ date:-2d }}"} -->'),
        )
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        bundle = catalog.bundle("personal", today=TODAY)

        note = next(note for note in bundle.notes if note.stem == "Home")
        steps = afanes.core.steps.StepDocument(note.document.body).steps
        assert steps[0].actual == TODAY - datetime.timedelta(days=2)

    def test_malformed_placeholder_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _guide(root)
        _write(
            root,
            Path("personal/en/projects/Home.md"),
            _project_text(frontmatter='due_date: "{{ date:soon }}"\n'),
        )
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal", today=TODAY)

        assert "brace expression" in str(info.value)

    def test_placeholder_without_a_sign_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        _guide(root)
        _write(
            root,
            Path("personal/en/projects/Home.md"),
            _project_text(step='- [ ] Call <!-- {plan: "{{ date:2d }}"} -->'),
        )
        catalog = afanes.core.templates.TemplateCatalog.from_root(root)

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal", today=TODAY)

        assert "brace expression" in str(info.value)


class TestDateRules:
    def _catalog_with(
        self, tmp_path: Path, *, frontmatter: str = "", step: str = "- [ ] Call"
    ) -> afanes.core.templates.TemplateCatalog:
        root = tmp_path / "templates"
        _guide(root)
        _write(root, Path("personal/en/projects/Home.md"), _project_text(frontmatter=frontmatter, step=step))
        return afanes.core.templates.TemplateCatalog.from_root(root)

    def test_past_due_date_is_refused(self, tmp_path: Path) -> None:
        yesterday = (TODAY - datetime.timedelta(days=1)).isoformat()
        catalog = self._catalog_with(tmp_path, frontmatter=f"due_date: {yesterday}\n")

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal", today=TODAY)

        assert "due date on or before" in str(info.value)

    def test_due_date_today_is_refused(self, tmp_path: Path) -> None:
        catalog = self._catalog_with(tmp_path, frontmatter=f"due_date: {TODAY.isoformat()}\n")

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal", today=TODAY)

        assert "due date on or before" in str(info.value)

    def test_past_plan_date_is_refused(self, tmp_path: Path) -> None:
        yesterday = (TODAY - datetime.timedelta(days=1)).isoformat()
        catalog = self._catalog_with(tmp_path, step=f"- [ ] Call <!-- {{plan: {yesterday}}} -->")

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal", today=TODAY)

        assert "planned on or before" in str(info.value)

    def test_future_actual_date_is_refused(self, tmp_path: Path) -> None:
        tomorrow = (TODAY + datetime.timedelta(days=1)).isoformat()
        catalog = self._catalog_with(tmp_path, step=f"- [x] Call <!-- {{actual: {tomorrow}}} -->")

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal", today=TODAY)

        assert "actual date after" in str(info.value)

    def test_actual_date_on_an_unchecked_step_is_refused(self, tmp_path: Path) -> None:
        yesterday = (TODAY - datetime.timedelta(days=1)).isoformat()
        catalog = self._catalog_with(tmp_path, step=f"- [ ] Call <!-- {{actual: {yesterday}}} -->")

        with pytest.raises(TemplateContentError) as info:
            catalog.bundle("personal", today=TODAY)

        assert "unchecked step with an actual date" in str(info.value)

    def test_future_dates_are_accepted(self, tmp_path: Path) -> None:
        tomorrow = (TODAY + datetime.timedelta(days=1)).isoformat()
        catalog = self._catalog_with(
            tmp_path,
            frontmatter=f"due_date: {tomorrow}\n",
            step=f"- [x] Call <!-- {{actual: {TODAY.isoformat()}}} -->\n- [ ] Done <!-- {{plan: {tomorrow}}} -->",
        )

        bundle = catalog.bundle("personal", today=TODAY)

        note = next(note for note in bundle.notes if note.stem == "Home")
        assert note.document.due_date == TODAY + datetime.timedelta(days=1)


class TestCreationWritesBundledContent:
    def test_blank_creation_writes_the_guide_and_cards(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        creation = afanes.core.vault.service.Vault.create_directory(root)

        files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
        assert files == [
            "afanes.yaml",
            "reference/Getting started.md",
            "templates/daily.md",
            "templates/organization.md",
            "templates/person.md",
            "templates/place.md",
            "templates/process.md",
            "templates/source.md",
            "templates/team.md",
            "templates/topic.md",
        ]
        assert creation.template is None
        assert creation.written_notes == (root.resolve() / "reference/Getting started.md",)
        assert len(creation.written_cards) == CARD_COUNT

    def test_templated_creation_writes_the_guide_first(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        creation = afanes.core.vault.service.Vault.create_directory(root, template="personal")

        relative = [path.relative_to(root).as_posix() for path in creation.written_notes]
        assert creation.template == "personal"
        assert relative[0] == "reference/Getting started.md"
        assert relative[1:] == sorted(relative[1:])

    def test_nested_category_notes_land_in_their_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        afanes.core.vault.service.Vault.create_directory(root, template="personal")

        assert (root / "reference" / "person" / "Sam Rivera.md").is_file()
        assert (root / "reference" / "place" / "The corner garage.md").is_file()

    def test_written_notes_stay_inside_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        creation = afanes.core.vault.service.Vault.create_directory(root, template="study")

        assert all(path.is_relative_to(creation.vault.root) for path in creation.written_notes)

    def test_missing_locale_still_creates_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        creation = afanes.core.vault.service.Vault.create_directory(root, template="work", locale="fr")

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
            classmethod(constant(catalog)),
        )
        target = tmp_path / "vault"

        with pytest.raises(TemplateContentError):
            afanes.core.vault.service.Vault.create_directory(target, template="personal")

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
            classmethod(constant(catalog)),
        )
        target = tmp_path / "vault"
        target.mkdir()

        with pytest.raises(TemplateContentError):
            afanes.core.vault.service.Vault.create_directory(target, template="personal")

        assert list(target.iterdir()) == []

    def test_mid_write_failure_names_the_note_and_the_written_notes(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        original = afanes.core.atomic.AtomicWriter.write_text_atomic
        calls: list[Path] = []

        def fail_on_fourth(path: Path, text: str) -> None:
            calls.append(path)
            if len(calls) == FAILING_WRITE_CALL:
                message = "disk full"
                raise OSError(message)
            original(path, text)

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", fail_on_fourth)
        root = tmp_path / "vault"

        with pytest.raises(TemplateWriteError) as info:
            afanes.core.vault.service.Vault.create_directory(root, template="personal")

        message = str(info.value)
        assert calls[3].name == "Monthly budget.md"
        assert "Monthly budget.md" in message
        assert "reference/Getting started.md" in message
        assert (root / "reference" / "Getting started.md").is_file()
        assert (root / "projects" / "Car service.md").is_file()
        assert not (root / "projects" / "Monthly budget.md").exists()


class TestTemplateCardSeeding:
    def test_a_templated_vault_also_writes_the_seven_cards(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"

        creation = afanes.core.vault.service.Vault.create_directory(root, template="personal")

        assert len(creation.written_cards) == CARD_COUNT
        snapshot = creation.vault.scan()
        assert "Person" not in {note.name for note in snapshot.notes}
        assert snapshot.failures == ()

    def test_a_card_can_be_edited_after_creation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        afanes.core.vault.service.Vault.create_directory(root)
        card = root / "templates" / "person.md"
        card.write_text(
            "---\ntype: reference\ncategory: person\ntitle: Contact\ndescription: A person.\n---\n\n## Details\n",
            encoding="utf-8",
        )

        listing = afanes.core.template_cards.TemplateCardCatalog.from_root(root / "templates").load()

        assert [item.title for item in listing.cards if item.relative_path.name == "person.md"] == ["Contact"]

    def test_a_deleted_card_is_not_restored(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        creation = afanes.core.vault.service.Vault.create_directory(root)
        card = root / "templates" / "person.md"
        card.unlink()

        creation.vault.scan()
        listing = afanes.core.template_cards.TemplateCardCatalog.from_root(root / "templates").load()

        assert not card.exists()
        assert [item.relative_path.name for item in listing.cards].count("person.md") == 0

    def test_a_broken_bundled_card_writes_nothing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cards_root = tmp_path / "template_cards"
        _write(cards_root, Path("broken.md"), "---\ntype: reference\n---\n")
        catalog = afanes.core.template_cards.TemplateCardCatalog.from_root(cards_root)
        monkeypatch.setattr(
            afanes.core.template_cards.TemplateCardCatalog,
            "bundled",
            classmethod(constant(catalog)),
        )
        target = tmp_path / "vault"

        with pytest.raises(TemplateCardContentError):
            afanes.core.vault.service.Vault.create_directory(target)

        assert not target.exists()

    def test_a_mid_write_card_failure_names_the_card_and_the_written_cards(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        original = afanes.core.atomic.AtomicWriter.write_text_atomic
        calls: list[Path] = []

        def fail_on_fourth(path: Path, text: str) -> None:
            calls.append(path)
            if len(calls) == FAILING_WRITE_CALL:
                message = "disk full"
                raise OSError(message)
            original(path, text)

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", fail_on_fourth)
        root = tmp_path / "vault"

        with pytest.raises(TemplateCardWriteError) as info:
            afanes.core.vault.service.Vault.create_directory(root)

        message = str(info.value)
        assert calls[3].name == "person.md"
        assert "person.md" in message
        assert "templates/organization.md" in message
        assert (root / "reference" / "Getting started.md").is_file()
        assert (root / "templates" / "daily.md").is_file()
        assert (root / "templates" / "organization.md").is_file()
        assert not (root / "templates" / "person.md").exists()
        assert afanes.core.vault.service.Vault(root).scan().failures == ()
