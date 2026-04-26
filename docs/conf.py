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
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

master_doc = "index"
html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_title = "fuggers-py"
html_logo = "_static/fuggers-py-logo.png"
html_theme_options = {
    "sidebar_hide_name": True,
    "light_css_variables": {
        "color-background-primary": "#ffffff",
        "color-background-secondary": "#ffffff",
        "color-sidebar-background": "#ffffff",
        "color-sidebar-background-border": "#e5e7eb",
    },
    "dark_css_variables": {
        "color-background-primary": "#ffffff",
        "color-background-secondary": "#ffffff",
        "color-sidebar-background": "#ffffff",
        "color-sidebar-background-border": "#e5e7eb",
        "color-foreground-primary": "#172033",
        "color-foreground-secondary": "#4b5563",
        "color-foreground-muted": "#6b7280",
        "color-brand-primary": "#0b67c2",
        "color-brand-content": "#0b67c2",
        "color-api-name": "#172033",
        "color-api-pre-name": "#4b5563",
        "color-inline-code-background": "#f3f4f6",
        "color-inline-code-foreground": "#1f2937",
        "color-highlighted-background": "#eef6ff",
    },
}

myst_heading_anchors = 3
napoleon_google_docstring = False
napoleon_numpy_docstring = True
autodoc_typehints = "description"
autodoc_member_order = "bysource"
suppress_warnings = ["ref.python", "sphinx_autodoc_typehints.forward_reference"]
