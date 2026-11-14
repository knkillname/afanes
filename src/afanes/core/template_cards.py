# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reference and log template cards stored in a vault ``templates/`` folder.

A template card is a Markdown file whose frontmatter declares its note type and
whose body is a starter fragment. Reference cards also declare a category; log
cards do not. The catalog reads either the bundled defaults shipped inside the
package or the cards found in a vault folder. Reading never writes and never
raises for a single invalid user card; the caller receives every valid card plus
an issue for each refused file.
"""

import dataclasses
import importlib.resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Self

from markdown_it import MarkdownIt

from afanes.core.errors import AfanesError, DomainMessage, MessageCode, TemplateCardContentError
from afanes.core.frontmatter import NoteDocument
from afanes.models.note import CategoryLabel, NoteType

# Public package folder that holds the bundled card locale folders.
TEMPLATE_CARDS_PACKAGE = "template_cards"

# Public base language. A locale without its own card set falls back to this one.
BASE_LOCALE = "en"

# Public canonical card extension shared with the vault layout.
NOTE_SUFFIX = ".md"


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateCard:
    """One validated reference or log template card.

    Attributes
    ----------
    relative_path : pathlib.Path
        Card path relative to the ``templates/`` folder, used as a stable
        identity and to distinguish duplicate titles.
    note_type : NoteType
        Note type the card creates: ``reference`` or ``log``.
    category : CategoryLabel | None
        Reference category applied to a note created from this card, or
        ``None`` for a log card.
    title : str
        Display title shown in the pickers.
    description : str | None
        One-line explanation, or ``None`` when the card omits or blanks it.
    body : str
        Starter body appended to a created note, normalized to LF and stripped
        of surrounding newlines. Empty when the card declares no body.
    text : str
        Complete card source, written verbatim when the card is copied into a
        new vault.
    """

    relative_path: Path
    note_type: NoteType
    category: CategoryLabel | None
    title: str
    description: str | None
    body: str
    text: str


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateCardIssue:
    """A card file that could not be read, parsed, or validated.

    Attributes
    ----------
    relative_path : pathlib.Path
        Card path relative to the ``templates/`` folder.
    message : DomainMessage
        Stable explanation of the violated rule.
    """

    relative_path: Path
    message: DomainMessage


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateCardListing:
    """Result of reading one template card folder.

    Attributes
    ----------
    cards : tuple[TemplateCard, ...]
        Valid cards ordered by title and then by relative path.
    issues : tuple[TemplateCardIssue, ...]
        Refused files ordered by relative path. Empty when every file is valid.
    """

    cards: tuple[TemplateCard, ...]
    issues: tuple[TemplateCardIssue, ...]

    def for_type(self, note_type: NoteType) -> tuple[TemplateCard, ...]:
        """Return the valid cards that create one note type.

        Parameters
        ----------
        note_type : NoteType
            Target type to filter by.

        Returns
        -------
        tuple[TemplateCard, ...]
            Cards whose :attr:`TemplateCard.note_type` matches, in listing
            order.
        """
        return tuple(card for card in self.cards if card.note_type is note_type)


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateCardCatalog:
    """Read reference template cards from one folder.

    Parameters
    ----------
    root : importlib.resources.abc.Traversable
        Folder holding card files. A filesystem path is accepted.
    base_root : importlib.resources.abc.Traversable | None
        English card folder a localized catalog must match, or ``None`` for a
        base or user catalog.

    Notes
    -----
    Use :meth:`bundled` for the installed defaults and :meth:`from_root` for a
    vault folder or a synthetic tree. Reading performs blocking file I/O but
    never writes, and a missing folder is an empty catalog rather than an
    error.
    """

    root: Traversable
    base_root: Traversable | None = None

    @classmethod
    def bundled(cls, locale: str | None = None) -> Self:
        """Return the catalog shipped inside the installed package.

        Parameters
        ----------
        locale : str | None
            Requested locale. ``None`` uses the base locale, and a locale
            without a card set falls back to the base cards.

        Returns
        -------
        TemplateCardCatalog
            Catalog rooted at the matching locale folder. A localized catalog
            remembers the English folder so :meth:`strict_cards` can compare
            the two sets.
        """
        package = importlib.resources.files("afanes").joinpath(TEMPLATE_CARDS_PACKAGE)
        base = package.joinpath(BASE_LOCALE)
        requested = BASE_LOCALE if locale is None else locale
        if requested == BASE_LOCALE:
            return cls(root=base)
        candidate = package.joinpath(requested)
        if not candidate.is_dir():
            return cls(root=base)
        return cls(root=candidate, base_root=base)

    @classmethod
    def from_root(cls, root: Traversable) -> Self:
        """Return a catalog rooted at an arbitrary traversable folder.

        Parameters
        ----------
        root : importlib.resources.abc.Traversable
            Folder holding card files. A filesystem path is accepted.

        Returns
        -------
        TemplateCardCatalog
            Catalog rooted at ``root``.
        """
        return cls(root=root)

    def load(self) -> TemplateCardListing:
        """Read every card in the folder without raising for one bad file.

        Returns
        -------
        TemplateCardListing
            Valid cards plus an issue for each refused file. A missing folder
            yields an empty listing, and an unreadable folder yields one issue.
        """
        try:
            if not self.root.is_dir():
                return TemplateCardListing(cards=(), issues=())
            children = sorted(self.root.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            issue = TemplateCardIssue(
                relative_path=Path(self.root.name),
                message=DomainMessage.of(MessageCode.CARD_FOLDER_READ_FAILED, detail=str(exc)),
            )
            return TemplateCardListing(cards=(), issues=(issue,))

        cards: list[TemplateCard] = []
        issues: list[TemplateCardIssue] = []
        for child in children:
            relative = Path(child.name)
            if relative.suffix.casefold() != NOTE_SUFFIX:
                continue
            try:
                if child.is_dir() or not child.is_file():
                    continue
                text = child.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                issues.append(
                    TemplateCardIssue(
                        relative_path=relative,
                        message=DomainMessage.of(
                            MessageCode.CARD_READ_FAILED,
                            path=relative.as_posix(),
                            detail=str(exc),
                        ),
                    )
                )
                continue
            try:
                cards.append(self.parse(relative, text))
            except AfanesError as exc:
                problem = exc.domain_message
                if problem is None:
                    problem = DomainMessage.of(MessageCode.CARD_READ_FAILED, path=relative.as_posix(), detail=str(exc))
                issues.append(TemplateCardIssue(relative_path=relative, message=problem))

        cards.sort(key=lambda card: (card.title.casefold(), card.relative_path.as_posix()))
        return TemplateCardListing(cards=tuple(cards), issues=tuple(issues))

    def strict_cards(self) -> tuple[TemplateCard, ...]:
        """Read every bundled card and refuse any invalid or missing content.

        Returns
        -------
        tuple[TemplateCard, ...]
            Valid cards ordered by title and then by relative path.

        Raises
        ------
        TemplateCardContentError
            If the folder holds no cards, or any file cannot be read or
            validated. The message names the offending file.
        """
        listing = self.load()
        if listing.issues:
            issue = listing.issues[0]
            raise TemplateCardContentError(issue.message)
        if not listing.cards:
            message = DomainMessage.of(MessageCode.CARDS_MISSING)
            raise TemplateCardContentError(message)
        if self.base_root is not None:
            self._validate_localized(listing.cards)
        return listing.cards

    def _validate_localized(self, cards: tuple[TemplateCard, ...]) -> None:
        """Verify a localized set matches the English filenames, types, and categories.

        Parameters
        ----------
        cards : tuple[TemplateCard, ...]
            Valid cards read from the localized folder.

        Raises
        ------
        TemplateCardContentError
            If a filename is missing or extra, or a matching filename changes
            its type or category.
        """
        base_root = self.base_root
        if base_root is None:
            return
        base = TemplateCardCatalog(root=base_root).strict_cards()
        base_by_name = {card.relative_path.name: card for card in base}
        localized_by_name = {card.relative_path.name: card for card in cards}
        missing = sorted(set(base_by_name) - set(localized_by_name))
        extra = sorted(set(localized_by_name) - set(base_by_name))
        mismatched = sorted(
            name
            for name in set(base_by_name) & set(localized_by_name)
            if (base_by_name[name].note_type, base_by_name[name].category)
            != (localized_by_name[name].note_type, localized_by_name[name].category)
        )
        if not missing and not extra and not mismatched:
            return
        detail = f"missing={missing}, extra={extra}, mismatched={mismatched}"
        message = DomainMessage.of(MessageCode.CARD_LOCALE_SHAPE, detail=detail)
        raise TemplateCardContentError(message)

    @classmethod
    def parse(cls, relative_path: Path, text: str) -> TemplateCard:
        """Validate one card source and build its value object.

        Parameters
        ----------
        relative_path : pathlib.Path
            Card path relative to the ``templates/`` folder.
        text : str
            Complete card source, including its frontmatter.

        Returns
        -------
        TemplateCard
            Validated card with its title, description, and starter body.

        Raises
        ------
        TemplateCardContentError
            If the frontmatter cannot be parsed, the type is not ``reference``
            or ``log``, a reference category is missing, a log card declares a
            category, workflow keys are present, the title or description has
            the wrong type, or the body contains a level-1 heading.
        """
        path = relative_path.as_posix()
        try:
            document = NoteDocument.from_text(text)
        except AfanesError as exc:
            message = DomainMessage.of(MessageCode.CARD_FRONTMATTER_PARSE, path=path, detail=str(exc))
            raise TemplateCardContentError(message) from exc
        note_type = document.note_type
        if note_type not in (NoteType.REFERENCE, NoteType.LOG):
            message = DomainMessage.of(MessageCode.CARD_TYPE_REQUIRED, path=path)
            raise TemplateCardContentError(message)
        category = document.category
        if note_type is NoteType.REFERENCE and category is None:
            message = DomainMessage.of(MessageCode.CARD_CATEGORY_REQUIRED, path=path)
            raise TemplateCardContentError(message)
        if note_type is NoteType.LOG and category is not None:
            message = DomainMessage.of(MessageCode.CARD_LOG_NO_CATEGORY, path=path)
            raise TemplateCardContentError(message)
        cls._refuse_workflow_keys(relative_path, document)
        title = cls._title(relative_path, document.raw)
        description = cls._description(relative_path, document.raw)
        body = document.body.strip("\r\n")
        if cls._has_level_one_heading(body):
            message = DomainMessage.of(MessageCode.CARD_BODY_HEADING, path=path)
            raise TemplateCardContentError(message)
        return TemplateCard(
            relative_path=relative_path,
            note_type=note_type,
            category=category,
            title=title,
            description=description,
            body=body,
            text=text,
        )

    @staticmethod
    def _refuse_workflow_keys(relative_path: Path, document: NoteDocument) -> None:
        """Refuse a card that carries workflow state."""
        path = relative_path.as_posix()
        if document.status is not None:
            message = DomainMessage.of(MessageCode.CARD_STATUS_NOT_ALLOWED, path=path)
            raise TemplateCardContentError(message)
        if document.raw.get("due_date") is not None:
            message = DomainMessage.of(MessageCode.CARD_DUE_NOT_ALLOWED, path=path)
            raise TemplateCardContentError(message)

    @classmethod
    def _title(cls, relative_path: Path, raw: dict[str, object]) -> str:
        """Return the declared title, falling back to the file stem."""
        value = raw.get("title")
        if value is None:
            return relative_path.stem
        if not isinstance(value, str):
            message = DomainMessage.of(MessageCode.CARD_TITLE_NOT_STRING, path=relative_path.as_posix())
            raise TemplateCardContentError(message)
        title = value.strip()
        return title or relative_path.stem

    @classmethod
    def _description(cls, relative_path: Path, raw: dict[str, object]) -> str | None:
        """Return the optional description, normalizing a blank value."""
        value = raw.get("description")
        if value is None:
            return None
        if not isinstance(value, str):
            message = DomainMessage.of(MessageCode.CARD_DESCRIPTION_NOT_STRING, path=relative_path.as_posix())
            raise TemplateCardContentError(message)
        description = value.strip()
        return description or None

    @staticmethod
    def _has_level_one_heading(body: str) -> bool:
        """Return whether the body contains a level-1 heading."""
        return any(token.type == "heading_open" and token.tag == "h1" for token in MarkdownIt("commonmark").parse(body))
