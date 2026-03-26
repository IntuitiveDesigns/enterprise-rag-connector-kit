import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))


project = "Enterprise RAG Connector Kit"
copyright = "2026, Steven Lopez"
author = "Steven Lopez"
release = "0.1.0"


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
    "sphinx_autodoc_typehints",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autoclass_content = "both"

templates_path = ["_templates"]
exclude_patterns = []


html_theme = "alabaster"
html_static_path = ["_static"]

html_title = "Enterprise RAG Connector Kit"
html_short_title = "Enterprise RAG Connector"
