"""Sphinx configuration for the Afanes documentation."""

import importlib.metadata
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "afanes"
author = "Mario Abarca"
copyright = "2026, Mario Abarca"

release = importlib.metadata.version("afanes")
version = ".".join(release.split(".")[:2])

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
    "sphinx_design",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
master_doc = "index"
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

myst_enable_extensions = ["colon_fence", "deflist", "tasklist"]
myst_heading_anchors = 3

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "show-inheritance": True,
}
autodoc_typehints = "description"
napoleon_google_docstring = False
napoleon_numpy_docstring = True
nitpicky = True

html_theme = "furo"
html_title = "Afanes documentation"
html_short_title = "Afanes"
html_theme_options = {
    "navigation_with_keys": True,
}
html_static_path = ["_static"]
html_css_files = ["custom.css"]
