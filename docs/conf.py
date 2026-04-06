"""Sphinx configuration for the curated project documentation."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

project = "fuggers-py"
author = "Stanislaw Kubik"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
]

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "MODULE_REFERENCE.md",
    "SRC_STRUCTURE.md",
    "conventions.md",
    "docstring_standard.md",
    "validation_strategy.md",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

master_doc = "index"
html_theme = "furo"
html_static_path = ["_static"]
html_title = "fuggers-py"

myst_heading_anchors = 3
napoleon_google_docstring = False
napoleon_numpy_docstring = True
autodoc_typehints = "description"
autodoc_member_order = "bysource"
