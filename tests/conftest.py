"""Shared test setup for generated gettext catalogs."""

import pathlib

import pytest

import afanes.i18n.po

CATALOG_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "afanes" / "i18n" / "locales"


@pytest.fixture(scope="session", autouse=True)
def compiled_catalogs() -> None:
    """Compile every gettext source before locale tests load a catalog."""
    afanes.i18n.po.CatalogCompiler(localedir=CATALOG_ROOT).compile()
