# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Render structured domain messages through the gettext catalog."""

import dataclasses
import gettext
from typing import Self

import afanes.core.errors
import afanes.core.localization
import afanes.i18n.catalog
import afanes.i18n.messages.en

# Public gettext domain shared by the interface and the command line.
MESSAGES_DOMAIN = "afanes-messages"


@dataclasses.dataclass(frozen=True, slots=True)
class MessageCatalog:
    """Domain message templates resolved for one locale.

    Attributes
    ----------
    locale : afanes.core.localization.LocaleTag
        Active locale.
    translations : gettext.NullTranslations
        Loaded message catalog.
    """

    locale: afanes.core.localization.LocaleTag
    translations: gettext.NullTranslations

    @classmethod
    def for_locale(
        cls,
        locale: afanes.core.localization.LocaleTag,
        loader: afanes.i18n.catalog.TranslationLoader | None = None,
    ) -> Self:
        """Load the message catalog for a locale.

        Parameters
        ----------
        locale : afanes.core.localization.LocaleTag
            Active locale.
        loader : afanes.i18n.catalog.TranslationLoader | None
            Catalog loader. ``None`` uses the bundled catalogs.

        Returns
        -------
        MessageCatalog
            Catalog for the locale.
        """
        active_loader = afanes.i18n.catalog.TranslationLoader.default() if loader is None else loader
        return cls(locale=locale, translations=active_loader.load(MESSAGES_DOMAIN, locale))

    @classmethod
    def english(cls) -> Self:
        """Return the English message catalog.

        Returns
        -------
        MessageCatalog
            Catalog with the English templates.
        """
        return cls.for_locale(afanes.core.localization.LocaleTag.parse(None))

    def render(self, message: afanes.core.errors.DomainMessage) -> str:
        """Render one structured domain message.

        Parameters
        ----------
        message : afanes.core.errors.DomainMessage
            Message identity and ordered values.

        Returns
        -------
        str
            Localized sentence with every value substituted.

        Raises
        ------
        afanes.i18n.catalog.CatalogError
            If the code has no English template or a template placeholder has
            no value.
        """
        template = afanes.i18n.messages.en.TEMPLATES.get(message.code)
        if template is None:
            detail = f"No English message template for {message.code.value!r}"
            raise afanes.i18n.catalog.CatalogError(detail)
        translated = self.translations.pgettext(message.code.value, template)
        values = dict(message.values)
        try:
            return translated.format(**values)
        except (KeyError, IndexError, ValueError) as exc:
            detail = f"Message {message.code.value!r} has no value for a template placeholder"
            raise afanes.i18n.catalog.CatalogError(detail) from exc
