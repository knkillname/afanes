# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bundled starter content and the ordered template catalog.

The module owns one cohesive concern: the Markdown trees shipped inside the
package, the locale layout that holds them, and the rules every tree must satisfy
before any of it is written into a new vault. It reads package resources only
and never writes.
"""

import dataclasses
import datetime
import importlib.resources
import re
from importlib.resources.abc import Traversable
from pathlib import Path

import afanes.core.links
import afanes.core.names
import afanes.core.steps
from afanes.core.errors import AfanesError, TemplateContentError, UnknownTemplateError
from afanes.core.frontmatter import NoteDocument
from afanes.models.note import CategoryLabel, NoteType

# Public base language. A locale without its own tree falls back to this one.
BASE_LOCALE = "en"

# Public package folder that holds every bundled tree.
TEMPLATES_PACKAGE = "templates"

# Public identifier the guide fixture uses. The leading underscore keeps it out
# of the selectable catalog.
GUIDE_IDENTIFIER = "_guide"
GUIDE_STEM = "Getting started"
GUIDE_RELATIVE_PATH = Path("reference") / f"{GUIDE_STEM}.md"

# Public canonical note extension shared with the vault layout.
NOTE_SUFFIX = ".md"

# Public folder names a bundled tree may use. They mirror the canonical vault
# layout; a tree stored anywhere else is refused.
INBOX_DIRECTORY = Path("inbox")
TRASH_DIRECTORY = Path("trash")
REFERENCE_DIRECTORY = Path("reference")
PROJECTS_DIRECTORY = Path("projects")

# Implementation detail: one supported date placeholder and any brace expression
# left after rendering, which is a refused typo.
_DATE_PATTERN = re.compile(r"\{\{\s*date:\s*([+-])(\d{1,3})d\s*\}\}")
_BRACE_PATTERN = re.compile(r"\{\{.*?\}\}", re.DOTALL)


@dataclasses.dataclass(frozen=True, slots=True)
class VaultTemplate:
    """One selectable starter template.

    Attributes
    ----------
    identifier : str
        Stable kebab-case identifier used by the picker and the command line.
    label : str
        Short display name.
    description : str
        One-sentence explanation shown beside the label.
    """

    identifier: str
    label: str
    description: str


# Public fixed catalog, in the order every presentation reports it.
BUNDLED_TEMPLATES: tuple[VaultTemplate, ...] = (
    VaultTemplate(
        identifier="personal",
        label="Personal",
        description="Life administration for the home, the car, and the paperwork that arrives each year.",
    ),
    VaultTemplate(
        identifier="work",
        label="Work",
        description="Shared outcomes, the groups that own them, and the processes that carry them.",
    ),
    VaultTemplate(
        identifier="study",
        label="Study",
        description="Course and research work, with the topics and sources kept beside it.",
    ),
)


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateSummary:
    """Catalog entry with the number of notes its template writes.

    Attributes
    ----------
    identifier : str
        Stable kebab-case identifier.
    label : str
        Short display name.
    description : str
        One-sentence explanation shown beside the label.
    note_count : int
        Number of notes the template writes, excluding the guide note.
    """

    identifier: str
    label: str
    description: str
    note_count: int


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateNote:
    """One bundled note: its vault-relative path, text, and parsed metadata.

    Attributes
    ----------
    relative_path : pathlib.Path
        Path the note takes inside a created vault, relative to the vault root.
    text : str
        Rendered note text, with date placeholders resolved, written as read.
    document : NoteDocument
        Parsed metadata and body used by validation.

    Notes
    -----
    Validation happens before creation, so a ``TemplateNote`` always describes
    content that already parsed. A note in a refused tree never reaches this
    type.
    """

    relative_path: Path
    text: str
    document: NoteDocument

    @property
    def stem(self) -> str:
        """Return the identity stem of this bundled note.

        Returns
        -------
        str
            Filename stem, which is also the note's identity and reference name.
        """
        return self.relative_path.stem

    @property
    def note_type(self) -> NoteType | None:
        """Return the declared note type.

        Returns
        -------
        NoteType | None
            Declared type, or ``None`` when the frontmatter omits it.
        """
        return self.document.note_type

    @property
    def category(self) -> CategoryLabel | None:
        """Return the declared reference category.

        Returns
        -------
        CategoryLabel | None
            Category label, or ``None`` for an uncategorized note.
        """
        return self.document.category


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateBundle:
    """Resolved content one vault creation writes.

    Attributes
    ----------
    template : str | None
        Template identifier, or ``None`` for a creation without starter content.
    locale : str
        Locale the template tree resolved to.
    guide : tuple[TemplateNote, ...]
        Guide notes written into every created vault.
    notes : tuple[TemplateNote, ...]
        Notes declared by the chosen template, empty for a blank creation.
    """

    template: str | None
    locale: str
    guide: tuple[TemplateNote, ...]
    notes: tuple[TemplateNote, ...]

    @property
    def ordered_notes(self) -> tuple[TemplateNote, ...]:
        """Return the notes in creation order.

        Returns
        -------
        tuple[TemplateNote, ...]
            Guide notes first, then the template's notes, each in path order.
        """
        return (*self.guide, *self.notes)


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateCatalog:
    """The fixed template catalog and the trees read from one package folder.

    Parameters
    ----------
    root : importlib.resources.abc.Traversable
        Folder holding ``<template-id>/<locale>/`` trees and the
        ``_guide/<locale>/`` fixture.
    templates : tuple[VaultTemplate, ...]
        Selectable entries in catalog order.

    Notes
    -----
    Use :meth:`bundled` for the installed content. :meth:`from_root` accepts any
    traversable root, which lets tests exercise validation against synthetic
    trees without touching the package.
    """

    root: Traversable
    templates: tuple[VaultTemplate, ...] = BUNDLED_TEMPLATES

    @classmethod
    def bundled(cls) -> "TemplateCatalog":
        """Return the catalog shipped inside the installed package.

        Returns
        -------
        TemplateCatalog
            Catalog rooted at the package's ``templates`` folder.

        Notes
        -----
        Reading uses ``importlib.resources``, so the same code works from a
        source checkout and from an installed wheel. No file is written.
        """
        package = importlib.resources.files("afanes")
        return cls(root=package.joinpath(TEMPLATES_PACKAGE))

    @classmethod
    def from_root(cls, root: Traversable) -> "TemplateCatalog":
        """Return a catalog rooted at an arbitrary traversable folder.

        Parameters
        ----------
        root : importlib.resources.abc.Traversable
            Folder holding the template trees. A filesystem path is accepted.

        Returns
        -------
        TemplateCatalog
            Catalog with the fixed bundled entries.
        """
        return cls(root=root)

    @property
    def identifiers(self) -> tuple[str, ...]:
        """Return every selectable identifier in catalog order.

        Returns
        -------
        tuple[str, ...]
            Kebab-case identifiers.
        """
        return tuple(template.identifier for template in self.templates)

    @classmethod
    def today(cls) -> datetime.date:
        """Return the calendar date creation resolves bundled content against.

        Returns
        -------
        datetime.date
            Current local calendar date.

        Notes
        -----
        This class method is the single time source for rendering and date
        validation. Tests patch it to make a creation deterministic; application
        code never passes a clock object around.
        """
        return datetime.datetime.now(tz=datetime.UTC).astimezone().date()

    @classmethod
    def _render_dates(cls, text: str, today: datetime.date) -> str:
        """Replace every supported date placeholder with an ISO calendar date.

        Parameters
        ----------
        text : str
            Bundled note text as read from the package.
        today : datetime.date
            Calendar date the offsets are measured from.

        Returns
        -------
        str
            Text with each ``{{ date:+Nd }}`` or ``{{ date:-Nd }}`` replaced by
            the corresponding ``YYYY-MM-DD`` date. Other text is unchanged.

        Notes
        -----
        The syntax is intentionally two tokens, not an expression language.
        Callers refuse any brace expression left after this method runs.
        """

        def replace(match: re.Match[str]) -> str:
            sign = match.group(1)
            days = int(match.group(2))
            offset = days if sign == "+" else -days
            return (today + datetime.timedelta(days=offset)).isoformat()

        return _DATE_PATTERN.sub(replace, text)

    def find(self, identifier: str) -> VaultTemplate:
        """Return one catalog entry by identifier.

        Parameters
        ----------
        identifier : str
            Kebab-case identifier. Matching ignores case and surrounding
            whitespace.

        Returns
        -------
        VaultTemplate
            Matching catalog entry.

        Raises
        ------
        UnknownTemplateError
            If no entry matches. The message lists the valid identifiers.
        """
        key = identifier.strip().casefold()
        for template in self.templates:
            if template.identifier.casefold() == key:
                return template
        valid = ", ".join(self.identifiers)
        message = f"Unknown template {identifier!r}; choose one of: {valid}"
        raise UnknownTemplateError(message)

    def summaries(self) -> tuple[TemplateSummary, ...]:
        """Return every catalog entry with the notes it writes.

        Returns
        -------
        tuple[TemplateSummary, ...]
            Entries in catalog order. Each count excludes the guide note.

        Raises
        ------
        TemplateContentError
            If a bundled tree is missing or invalid.

        Notes
        -----
        This method validates every tree it counts, so a broken bundle fails
        here instead of during creation.
        """
        summaries: list[TemplateSummary] = []
        for template in self.templates:
            bundle = self.bundle(template.identifier)
            summaries.append(
                TemplateSummary(
                    identifier=template.identifier,
                    label=template.label,
                    description=template.description,
                    note_count=len(bundle.notes),
                )
            )
        return tuple(summaries)

    def bundle(
        self,
        identifier: str | None,
        locale: str | None = None,
        *,
        today: datetime.date | None = None,
    ) -> TemplateBundle:
        """Resolve, render, and validate the content one creation writes.

        Parameters
        ----------
        identifier : str | None
            Template identifier, or ``None`` to write only the guide note.
        locale : str | None
            Requested locale. ``None`` uses ``BASE_LOCALE``. A locale
            without a tree falls back to the base locale.
        today : datetime.date | None
            Calendar date date placeholders and the date rules are measured
            against. ``None`` uses :meth:`today`.

        Returns
        -------
        TemplateBundle
            Guide notes plus the template's notes, ready to write, with date
            placeholders already resolved.

        Raises
        ------
        UnknownTemplateError
            If ``identifier`` names no catalog entry.
        TemplateContentError
            If the guide or the template tree is missing, does not parse,
            contains an unresolvable placeholder, or violates a vault validity
            rule.
        """
        creation_date = self.today() if today is None else today
        requested = locale or BASE_LOCALE
        guide_root, resolved_locale = self._locale_root(GUIDE_IDENTIFIER, requested)
        guide = self._read_notes(guide_root, creation_date)
        self._validate_guide(guide)
        if identifier is None:
            self._validate_tree("the guide note", guide, creation_date)
            return TemplateBundle(template=None, locale=resolved_locale, guide=guide, notes=())

        template = self.find(identifier)
        template_root, template_locale = self._locale_root(template.identifier, requested)
        notes = self._read_notes(template_root, creation_date)
        subject = f"template {template.identifier!r}"
        self._validate_reserved_name(subject, notes)
        self._validate_tree(subject, (*guide, *notes), creation_date)
        self._validate_locales(template.identifier, creation_date)
        return TemplateBundle(
            template=template.identifier,
            locale=template_locale,
            guide=guide,
            notes=notes,
        )

    def _locale_root(self, identifier: str, locale: str) -> tuple[Traversable, str]:
        """Return the folder for a locale, falling back to the base locale.

        Parameters
        ----------
        identifier : str
            Template identifier or :data:`GUIDE_IDENTIFIER`.
        locale : str
            Requested locale folder name.

        Returns
        -------
        tuple[importlib.resources.abc.Traversable, str]
            Folder to read and the locale it actually represents.

        Raises
        ------
        TemplateContentError
            If neither the requested locale nor the base locale exists.
        """
        base = self.root.joinpath(identifier)
        candidate = base.joinpath(locale)
        if candidate.is_dir():
            return candidate, locale
        fallback = base.joinpath(BASE_LOCALE)
        if fallback.is_dir():
            return fallback, BASE_LOCALE
        message = f"Bundled content for {identifier!r} is missing the {locale!r} and {BASE_LOCALE!r} locales"
        raise TemplateContentError(message)

    @classmethod
    def _read_notes(
        cls,
        root: Traversable,
        today: datetime.date,
        prefix: tuple[str, ...] = (),
    ) -> tuple[TemplateNote, ...]:
        """Read and render every Markdown note under one tree.

        Parameters
        ----------
        root : importlib.resources.abc.Traversable
            Folder to walk.
        today : datetime.date
            Calendar date every date placeholder is measured from.
        prefix : tuple[str, ...]
            Relative path segments accumulated by the recursion.

        Returns
        -------
        tuple[TemplateNote, ...]
            Parsed notes ordered by relative path, with placeholders resolved.

        Raises
        ------
        TemplateContentError
            If a note cannot be read or parsed, or still contains a brace
            expression after rendering.
        """
        notes: list[TemplateNote] = []
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            relative = Path(*prefix, child.name)
            if child.is_dir():
                notes.extend(cls._read_notes(child, today, (*prefix, child.name)))
                continue
            if relative.suffix.casefold() != NOTE_SUFFIX:
                continue
            try:
                text = child.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                message = f"Bundled note {relative.as_posix()!r} cannot be read: {exc}"
                raise TemplateContentError(message) from exc
            rendered = cls._render_dates(text, today)
            if _BRACE_PATTERN.search(rendered):
                message = f"Bundled note {relative.as_posix()!r} has a brace expression that cannot be resolved"
                raise TemplateContentError(message)
            try:
                document = NoteDocument.from_text(rendered)
            except AfanesError as exc:
                message = f"Bundled note {relative.as_posix()!r} cannot be parsed: {exc}"
                raise TemplateContentError(message) from exc
            notes.append(TemplateNote(relative_path=relative, text=rendered, document=document))
        return tuple(notes)

    def _validate_guide(self, guide: tuple[TemplateNote, ...]) -> None:
        """Verify the guide fixture is the one canonical reference note.

        Parameters
        ----------
        guide : tuple[TemplateNote, ...]
            Notes read from the guide tree.

        Raises
        ------
        TemplateContentError
            If the tree does not hold exactly one reference note at the
            canonical guide path.
        """
        if len(guide) != 1:
            self._refuse("the guide note", f"expected exactly one note, found {len(guide)}")
        note = guide[0]
        if note.relative_path != GUIDE_RELATIVE_PATH:
            self._refuse(
                "the guide note",
                f"expected {GUIDE_RELATIVE_PATH.as_posix()!r}, found {note.relative_path.as_posix()!r}",
            )
        if note.note_type is not NoteType.REFERENCE:
            self._refuse("the guide note", "must declare type: reference")
        if note.category is not None:
            self._refuse("the guide note", "must not declare a category")
        if note.document.status is not None:
            self._refuse("the guide note", "must not declare a status")

    def _validate_reserved_name(self, subject: str, notes: tuple[TemplateNote, ...]) -> None:
        """Refuse a template note that claims the guide's name.

        Parameters
        ----------
        subject : str
            Human-readable subject used in failure messages.
        notes : tuple[TemplateNote, ...]
            Template notes, excluding the guide.

        Raises
        ------
        TemplateContentError
            If a template note uses the reserved guide stem.
        """
        reserved = afanes.core.names.normalize_name(GUIDE_STEM)
        for note in notes:
            if afanes.core.names.normalize_name(note.stem) == reserved:
                self._refuse(
                    subject,
                    f"note {note.relative_path.as_posix()!r} uses the reserved guide name {GUIDE_STEM!r}",
                )

    def _validate_tree(
        self,
        subject: str,
        notes: tuple[TemplateNote, ...],
        today: datetime.date,
    ) -> None:
        """Verify that one bundled tree is a valid vault fragment.

        Parameters
        ----------
        subject : str
            Human-readable subject used in failure messages.
        notes : tuple[TemplateNote, ...]
            Notes to validate, including the guide.
        today : datetime.date
            Calendar date the date rules are measured against.

        Raises
        ------
        TemplateContentError
            If a note lacks a type, is a capture, sits under ``inbox/`` or
            ``trash/``, has an unsafe or duplicate name, is in the wrong folder,
            references a name the tree does not contain, or carries a date that
            would create pending work.
        """
        self._validate_notes(subject, notes)
        self._validate_placement(subject, notes)
        self._validate_references(subject, notes)
        self._validate_dates(subject, notes, today)

    def _validate_notes(self, subject: str, notes: tuple[TemplateNote, ...]) -> None:
        """Verify note types, names, and uniqueness.

        Parameters
        ----------
        subject : str
            Human-readable subject used in failure messages.
        notes : tuple[TemplateNote, ...]
            Notes to validate.

        Raises
        ------
        TemplateContentError
            If a rule is violated.
        """
        seen: dict[str, Path] = {}
        for note in notes:
            relative = note.relative_path
            note_type = note.note_type
            if note_type is None:
                self._refuse(subject, f"note {relative.as_posix()!r} declares no type")
            if note_type is NoteType.NOTE:
                self._refuse(
                    subject, f"note {relative.as_posix()!r} is a capture; bundles hold references and projects"
                )
            first = relative.parts[0].casefold()
            if first in {INBOX_DIRECTORY.name.casefold(), TRASH_DIRECTORY.name.casefold()}:
                self._refuse(subject, f"note {relative.as_posix()!r} is stored under {relative.parts[0]}/")
            stem = relative.stem
            if afanes.core.names.safe_filename(stem) != stem:
                self._refuse(subject, f"note {relative.as_posix()!r} is not a cross-platform filename")
            key = afanes.core.names.normalize_name(stem)
            if key in seen:
                earlier = seen[key].as_posix()
                self._refuse(subject, f"notes {earlier!r} and {relative.as_posix()!r} share the name {stem!r}")
            seen[key] = relative

    def _validate_placement(self, subject: str, notes: tuple[TemplateNote, ...]) -> None:
        """Verify each note sits in the folder its type and category select.

        Parameters
        ----------
        subject : str
            Human-readable subject used in failure messages.
        notes : tuple[TemplateNote, ...]
            Notes to validate.

        Raises
        ------
        TemplateContentError
            If a note is misplaced.
        """
        for note in notes:
            expected = self._expected_folder(note)
            actual = tuple(part.casefold() for part in note.relative_path.parent.parts)
            wanted = tuple(part.casefold() for part in expected.parts)
            if actual != wanted:
                self._refuse(
                    subject,
                    f"note {note.relative_path.as_posix()!r} belongs in {expected.as_posix()}/",
                )

    @classmethod
    def _expected_folder(cls, note: TemplateNote) -> Path:
        """Return the canonical folder for one note.

        Parameters
        ----------
        note : TemplateNote
            Note with a validated type.

        Returns
        -------
        pathlib.Path
            Vault-relative folder the note must occupy.
        """
        if note.note_type is NoteType.PROJECT:
            return PROJECTS_DIRECTORY
        category = note.category
        if category is None:
            return REFERENCE_DIRECTORY
        return REFERENCE_DIRECTORY / afanes.core.names.safe_filename(category.value)

    def _validate_references(self, subject: str, notes: tuple[TemplateNote, ...]) -> None:
        """Verify every internal reference resolves to exactly one bundled note.

        Parameters
        ----------
        subject : str
            Human-readable subject used in failure messages.
        notes : tuple[TemplateNote, ...]
            Notes to validate.

        Raises
        ------
        TemplateContentError
            If a reference resolves to no note or to more than one.
        """
        root = Path("bundled")
        entries: list[afanes.core.links.CatalogEntry] = []
        for note in notes:
            note_type = note.note_type
            if note_type is None:
                continue
            entries.append(afanes.core.links.CatalogEntry(path=root / note.relative_path, note_type=note_type))
        catalog = afanes.core.links.NameCatalog.from_entries(entries)
        reader = afanes.core.links.ReferenceReader()
        for note in notes:
            for reference in reader.extract(note.document.body):
                resolution = catalog.resolve(reference)
                if resolution.outcome is not afanes.core.links.ResolutionOutcome.RESOLVED:
                    self._refuse(
                        subject,
                        f"note {note.relative_path.as_posix()!r} references {reference.name!r}, "
                        "which does not resolve to exactly one note in the tree",
                    )

    def _validate_dates(
        self,
        subject: str,
        notes: tuple[TemplateNote, ...],
        today: datetime.date,
    ) -> None:
        """Verify that bundled dates cannot create pending work at creation.

        Parameters
        ----------
        subject : str
            Human-readable subject used in failure messages.
        notes : tuple[TemplateNote, ...]
            Notes to validate, including the guide.
        today : datetime.date
            Creation date the rules are measured against.

        Raises
        ------
        TemplateContentError
            If a project due date or an unchecked step plan date is on or before
            ``today``, if an unchecked step declares an actual date, or if a
            checked step's actual date is after ``today``.
        """
        for note in notes:
            due_date = note.document.due_date
            if due_date is not None and due_date <= today:
                self._refuse(
                    subject,
                    f"note {note.relative_path.as_posix()!r} has a due date on or before {today.isoformat()}",
                )
            if note.note_type is not NoteType.PROJECT:
                continue
            steps = afanes.core.steps.StepDocument(note.document.body).steps
            for step in steps:
                if step.checked:
                    if step.actual is not None and step.actual > today:
                        self._refuse(
                            subject,
                            f"note {note.relative_path.as_posix()!r} has a completed step "
                            f"with an actual date after {today.isoformat()}",
                        )
                    continue
                if step.actual is not None:
                    self._refuse(
                        subject,
                        f"note {note.relative_path.as_posix()!r} has an unchecked step with an actual date",
                    )
                if step.plan is not None and step.plan <= today:
                    self._refuse(
                        subject,
                        f"note {note.relative_path.as_posix()!r} has an open step "
                        f"planned on or before {today.isoformat()}",
                    )

    def _validate_locales(self, identifier: str, today: datetime.date) -> None:
        """Verify every locale tree of one template has the same shape.

        Parameters
        ----------
        identifier : str
            Template identifier.
        today : datetime.date
            Calendar date every date placeholder is measured from.

        Raises
        ------
        TemplateContentError
            If the template has no locale tree or a tree differs from the base
            tree in project count, reference count, or step counts.
        """
        base = self.root.joinpath(identifier)
        locales = tuple(sorted((child for child in base.iterdir() if child.is_dir()), key=lambda item: item.name))
        if not locales:
            message = f"Bundled template {identifier!r} has no locale folder"
            raise TemplateContentError(message)
        reference_root = next((child for child in locales if child.name == BASE_LOCALE), locales[0])
        reference_shape = self._shape(self._read_notes(reference_root, today))
        for locale_root in locales:
            if locale_root is reference_root:
                continue
            shape = self._shape(self._read_notes(locale_root, today))
            if shape != reference_shape:
                message = (
                    f"Bundled template {identifier!r} locale {locale_root.name!r} "
                    "does not match the shape of its base locale"
                )
                raise TemplateContentError(message)

    @classmethod
    def _shape(cls, notes: tuple[TemplateNote, ...]) -> tuple[int, int, tuple[int, ...]]:
        """Return the comparable shape of one locale tree.

        Parameters
        ----------
        notes : tuple[TemplateNote, ...]
            Notes of one locale tree.

        Returns
        -------
        tuple[int, int, tuple[int, ...]]
            Project count, reference count, and sorted per-project step counts.
        """
        projects = [note for note in notes if note.note_type is NoteType.PROJECT]
        references = [note for note in notes if note.note_type is NoteType.REFERENCE]
        steps = tuple(sorted(len(afanes.core.steps.StepDocument(note.document.body).steps) for note in projects))
        return (len(projects), len(references), steps)

    @classmethod
    def _refuse(cls, subject: str, detail: str) -> None:
        """Raise a content error naming the subject and the violated rule.

        Parameters
        ----------
        subject : str
            Human-readable subject used in the message.
        detail : str
            Explanation of the violated rule.

        Raises
        ------
        TemplateContentError
            Always.
        """
        message = f"Bundled {subject} is invalid: {detail}"
        raise TemplateContentError(message)
