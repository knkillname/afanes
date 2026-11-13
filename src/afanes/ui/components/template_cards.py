# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared template card picker used by processing and the creation dialogs.

The component owns the option keys and order, duplicate-title disambiguation,
selection fallback, descriptions, and invalid-card warnings. Contexts supply
their own copy so the processing wizard and the reference and log dialogs can
share the mechanics without sharing their surrounding forms.
"""

import dataclasses
from collections.abc import Callable, Sequence
from enum import StrEnum

import flet as ft

import afanes.ui.strings
import afanes.ui.theme
from afanes.core.template_cards import TemplateCard, TemplateCardIssue

EMPTY_KEY = "empty"


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateCardPhrases:
    """Copy for one template card picker context.

    Attributes
    ----------
    label : str
        Dropdown label.
    empty : str
        Display text for the Empty option.
    empty_description : str
        Description shown while Empty is selected.
    no_description : str
        Description shown for a card that declares none.
    warning : str
        Invalid-card warning with a ``paths`` placeholder.
    option : str
        Option text with ``title`` and ``description`` placeholders.
    option_plain : str
        Option text with a ``title`` placeholder.
    option_duplicate : str
        Duplicate-title option text with ``title``, ``description``, and
        ``path`` placeholders.
    option_duplicate_plain : str
        Duplicate-title option text with ``title`` and ``path`` placeholders.
    """

    label: str
    empty: str
    empty_description: str
    no_description: str
    warning: str
    option: str
    option_plain: str
    option_duplicate: str
    option_duplicate_plain: str


class TemplateCardContext(StrEnum):
    """One surrounding form that offers a template card picker.

    Attributes
    ----------
    REFERENCE : str
        New-reference dialog in the workspace browser.
    PROCESSING : str
        Reference or Later outcome in the Processing Wizard.
    LOG : str
        New-log-entry dialog.
    """

    REFERENCE = "reference"
    PROCESSING = "processing"
    LOG = "log"

    def phrases(self) -> TemplateCardPhrases:
        """Return the copy for this context.

        Returns
        -------
        TemplateCardPhrases
            Label, Empty, description, warning, and option formats. The log
            context names a log entry instead of a reference category.
        """
        if self is TemplateCardContext.LOG:
            return TemplateCardPhrases(
                label=afanes.ui.strings.LOG_CARD_LABEL,
                empty=afanes.ui.strings.LOG_CARD_EMPTY,
                empty_description=afanes.ui.strings.LOG_CARD_DESCRIPTION_EMPTY,
                no_description=afanes.ui.strings.BROWSER_TEMPLATE_NO_DESCRIPTION,
                warning=afanes.ui.strings.BROWSER_TEMPLATE_INVALID,
                option=afanes.ui.strings.BROWSER_TEMPLATE_OPTION,
                option_plain=afanes.ui.strings.BROWSER_TEMPLATE_OPTION_PLAIN,
                option_duplicate=afanes.ui.strings.BROWSER_TEMPLATE_OPTION_DUPLICATE,
                option_duplicate_plain=afanes.ui.strings.BROWSER_TEMPLATE_OPTION_DUPLICATE_PLAIN,
            )
        if self is TemplateCardContext.PROCESSING:
            return TemplateCardPhrases(
                label=afanes.ui.strings.PROCESSING_TEMPLATE_LABEL,
                empty=afanes.ui.strings.PROCESSING_TEMPLATE_EMPTY,
                empty_description=afanes.ui.strings.PROCESSING_TEMPLATE_DESCRIPTION_EMPTY,
                no_description=afanes.ui.strings.PROCESSING_TEMPLATE_NO_DESCRIPTION,
                warning=afanes.ui.strings.PROCESSING_TEMPLATE_INVALID,
                option=afanes.ui.strings.PROCESSING_TEMPLATE_OPTION,
                option_plain=afanes.ui.strings.PROCESSING_TEMPLATE_OPTION_PLAIN,
                option_duplicate=afanes.ui.strings.PROCESSING_TEMPLATE_OPTION_DUPLICATE,
                option_duplicate_plain=afanes.ui.strings.PROCESSING_TEMPLATE_OPTION_DUPLICATE_PLAIN,
            )
        return TemplateCardPhrases(
            label=afanes.ui.strings.BROWSER_TEMPLATE_LABEL,
            empty=afanes.ui.strings.BROWSER_TEMPLATE_EMPTY,
            empty_description=afanes.ui.strings.BROWSER_TEMPLATE_DESCRIPTION_EMPTY,
            no_description=afanes.ui.strings.BROWSER_TEMPLATE_NO_DESCRIPTION,
            warning=afanes.ui.strings.BROWSER_TEMPLATE_INVALID,
            option=afanes.ui.strings.BROWSER_TEMPLATE_OPTION,
            option_plain=afanes.ui.strings.BROWSER_TEMPLATE_OPTION_PLAIN,
            option_duplicate=afanes.ui.strings.BROWSER_TEMPLATE_OPTION_DUPLICATE,
            option_duplicate_plain=afanes.ui.strings.BROWSER_TEMPLATE_OPTION_DUPLICATE_PLAIN,
        )


class TemplateCardPicker:
    """Dropdown, description, and warning for one template card context.

    Parameters
    ----------
    context : TemplateCardContext
        Surrounding form that supplies the copy.
    prefix : str
        Control key prefix. The dropdown, description, and warning keys are
        ``<prefix>-template``, ``<prefix>-template-description``, and
        ``<prefix>-template-warning``.
    on_change : Callable[[], None] | None
        Called after the selection changes, or ``None`` when the caller only
        needs the description refreshed.

    Attributes
    ----------
    dropdown : flet.Dropdown
        Card option list with Empty last.
    description : flet.Text
        Description of the selected card or of Empty.
    warning : flet.Text
        Invalid-card warning, visible only when issues are reported.
    """

    def __init__(
        self,
        context: TemplateCardContext,
        prefix: str,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        """Build the picker controls for one context.

        Parameters
        ----------
        context : TemplateCardContext
            Surrounding form that supplies the copy.
        prefix : str
            Control key prefix used to keep dialog control keys stable.
        on_change : Callable[[], None] | None
            Called after the selection changes.
        """
        self._phrases = context.phrases()
        self._on_change = on_change
        self._choices: dict[str, TemplateCard | None] = {EMPTY_KEY: None}
        self.dropdown = ft.Dropdown(
            label=self._phrases.label,
            options=[],
            value=EMPTY_KEY,
            on_select=self._handle_select,
            key=f"{prefix}-template",
        )
        self.description = ft.Text(
            self._phrases.empty_description,
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            selectable=True,
            key=f"{prefix}-template-description",
        )
        self.warning = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            selectable=True,
            visible=False,
            key=f"{prefix}-template-warning",
        )

    @property
    def selected_card(self) -> TemplateCard | None:
        """Return the selected card, or ``None`` for Empty.

        Returns
        -------
        TemplateCard | None
            Selected card, or ``None`` when Empty is selected or the current
            value is unknown.
        """
        return self._choices.get(self.dropdown.value or EMPTY_KEY)

    def refresh(
        self,
        cards: Sequence[TemplateCard],
        issues: Sequence[TemplateCardIssue] = (),
    ) -> None:
        """Rebuild the options from a card listing.

        Parameters
        ----------
        cards : Sequence[TemplateCard]
            Valid cards for this context. The picker orders them by title and
            then relative path, so duplicate-title suffixes stay stable.
        issues : Sequence[TemplateCardIssue]
            Refused card files, or an empty sequence when every card is valid.

        Notes
        -----
        The current selection is kept when its card is still present and falls
        back to Empty when it disappears. The caller repaints the page.
        """
        ordered = sorted(cards, key=lambda card: (card.title.casefold(), card.relative_path.as_posix()))
        counts: dict[str, int] = {}
        for card in ordered:
            counts[card.title.casefold()] = counts.get(card.title.casefold(), 0) + 1
        selected = self.dropdown.value or EMPTY_KEY
        choices: dict[str, TemplateCard | None] = {}
        options: list[ft.dropdown.Option] = []
        for card in ordered:
            key = f"card:{card.relative_path.as_posix()}"
            choices[key] = card
            options.append(ft.dropdown.Option(key=key, text=self._option_text(card, counts)))
        choices[EMPTY_KEY] = None
        options.append(ft.dropdown.Option(key=EMPTY_KEY, text=self._phrases.empty))
        self._choices = choices
        self.dropdown.options = options
        self.dropdown.value = selected if selected in choices else EMPTY_KEY
        self._refresh_description()
        self._refresh_warning(issues)

    def _handle_select(self, _event: object = None) -> None:
        """Refresh the description and notify the caller of a selection change."""
        self._refresh_description()
        if self._on_change is not None:
            self._on_change()

    def _refresh_description(self) -> None:
        """Show the selected card's description or the Empty explanation."""
        card = self.selected_card
        if card is None:
            self.description.value = self._phrases.empty_description
            return
        self.description.value = card.description or self._phrases.no_description

    def _refresh_warning(self, issues: Sequence[TemplateCardIssue]) -> None:
        """Show or hide the invalid-card warning for the current listing."""
        self.warning.visible = bool(issues)
        if not issues:
            self.warning.value = ""
            return
        paths = ", ".join(issue.relative_path.as_posix() for issue in issues)
        self.warning.value = self._phrases.warning.format(paths=paths)

    def _option_text(self, card: TemplateCard, counts: dict[str, int]) -> str:
        """Return the display text for one card option."""
        duplicate = counts[card.title.casefold()] > 1
        if card.description:
            if duplicate:
                return self._phrases.option_duplicate.format(
                    title=card.title,
                    description=card.description,
                    path=card.relative_path.as_posix(),
                )
            return self._phrases.option.format(title=card.title, description=card.description)
        if duplicate:
            return self._phrases.option_duplicate_plain.format(
                title=card.title,
                path=card.relative_path.as_posix(),
            )
        return self._phrases.option_plain.format(title=card.title)
