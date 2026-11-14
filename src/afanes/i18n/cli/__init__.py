# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Localized copy for the headless command surface."""

from typing import Self

import afanes.core.errors
import afanes.core.localization
import afanes.core.templates
import afanes.i18n.catalog
import afanes.i18n.cli.en
import afanes.i18n.messages
import afanes.i18n.templates

# Public gettext domain for the command line.
CLI_DOMAIN = "afanes-cli"


class CliCopy(afanes.i18n.catalog.LocalizedCatalog):
    """Localized copy for the command line."""

    @classmethod
    def for_locale(
        cls,
        locale: afanes.core.localization.LocaleTag,
        loader: afanes.i18n.catalog.TranslationLoader | None = None,
    ) -> Self:
        """Load the command-line catalog for a locale.

        Parameters
        ----------
        locale : afanes.core.localization.LocaleTag
            Active locale.
        loader : afanes.i18n.catalog.TranslationLoader | None
            Catalog loader. ``None`` uses the bundled catalogs.

        Returns
        -------
        CliCopy
            Localized command-line catalog.
        """
        return cls.load(afanes.i18n.cli.en, CLI_DOMAIN, locale, loader)

    @classmethod
    def english(cls) -> Self:
        """Return the English command-line catalog.

        Returns
        -------
        CliCopy
            Catalog with the English source messages.
        """
        return cls.for_locale(afanes.core.localization.LocaleTag.parse(None))

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
