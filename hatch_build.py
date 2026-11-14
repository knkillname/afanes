# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compile gettext catalogs before Hatchling collects package files."""

import importlib
import pathlib
import sys
import typing

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CatalogsBuildHook(BuildHookInterface):
    """Generate every ``.mo`` catalog before a wheel or sdist is written."""

    def initialize(self, _version: str, build_data: dict[str, typing.Any]) -> None:
        """Compile the tracked ``.po`` sources and include their outputs.

        Parameters
        ----------
        _version : str
            Build version selected by Hatchling. It does not affect the
            catalogs.
        build_data : dict[str, typing.Any]
            Mutable build metadata. Compiled catalogs are appended to its
            ``artifacts`` patterns so the wheel and source distribution include
            them even though Git ignores them.
        """
        source_root = pathlib.Path(self.root) / "src"
        source_text = str(source_root)
        if source_text not in sys.path:
            sys.path.insert(0, source_text)

        i18n_po = importlib.import_module("afanes.i18n.po")
        catalogs = i18n_po.CatalogCompiler(
            localedir=source_root / "afanes" / "i18n" / "locales",
        ).compile()
        artifacts: list[str] = build_data.setdefault("artifacts", [])
        artifacts.extend(f"/{path.relative_to(self.root).as_posix()}" for path in catalogs)
