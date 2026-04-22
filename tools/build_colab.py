"""Generator for Colab-ready copies of course notebooks."""
from __future__ import annotations

import re

GITHUB_OWNER = "ixnix"
GITHUB_REPO = "GE5280PythonGeosciences"
GITHUB_BRANCH = "main"

RAW_PREFIX = (
    f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/"
    f"{GITHUB_BRANCH}/"
)
COLAB_PREFIX = (
    f"https://colab.research.google.com/github/{GITHUB_OWNER}/{GITHUB_REPO}/"
    f"blob/{GITHUB_BRANCH}/"
)


def build_raw_url(module: int, subpath: str) -> str:
    return f"{RAW_PREFIX}module_{module}/{subpath}"


def build_colab_open_url(module: int, notebook_name: str) -> str:
    return f"{COLAB_PREFIX}colab/module_{module}/{notebook_name}"


_PATH_RE = re.compile(r"""(['"])(data|img)/([^'"\s]+)\1""")


def rewrite_code_string_paths(source: str, module: int) -> str:
    """Rewrite every 'data/...' or 'img/...' string literal in source code
    to the corresponding GitHub raw URL for the given module.

    Only rewrites strings that begin with exactly 'data/' or 'img/' — so
    unrelated strings like 'output.csv' or 'hello world' are untouched.
    Colab's CWD is /content, so relative-path writes continue to work
    without rewriting.
    """
    def _sub(m: "re.Match") -> str:
        quote, subdir, rest = m.group(1), m.group(2), m.group(3)
        url = build_raw_url(module, f"{subdir}/{rest}")
        return f"{quote}{url}{quote}"

    return _PATH_RE.sub(_sub, source)


_MD_IMAGE_RE = re.compile(r"""(\!?\[[^\]]*\])\((data|img)/([^\s)]+)\)""")

_HTML_IMG_RE = re.compile(
    r"""(<img\s[^>]*?src\s*=\s*)(['"])(data|img)/([^'"\s]+)\2""",
    flags=re.IGNORECASE,
)


def rewrite_markdown_paths(source: str, module: int) -> str:
    """Rewrite markdown image/link references and HTML <img src=> tags
    that point at 'data/...' or 'img/...' to GitHub raw URLs."""
    def _md_sub(m: "re.Match") -> str:
        prefix, subdir, rest = m.group(1), m.group(2), m.group(3)
        url = build_raw_url(module, f"{subdir}/{rest}")
        return f"{prefix}({url})"

    def _html_sub(m: "re.Match") -> str:
        attr, quote, subdir, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        url = build_raw_url(module, f"{subdir}/{rest}")
        return f"{attr}{quote}{url}{quote}"

    out = _MD_IMAGE_RE.sub(_md_sub, source)
    out = _HTML_IMG_RE.sub(_html_sub, out)
    return out


def strip_widgets_metadata(nb) -> None:
    """Remove the 'widgets' notebook-level metadata key, a legacy JupyterLab
    artifact that can crash Colab's renderer."""
    nb.metadata.pop("widgets", None)


def clear_outputs(nb) -> None:
    """Clear outputs and execution counts from all code cells."""
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
