# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Localized interface copy and its formatting rules."""

import dataclasses
from collections.abc import Mapping
from typing import Self

import afanes.core.errors
import afanes.core.localization
import afanes.core.templates
import afanes.i18n.catalog
import afanes.i18n.messages
import afanes.i18n.templates
import afanes.i18n.ui.en

# Public gettext domain for the interface.
UI_DOMAIN = "afanes-ui"


@dataclasses.dataclass(frozen=True, slots=True)
class CopyFormatter:
    """Format interface counts and labels for one active catalog.

    Attributes
    ----------
    catalog : UiCopy
        Catalog that supplies the localized phrases.
    """

    catalog: "UiCopy"

    def log_entry_count(self, count: int) -> str:
        """Return a compact entry count for a tree row.

        Parameters
        ----------
        count : int
            Number of notes at or below the row.

        Returns
        -------
        str
            Parenthesized count.
        """
        return f"({self.catalog.locale_format.count(count)})"

    def log_day_tooltip(self, day: int, count: int) -> str:
        """Return the calendar day tooltip for an entry count.

        Parameters
        ----------
        day : int
            Calendar day.
        count : int
            Number of entries on that day.

        Returns
        -------
        str
            Tooltip naming the date and entry count.
        """
        if count == 0:
            return self.catalog.LOG_DAY_TOOLTIP_NONE.format(day=day)
        if count == 1:
            return self.catalog.LOG_DAY_TOOLTIP_ONE.format(day=day)
        return self.catalog.LOG_DAY_TOOLTIP_MANY.format(
            day=day,
            count=self.catalog.locale_format.count(count),
        )

    def reference_count(self, count: int, notes: int) -> str:
        """Return a short reference-count phrase for a page dialog.

        Parameters
        ----------
        count : int
            Number of references affected.
        notes : int
            Number of notes containing those references.

        Returns
        -------
        str
            Phrase such as ``2 references in 1 note``.
        """
        reference_word = self.catalog.REFERENCE_WORD_ONE if count == 1 else self.catalog.REFERENCE_WORD_MANY
        note_word = self.catalog.NOTE_WORD_ONE if notes == 1 else self.catalog.NOTE_WORD_MANY
        return self.catalog.REFERENCE_COUNT.format(
            references=self.catalog.locale_format.count(count),
            reference_word=reference_word,
            notes=self.catalog.locale_format.count(notes),
            note_word=note_word,
        )

    def trash_entry_count(self, count: int) -> str:
        """Return the trashed-note count used by the Empty Trash confirmation.

        Parameters
        ----------
        count : int
            Number of managed entries that will be deleted.

        Returns
        -------
        str
            Singular or plural phrase such as ``3 trashed notes``.
        """
        template = self.catalog.TRASH_ENTRY_ONE if count == 1 else self.catalog.TRASH_ENTRY_MANY
        return template.format(count=self.catalog.locale_format.count(count))

    def note_count(self, count: int) -> str:
        """Return the note-count label for the Inbox heading.

        Parameters
        ----------
        count : int
            Number of notes currently shown.

        Returns
        -------
        str
            Singular or plural count label.
        """
        template = self.catalog.NOTE_COUNT_ONE if count == 1 else self.catalog.NOTE_COUNT_MANY
        return template.format(count=self.catalog.locale_format.count(count))

    def open_step_count(self, count: int) -> str:
        """Return the open-step count label for a project row.

        Parameters
        ----------
        count : int
            Number of open steps.

        Returns
        -------
        str
            Singular or plural label.
        """
        template = self.catalog.PROJECT_OPEN_STEPS_ONE if count == 1 else self.catalog.PROJECT_OPEN_STEPS_MANY
        return template.format(count=self.catalog.locale_format.count(count))

    def review_pending(self, count: int) -> str:
        """Return the review badge label.

        Parameters
        ----------
        count : int
            Number of captures and stalled projects awaiting review.

        Returns
        -------
        str
            Singular or plural pending label, including zero.
        """
        template = self.catalog.REVIEW_PENDING_ONE if count == 1 else self.catalog.REVIEW_PENDING_MANY
        return template.format(count=self.catalog.locale_format.count(count))


