# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Localized labels and descriptions for the starter templates."""

from typing import Self

import afanes.core.localization
import afanes.core.templates
import afanes.i18n.catalog
import afanes.i18n.templates.en

# Public gettext domain shared with the structured domain messages.
TEMPLATES_DOMAIN = "afanes-messages"

_LABEL_KEYS = {
    "personal": ("TEMPLATE_PERSONAL_LABEL", "TEMPLATE_PERSONAL_DESCRIPTION"),
    "work": ("TEMPLATE_WORK_LABEL", "TEMPLATE_WORK_DESCRIPTION"),
    "study": ("TEMPLATE_STUDY_LABEL", "TEMPLATE_STUDY_DESCRIPTION"),
}


class TemplateLabelCatalog(afanes.i18n.catalog.LocalizedCatalog):
    """Localized labels and descriptions for the fixed template catalog."""

    @classmethod
    def for_locale(
        cls,
        locale: afanes.core.localization.LocaleTag,
        loader: afanes.i18n.catalog.TranslationLoader | None = None,
    ) -> Self:
        """Load the template label catalog for a locale.

        Parameters
        ----------
        locale : afanes.core.localization.LocaleTag
            Active locale.
        loader : afanes.i18n.catalog.TranslationLoader | None
            Catalog loader. ``None`` uses the bundled catalogs.

        Returns
        -------
        TemplateLabelCatalog
            Catalog for the locale.
        """
        return cls.load(afanes.i18n.templates.en, TEMPLATES_DOMAIN, locale, loader)

    @classmethod
    def english(cls) -> Self:
        """Return the English template label catalog.

        Returns
        -------
        TemplateLabelCatalog
            Catalog with the English source labels.
        """
        return cls.for_locale(afanes.core.localization.LocaleTag.parse(None))

    def labels(self) -> tuple[afanes.core.templates.TemplateLabel, ...]:
        """Return localized labels in the fixed catalog order.

        Returns
        -------
        tuple[afanes.core.templates.TemplateLabel, ...]
            One label and description per bundled template.
        """
        labels: list[afanes.core.templates.TemplateLabel] = []
        for template in afanes.core.templates.BUNDLED_TEMPLATES:
            label_key, description_key = _LABEL_KEYS[template.identifier]
            labels.append(
                afanes.core.templates.TemplateLabel(
                    identifier=template.identifier,
                    label=getattr(self, label_key),
                    description=getattr(self, description_key),
                )
            )
        return tuple(labels)
