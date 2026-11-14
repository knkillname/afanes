# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Standard gettext catalogs with English source messages.

English message modules are the schema. Spanish translations live in standard
``.po`` files and are loaded from compiled ``.mo`` files by the standard library
:mod:`gettext`. A missing Spanish entry falls back to the English source.
"""

import dataclasses
import gettext
import struct
import types
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Self

import afanes.core.localization


class CatalogError(Exception):
    """Raised when a catalog cannot render a requested message."""


@dataclasses.dataclass(frozen=True, slots=True)
class TranslationLoader:
    """Load gettext domains from one localedir.

    Attributes
    ----------
    localedir : pathlib.Path
        Directory holding ``<language>/LC_MESSAGES/<domain>.mo``.
    """

    localedir: Path

    @classmethod
    def default(cls) -> Self:
        """Return the loader for the package's bundled catalogs.

        Returns
        -------
        TranslationLoader
            Loader rooted at ``src/afanes/i18n/locales``.
        """
        return cls(localedir=Path(__file__).resolve().parent / "locales")

    def load(self, domain: str, locale: afanes.core.localization.LocaleTag) -> gettext.NullTranslations:
        """Load one domain for a locale.

        Parameters
        ----------
        domain : str
            Gettext domain name.
        locale : afanes.core.localization.LocaleTag
            Active locale. English loads the null catalog.

        Returns
        -------
        gettext.NullTranslations
            Loaded catalog, or a null catalog when the file is missing or
            corrupt. A missing Spanish entry then renders its English msgid.
        """
        try:
            return gettext.translation(
                domain,
                localedir=self.localedir,
                languages=[locale.language],
                fallback=True,
            )
        except (OSError, ValueError, struct.error):
            return gettext.NullTranslations()


@dataclasses.dataclass(frozen=True, slots=True)
class LocalizedCatalog:
    """English source messages resolved against one gettext domain.

    Attributes
    ----------
    source : types.ModuleType
        English source module whose public constants are the schema.
    domain : str
        Gettext domain name.
    locale : afanes.core.localization.LocaleTag
        Active locale.
    translations : gettext.NullTranslations
        Loaded catalog for the locale.
    """

    source: types.ModuleType
    domain: str
    locale: afanes.core.localization.LocaleTag
    translations: gettext.NullTranslations

    @classmethod
    def load(
        cls,
        source: types.ModuleType,
        domain: str,
        locale: afanes.core.localization.LocaleTag,
        loader: TranslationLoader | None = None,
    ) -> Self:
        """Build a catalog for one source module and locale.

        Parameters
        ----------
        source : types.ModuleType
            English source module.
        domain : str
            Gettext domain name.
        locale : afanes.core.localization.LocaleTag
            Active locale.
        loader : TranslationLoader | None
            Catalog loader. ``None`` uses the bundled catalogs.

        Returns
        -------
        LocalizedCatalog
            Catalog carrying the loaded translations.
        """
        active_loader = TranslationLoader.default() if loader is None else loader
        return cls(
            source=source,
            domain=domain,
            locale=locale,
            translations=active_loader.load(domain, locale),
        )

    def __getattr__(self, name: str) -> str:
        """Return one localized source constant.

        Parameters
        ----------
        name : str
            Public constant name in the English source module.

        Returns
        -------
        str
            Spanish value when present, otherwise the English msgid.

        Raises
        ------
        AttributeError
            If the English source module has no public string constant with
            that name.
        """
        if name.startswith("_"):
            message = f"{type(self).__name__} has no attribute {name!r}"
            raise AttributeError(message)
        english = getattr(self.source, name, None)
        if not isinstance(english, str):
            message = f"{self.domain} has no source message {name!r}"
            raise AttributeError(message)  # noqa: TRY004
        return self.translations.pgettext(name, english)

    def mapping(self, name: str) -> Mapping[str, str]:
        """Return one localized mapping constant.

        Parameters
        ----------
        name : str
            Public mapping constant name in the English source module.

        Returns
        -------
        collections.abc.Mapping[str, str]
            Read-only mapping whose entries use ``MAPPING.key`` contexts.

        Raises
        ------
        AttributeError
            If the English source module has no mapping constant with that
            name.
        TypeError
            If a mapping key or value is not text.
        """
        english = getattr(self.source, name, None)
        if not isinstance(english, Mapping):
            message = f"{self.domain} has no mapping source {name!r}"
            raise AttributeError(message)  # noqa: TRY004
        translated: dict[str, str] = {}
        for key, value in english.items():
            if not isinstance(key, str) or not isinstance(value, str):
                message = f"{self.domain} mapping {name!r} must map strings to strings"
                raise TypeError(message)
            translated[key] = self.translations.pgettext(f"{name}.{key}", value)
        return MappingProxyType(translated)