class UiCopy(afanes.i18n.catalog.LocalizedCatalog):
    """Localized copy for the interface."""

    @classmethod
    def for_locale(
        cls,
        locale: afanes.core.localization.LocaleTag,
        loader: afanes.i18n.catalog.TranslationLoader | None = None,
    ) -> Self:
        """Load the interface catalog for a locale.

        Parameters
        ----------
        locale : afanes.core.localization.LocaleTag
            Active locale.
        loader : afanes.i18n.catalog.TranslationLoader | None
            Catalog loader. ``None`` uses the bundled catalogs.

        Returns
        -------
        UiCopy
            Localized interface catalog.
        """
        return cls.load(afanes.i18n.ui.en, UI_DOMAIN, locale, loader)

    @classmethod
    def english(cls) -> Self:
        """Return the English interface catalog.

        Returns
        -------
        UiCopy
            Catalog with the English source messages.
        """
        return cls.for_locale(afanes.core.localization.LocaleTag.parse(None))

    @property
    def locale_format(self) -> afanes.core.localization.LocaleFormat:
        """Return display formatting for the active locale.

        Returns
        -------
        afanes.core.localization.LocaleFormat
            Date, time, and count formatting.
        """
        return afanes.core.localization.LocaleFormat.for_locale(self.locale)

    @property
    def formatter(self) -> CopyFormatter:
        """Return the count and label formatter bound to this catalog.

        Returns
        -------
        CopyFormatter
            Formatter using the active catalog.
        """
        return CopyFormatter(catalog=self)

    def template_labels(self) -> tuple[afanes.core.templates.TemplateLabel, ...]:
        """Return localized starter-template labels and descriptions.

        Returns
        -------
        tuple[afanes.core.templates.TemplateLabel, ...]
            One label per bundled template, in catalog order.
        """
        return afanes.i18n.templates.TemplateLabelCatalog.for_locale(self.locale).labels()

    def render_error(self, error: BaseException) -> str:
        """Render one boundary error in the active locale.

        Parameters
        ----------
        error : BaseException
            Domain error or a technical exception from a wrapped operation.

        Returns
        -------
        str
            Localized domain message, or the technical text for a non-domain
            error.
        """
        if isinstance(error, afanes.core.errors.AfanesError) and isinstance(
            error.domain_message, afanes.core.errors.DomainMessage
        ):
            return self.messages.render(error.domain_message)
        return str(error)

    @property
    def messages(self) -> afanes.i18n.messages.MessageCatalog:
        """Return the domain-message catalog for the active locale.

        Returns
        -------
        afanes.i18n.messages.MessageCatalog
            Catalog that renders structured domain messages in this locale.
        """
        return afanes.i18n.messages.MessageCatalog.for_locale(self.locale)

    @property
    def WORKSPACE_SECTION_LABELS(self) -> Mapping[str, str]:  # noqa: N802
        """Return the localized workspace destination labels.

        Returns
        -------
        collections.abc.Mapping[str, str]
            Labels keyed by destination.
        """
        return self.mapping("WORKSPACE_SECTION_LABELS")

    @property
    def REVIEW_KIND_LABELS(self) -> Mapping[str, str]:  # noqa: N802
        """Return the localized review kind labels.

        Returns
        -------
        collections.abc.Mapping[str, str]
            Labels keyed by review kind.
        """
        return self.mapping("REVIEW_KIND_LABELS")

    @property
    def PROJECT_GROUP_LABELS(self) -> Mapping[str, str]:  # noqa: N802
        """Return the localized project group labels.

        Returns
        -------
        collections.abc.Mapping[str, str]
            Labels keyed by project group.
        """
        return self.mapping("PROJECT_GROUP_LABELS")

    @property
    def PROCESSING_OUTCOME_LABELS(self) -> Mapping[str, str]:  # noqa: N802
        """Return the localized processing outcome labels.

        Returns
        -------
        collections.abc.Mapping[str, str]
            Labels keyed by processing outcome.
        """
        return self.mapping("PROCESSING_OUTCOME_LABELS")

    @property
    def PROCESSING_STATUS_LABELS(self) -> Mapping[str, str]:  # noqa: N802
        """Return the localized processing status labels.

        Returns
        -------
        collections.abc.Mapping[str, str]
            Labels keyed by status.
        """
        return self.mapping("PROCESSING_STATUS_LABELS")

    @property
    def PAGE_TYPE_LABELS(self) -> Mapping[str, str]:  # noqa: N802
        """Return the localized page type labels.

        Returns
        -------
        collections.abc.Mapping[str, str]
            Labels keyed by note type.
        """
        return self.mapping("PAGE_TYPE_LABELS")
