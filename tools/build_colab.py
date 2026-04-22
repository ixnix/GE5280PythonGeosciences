"""Generator for Colab-ready copies of course notebooks."""
from __future__ import annotations

import re
from pathlib import Path

import nbformat

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

# After URL rewrite: Image(filename="https://...") → Image(url="https://...").
# IPython's Image.filename opens a local file; for remote URLs, use url=.
_IMAGE_FILENAME_RE = re.compile(
    r"""(Image\s*\(\s*)filename(\s*=\s*)(['"])(https?://)""",
)


def rewrite_code_string_paths(source: str, module: int) -> str:
    """Rewrite every 'data/...' or 'img/...' string literal in source code
    to the corresponding GitHub raw URL for the given module.

    Only rewrites strings that begin with exactly 'data/' or 'img/' — so
    unrelated strings like 'output.csv' or 'hello world' are untouched.
    Colab's CWD is /content, so relative-path writes continue to work
    without rewriting.

    After URL rewriting, IPython.display.Image(filename=<url>) is converted
    to Image(url=<url>); filename= only works for local files.
    """
    def _sub(m: "re.Match") -> str:
        quote, subdir, rest = m.group(1), m.group(2), m.group(3)
        url = build_raw_url(module, f"{subdir}/{rest}")
        return f"{quote}{url}{quote}"

    out = _PATH_RE.sub(_sub, source)
    out = _IMAGE_FILENAME_RE.sub(r"\1url\2\3\4", out)
    return out


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


def build_header_cell(module: int, notebook_name: str, title: str):
    """Build the injected header markdown cell with the Open-in-Colab badge."""
    colab_url = build_colab_open_url(module, notebook_name)
    badge = "https://colab.research.google.com/assets/colab-badge.svg"
    source = (
        f"# {title}\n"
        "\n"
        f"[![Open In Colab]({badge})]({colab_url})\n"
        "\n"
        "*Run this notebook on Google Colab — no setup required.*"
    )
    return nbformat.v4.new_markdown_cell(source)


def build_cartopy_install_cell():
    """Build the code cell that installs cartopy — used for module 13 only."""
    return nbformat.v4.new_code_cell("!pip install -q cartopy")


def transform_notebook(
    source: Path,
    dest: Path,
    module: int,
    notebook_name: str,
    title: str,
    include_cartopy_install: bool,
) -> None:
    """Read a source notebook, apply all Colab transforms, write to dest."""
    nb = nbformat.read(source, as_version=4)

    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.source = rewrite_code_string_paths(cell.source, module)
        elif cell.cell_type == "markdown":
            cell.source = rewrite_markdown_paths(cell.source, module)

    strip_widgets_metadata(nb)
    clear_outputs(nb)

    injected = [build_header_cell(module, notebook_name, title)]
    if include_cartopy_install:
        injected.append(build_cartopy_install_cell())
    nb.cells = injected + nb.cells

    dest.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, dest)


def collect_referenced_paths(source: Path) -> set:
    """Scan a notebook for every 'data/...' or 'img/...' string/link.
    Returns a set of relative paths (e.g., {'data/foo.csv', 'img/bar.png'})."""
    nb = nbformat.read(source, as_version=4)
    refs: set = set()
    for cell in nb.cells:
        src = cell.source
        if cell.cell_type == "code":
            for m in _PATH_RE.finditer(src):
                refs.add(f"{m.group(2)}/{m.group(3)}")
        elif cell.cell_type == "markdown":
            for m in _MD_IMAGE_RE.finditer(src):
                refs.add(f"{m.group(2)}/{m.group(3)}")
            for m in _HTML_IMG_RE.finditer(src):
                refs.add(f"{m.group(3)}/{m.group(4)}")
    return refs


def validate_references(refs, module_dir: Path) -> None:
    """Raise FileNotFoundError if any referenced path is missing on disk."""
    missing = [r for r in refs if not (module_dir / r).exists()]
    if missing:
        raise FileNotFoundError(
            f"{module_dir}: referenced file(s) missing: {sorted(missing)}"
        )


