# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reference template cards stored in a vault ``templates/`` folder.

A template card is a Markdown file whose frontmatter declares a reference
category and whose body is a starter fragment. The catalog reads either the
bundled defaults shipped inside the package or the cards found in a vault
folder. Reading never writes and never raises for a single invalid user card;
the caller receives every valid card plus an issue for each refused file.
"""

import dataclasses
import importlib.resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Self

from markdown_it import MarkdownIt

from afanes.core.errors import AfanesError, TemplateCardContentError
from afanes.core.frontmatter import NoteDocument
from afanes.models.note import CategoryLabel, NoteType

# Public package folder that holds the seven bundled cards.
TEMPLATE_CARDS_PACKAGE = "template_cards"

# Public canonical card extension shared with the vault layout.
NOTE_SUFFIX = ".md"


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateCard:
    """One validated reference template card.

    Attributes
    ----------
    relative_path : pathlib.Path
        Card path relative to the ``templates/`` folder, used as a stable
        identity and to distinguish duplicate titles.
    category : CategoryLabel
        Reference category applied to a note created from this card.
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
    category: CategoryLabel
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
    message : str
        Concise explanation of the violated rule.
    """

    relative_path: Path
    message: str


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


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateCardCatalog:
    """Read reference template cards from one folder.

    Parameters
    ----------
    root : importlib.resources.abc.Traversable
        Folder holding card files. A filesystem path is accepted.

    Notes
    -----
    Use :meth:`bundled` for the installed defaults and :meth:`from_root` for a
    vault folder or a synthetic tree. Reading performs blocking file I/O but
    never writes, and a missing folder is an empty catalog rather than an
    error.
    """

    root: Traversable

    @classmethod
    def bundled(cls) -> Self:
        """Return the catalog shipped inside the installed package.

        Returns
        -------
        TemplateCardCatalog
            Catalog rooted at the package's ``template_cards`` folder.
        """
        package = importlib.resources.files("afanes")
        return cls(root=package.joinpath(TEMPLATE_CARDS_PACKAGE))

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
                message=f"the templates folder cannot be read: {exc}",
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
                issues.append(TemplateCardIssue(relative_path=relative, message=f"cannot be read: {exc}"))
                continue
            try:
                cards.append(self.parse(relative, text))
            except AfanesError as exc:
                issues.append(TemplateCardIssue(relative_path=relative, message=str(exc)))

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
            message = f"Bundled template card {issue.relative_path.as_posix()!r} is invalid: {issue.message}"
            raise TemplateCardContentError(message)
        if not listing.cards:
            message = "Bundled template cards are missing"
            raise TemplateCardContentError(message)
        return listing.cards

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
            If the frontmatter cannot be parsed, the type is not
            ``reference``, the category is missing, workflow keys are present,
            the title or description has the wrong type, or the body contains
            a level-1 heading.
        """
        try:
            document = NoteDocument.from_text(text)
        except AfanesError as exc:
            message = f"frontmatter cannot be parsed: {exc}"
            raise TemplateCardContentError(message) from exc
        if document.note_type is not NoteType.REFERENCE:
            message = "must declare type: reference"
            raise TemplateCardContentError(message)
        if document.category is None:
            message = "must declare a category"
            raise TemplateCardContentError(message)
        cls._refuse_workflow_keys(document)
        title = cls._title(relative_path, document.raw)
        description = cls._description(document.raw)
        body = document.body.strip("\r\n")
        if cls._has_level_one_heading(body):
            message = "the starter body must not contain a level-1 heading"
            raise TemplateCardContentError(message)
        return TemplateCard(
            relative_path=relative_path,
            category=document.category,
            title=title,
            description=description,
            body=body,
            text=text,
        )

    @staticmethod
    def _refuse_workflow_keys(document: NoteDocument) -> None:
        """Refuse a card that carries workflow state."""
        if document.status is not None:
            message = "must not declare a status"
            raise TemplateCardContentError(message)
        if document.raw.get("due_date") is not None:
            message = "must not declare a due date"
            raise TemplateCardContentError(message)

    @classmethod
    def _title(cls, relative_path: Path, raw: dict[str, object]) -> str:
        """Return the declared title, falling back to the file stem."""
        value = raw.get("title")
        if value is None:
            return relative_path.stem
        if not isinstance(value, str):
            message = "title must be a string"
            raise TemplateCardContentError(message)
        title = value.strip()
        return title or relative_path.stem

    @classmethod
    def _description(cls, raw: dict[str, object]) -> str | None:
        """Return the optional description, normalizing a blank value."""
        value = raw.get("description")
        if value is None:
            return None
        if not isinstance(value, str):
            message = "description must be a string"
            raise TemplateCardContentError(message)
        description = value.strip()
        return description or None

    @staticmethod
    def _has_level_one_heading(body: str) -> bool:
        """Return whether the body contains a level-1 heading."""
        return any(token.type == "heading_open" and token.tag == "h1" for token in MarkdownIt("commonmark").parse(body))