MODULES = [
    {"number": 1, "title": "Course Overview",
     "lecture": "1_Overview.ipynb", "extras": ["Syllabus.ipynb"]},
    {"number": 2, "title": "Variables",
     "lecture": "2_Variables.ipynb"},
    {"number": 3, "title": "Data Structures",
     "lecture": "3_DataStructure.ipynb"},
    {"number": 4, "title": "Control Flow",
     "lecture": "4_ControlFlow.ipynb"},
    {"number": 5, "title": "Functions",
     "lecture": "5_Functions.ipynb"},
    {"number": 6, "title": "NumPy",
     "lecture": "6_Numpy.ipynb"},
    {"number": 7, "title": "Pandas Data Structures",
     "lecture": "7_PandasDataStructure.ipynb"},
    {"number": 8, "title": "Data Wrangling",
     "lecture": "8_DataWrangling.ipynb"},
    {"number": 9, "title": "Data Aggregation",
     "lecture": "9_DataAggregation.ipynb"},
    {"number": 10, "title": "Time Series",
     "lecture": "10_TimeSeries.ipynb"},
    {"number": 11, "title": "Lambda Functions",
     "lecture": "11_LambdaFunction.ipynb"},
    {"number": 12, "title": "Object-Oriented Programming",
     "lecture": "12_OOP.ipynb"},
    {"number": 13, "title": "Cartopy",
     "lecture": "13_Cartopy.ipynb"},
    {"number": 14, "title": "Seaborn",
     "lecture": "14_Seaborn.ipynb"},
]


def _colab_link(module: int, notebook: str) -> str:
    url = build_colab_open_url(module, notebook)
    return f"[Open in Colab]({url})"


def build_landing_page() -> str:
    lines = [
        "# GE5280 — Run in Google Colab",
        "",
        "This directory contains Colab-ready copies of all course notebooks.",
        "Click any **Open in Colab** link below to launch the notebook in",
        "Google Colab. You need a free Google account; the free Colab tier is",
        "more than enough for this course. No local installation required.",
        "",
        "The original notebooks in `module_*/` are unchanged — this folder is",
        "a generated mirror. For module 13 (Cartopy), Colab will spend an",
        "extra 30–60 seconds installing the package on first cell run.",
        "",
        "| Module | Topic | Lecture | Assignment |",
        "|--------|-------|---------|------------|",
    ]
    for m in MODULES:
        num = m["number"]
        lecture_link = _colab_link(num, m["lecture"])
        assign_name = f"Assignment_{num}.ipynb"
        assign_link = _colab_link(num, assign_name)
        lines.append(
            f"| {num} | {m['title']} | {lecture_link} | {assign_link} |"
        )
        for extra in m.get("extras", []):
            extra_link = _colab_link(num, extra)
            lines.append(
                f"| {num} | {m['title']} ({extra[:-6]}) | {extra_link} | — |"
            )
    lines.append("")
    return "\n".join(lines)


import argparse
import shutil
import sys


def _lecture_notebooks_for(module):
    """Return list of (notebook_name, title, include_cartopy) tuples
    for one module. Covers lecture, extras (e.g., Syllabus), and assignment."""
    num = module["number"]
    include_cartopy = (num == 13)
    items = []
    items.append((module["lecture"], module["title"], include_cartopy))
    for extra in module.get("extras", []):
        items.append((extra, extra.replace(".ipynb", ""), include_cartopy))
    assignment = f"Assignment_{num}.ipynb"
    items.append((assignment, f"Assignment {num}: {module['title']}",
                  include_cartopy))
    return items


def build_all(repo_root: Path, output_dir: Path, only_module) -> None:
    """Generate all Colab copies. If output_dir exists, it is replaced."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for module in MODULES:
        num = module["number"]
        if only_module is not None and num != only_module:
            continue
        source_module_dir = repo_root / f"module_{num}"
        dest_module_dir = output_dir / f"module_{num}"
        dest_module_dir.mkdir(parents=True, exist_ok=True)

        for notebook_name, title, include_cartopy in _lecture_notebooks_for(module):
            source = source_module_dir / notebook_name
            if not source.exists():
                raise FileNotFoundError(f"Expected notebook missing: {source}")
            refs = collect_referenced_paths(source)
            validate_references(refs, source_module_dir)
            transform_notebook(
                source=source,
                dest=dest_module_dir / notebook_name,
                module=num,
                notebook_name=notebook_name,
                title=title,
                include_cartopy_install=include_cartopy,
            )

    (output_dir / "README.md").write_text(build_landing_page())


def _parse_args(argv):
    p = argparse.ArgumentParser(description="Generate Colab-ready notebook copies.")
    p.add_argument("--module", type=int, default=None,
                   help="Only rebuild this module (1-14).")
    p.add_argument("--output-dir", type=Path, default=Path("colab"),
                   help="Where to write output (default: ./colab).")
    p.add_argument("--dry-run", action="store_true",
                   help="List planned actions, write nothing.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    repo_root = Path.cwd()

    if args.dry_run:
        print(f"[dry-run] Would write output to: {args.output_dir}")
        for module in MODULES:
            num = module["number"]
            if args.module is not None and num != args.module:
                continue
            for notebook_name, _, _ in _lecture_notebooks_for(module):
                print(f"[dry-run]   module_{num}/{notebook_name}")
        print("[dry-run] Would write README.md landing page.")
        return 0

    build_all(repo_root=repo_root, output_dir=args.output_dir,
              only_module=args.module)
    print(f"Wrote Colab copies to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
