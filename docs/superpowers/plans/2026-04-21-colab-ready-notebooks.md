# Colab-Ready Notebook Copies — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two Python scripts (`tools/build_colab.py`, `tools/test_colab.py`) that generate a `colab/` mirror of 29 lecture/assignment notebooks with GitHub raw URLs for data/images, and validate the generated notebooks execute cleanly.

**Architecture:** Two self-contained Python scripts in `tools/`. The generator reads originals via `nbformat`, applies a narrow set of regex rewrites to code-cell strings and markdown image refs, injects header + (for module 13) install cells, and writes to `colab/module_N/`. The tester checks URL reachability and executes each generated notebook in a pinned "Colab-like" venv via `nbconvert --execute`. Everything is run manually by the author; no CI.

**Tech Stack:** Python 3.10+, `nbformat`, `nbconvert`, `requests`, `pytest`, `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-04-21-colab-ready-notebooks-design.md`

**Repo/URL constants used throughout:**
- GitHub owner: `ixnix`
- Repo: `GE5280PythonGeosciences`
- Branch: `main`
- Raw URL prefix: `https://raw.githubusercontent.com/ixnix/GE5280PythonGeosciences/main/`
- Colab URL prefix: `https://colab.research.google.com/github/ixnix/GE5280PythonGeosciences/blob/main/`

---

## File structure

```
tools/
├── __init__.py                 # empty, makes tools a package for tests
├── build_colab.py              # generator (single file, ~300 lines)
├── test_colab.py               # tester (single file, ~250 lines)
├── colab_requirements.txt      # pinned Colab-like venv
├── dev_requirements.txt        # pytest, nbformat, nbconvert, requests
├── README.md                   # how to run the tools
└── tests/
    ├── __init__.py             # empty
    ├── conftest.py             # shared pytest fixtures
    ├── fixtures/
    │   └── sample_notebook.ipynb   # tiny synthetic notebook for integration tests
    ├── test_build_colab.py
    └── test_test_colab.py

colab/                          # generated output (populated by Task 12)
├── README.md
└── module_1/ ... module_14/
```

Each script is a single file. Pure functions (URL builders, string rewriters, cell builders) are defined at module scope and unit-tested directly. CLI glue sits at the bottom of each script behind `if __name__ == "__main__":`.

---

## Task 1: Scaffolding and dependencies

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/tests/__init__.py`
- Create: `tools/dev_requirements.txt`
- Create: `tools/tests/conftest.py`
- Create: `tools/tests/fixtures/sample_notebook.ipynb`

- [ ] **Step 1: Create directories and empty init files**

```bash
mkdir -p tools/tests/fixtures
touch tools/__init__.py
touch tools/tests/__init__.py
```

- [ ] **Step 2: Write `tools/dev_requirements.txt`**

```
nbformat>=5.9
nbconvert>=7.10
requests>=2.31
pytest>=7.4
```

- [ ] **Step 3: Install dev dependencies**

Run: `pip install -r tools/dev_requirements.txt`
Expected: successful install (no errors).

- [ ] **Step 4: Create a minimal fixture notebook `tools/tests/fixtures/sample_notebook.ipynb`**

The fixture should be a real, valid nbformat-v4 JSON with:
- A markdown cell containing `# Sample Lecture\n\n![diagram](img/foo.png)\n\n<img src="img/bar.jpg">`
- A code cell containing `import pandas as pd\ndf = pd.read_csv("data/things.csv")`
- A code cell containing `from IPython.display import Image\nImage(filename="img/baz.png")`
- A code cell containing `with open("output.csv", "w") as f:\n    f.write("x")` — this tests that file writes are *not* rewritten
- An `outputs` array on each code cell that is non-empty (to verify stripping works)

Use `nbformat.v4.new_notebook()` via a one-off Python REPL to build it cleanly, then serialize with `nbformat.write`. Easiest: write a tiny one-off script, run once, delete the script, keep the `.ipynb`.

- [ ] **Step 5: Write `tools/tests/conftest.py`**

```python
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_notebook_path():
    return FIXTURES / "sample_notebook.ipynb"
```

- [ ] **Step 6: Commit**

```bash
git add tools/
git commit -m "tools: scaffold directory, dev requirements, test fixture"
```

---

## Task 2: URL builders

**Files:**
- Create: `tools/build_colab.py`
- Create: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Write failing tests in `tools/tests/test_build_colab.py`**

```python
from tools.build_colab import build_raw_url, build_colab_open_url


def test_build_raw_url_data_file():
    assert build_raw_url(7, "data/earthquake.txt") == (
        "https://raw.githubusercontent.com/ixnix/GE5280PythonGeosciences/"
        "main/module_7/data/earthquake.txt"
    )


def test_build_raw_url_img_file():
    assert build_raw_url(1, "img/filesystem.png") == (
        "https://raw.githubusercontent.com/ixnix/GE5280PythonGeosciences/"
        "main/module_1/img/filesystem.png"
    )


def test_build_colab_open_url():
    assert build_colab_open_url(13, "13_Cartopy.ipynb") == (
        "https://colab.research.google.com/github/ixnix/"
        "GE5280PythonGeosciences/blob/main/colab/module_13/13_Cartopy.ipynb"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: collection error / ImportError (module not created yet).

- [ ] **Step 3: Create `tools/build_colab.py` with the minimal implementation**

```python
"""Generator for Colab-ready copies of course notebooks."""
from __future__ import annotations

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: add URL builders for raw and Colab-open links"
```

---

## Task 3: Code-cell string rewriting

**Files:**
- Modify: `tools/build_colab.py`
- Modify: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Append failing tests to `tools/tests/test_build_colab.py`**

```python
from tools.build_colab import rewrite_code_string_paths


def test_rewrite_double_quoted_data_path():
    src = 'df = pd.read_csv("data/earthquake.txt")'
    out = rewrite_code_string_paths(src, module=6)
    assert out == (
        'df = pd.read_csv("https://raw.githubusercontent.com/ixnix/'
        'GE5280PythonGeosciences/main/module_6/data/earthquake.txt")'
    )


def test_rewrite_single_quoted_img_path():
    src = "Image(filename='img/foo.png')"
    out = rewrite_code_string_paths(src, module=1)
    assert "module_1/img/foo.png" in out
    assert "'https://raw" in out


def test_rewrite_leaves_unrelated_strings_alone():
    src = "x = 'hello world'\nfn = 'output.csv'"
    out = rewrite_code_string_paths(src, module=7)
    assert out == src


def test_rewrite_leaves_writes_and_non_data_paths_alone():
    # We do NOT rewrite 'output.csv' — Colab's CWD is /content, writes stay relative.
    src = 'with open("output.csv", "w") as f: pass'
    out = rewrite_code_string_paths(src, module=7)
    assert out == src


def test_rewrite_handles_nested_subdirs():
    src = "x = 'data/sub/nested.csv'"
    out = rewrite_code_string_paths(src, module=8)
    assert "module_8/data/sub/nested.csv" in out


def test_rewrite_multiple_occurrences():
    src = 'a = "data/one.csv"; b = "img/two.png"'
    out = rewrite_code_string_paths(src, module=9)
    assert "module_9/data/one.csv" in out
    assert "module_9/img/two.png" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tools/tests/test_build_colab.py::test_rewrite_double_quoted_data_path -v`
Expected: ImportError / attribute error.

- [ ] **Step 3: Add implementation to `tools/build_colab.py`**

```python
import re

# Matches 'data/...' or "data/..." and same for img/, capturing the quote.
# The path portion disallows whitespace, quotes, and path separators at start.
_PATH_RE = re.compile(r"""(['"])(data|img)/([^'"\s]+)\1""")


def rewrite_code_string_paths(source: str, module: int) -> str:
    """Rewrite every 'data/...' or 'img/...' string literal in source code
    to the corresponding GitHub raw URL for the given module.

    Only rewrites strings that begin with exactly 'data/' or 'img/' — so
    unrelated strings like 'output.csv' or 'hello world' are untouched.
    This is intentional: Colab's CWD is /content, so relative-path writes
    continue to work without rewriting.
    """
    def _sub(m: re.Match) -> str:
        quote, subdir, rest = m.group(1), m.group(2), m.group(3)
        url = build_raw_url(module, f"{subdir}/{rest}")
        return f"{quote}{url}{quote}"

    return _PATH_RE.sub(_sub, source)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 9 passed (3 prior + 6 new).

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: rewrite data/img string literals in code cells"
```

---

## Task 4: Markdown-cell path rewriting

**Files:**
- Modify: `tools/build_colab.py`
- Modify: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Append failing tests**

```python
from tools.build_colab import rewrite_markdown_paths


def test_rewrite_markdown_image():
    src = "Here's a picture:\n\n![diagram](img/foo.png)\n"
    out = rewrite_markdown_paths(src, module=7)
    assert "module_7/img/foo.png" in out
    assert "![diagram](https://raw" in out


def test_rewrite_markdown_data_link():
    src = "See [data](data/things.csv) for details."
    out = rewrite_markdown_paths(src, module=8)
    assert "module_8/data/things.csv" in out


def test_rewrite_html_img_tag_double_quoted():
    src = '<img src="img/bar.jpg" width="300">'
    out = rewrite_markdown_paths(src, module=1)
    assert 'src="https://raw' in out
    assert "module_1/img/bar.jpg" in out


def test_rewrite_html_img_tag_single_quoted():
    src = "<img src='img/bar.jpg'>"
    out = rewrite_markdown_paths(src, module=1)
    assert "src='https://raw" in out


def test_rewrite_markdown_leaves_prose_alone():
    # Unquoted mentions in prose stay as-is.
    src = "The data/ folder contains CSV files."
    out = rewrite_markdown_paths(src, module=7)
    assert out == src
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tools/tests/test_build_colab.py::test_rewrite_markdown_image -v`
Expected: ImportError.

- [ ] **Step 3: Add implementation to `tools/build_colab.py`**

```python
# ![alt](data/foo.csv) or ![alt](img/foo.png)
_MD_IMAGE_RE = re.compile(r"""(\!?\[[^\]]*\])\((data|img)/([^\s)]+)\)""")

# <img src="img/foo.png"> or <img src='img/foo.png'>
_HTML_IMG_RE = re.compile(
    r"""(<img\s[^>]*?src\s*=\s*)(['"])(data|img)/([^'"\s]+)\2""",
    flags=re.IGNORECASE,
)


def rewrite_markdown_paths(source: str, module: int) -> str:
    """Rewrite markdown image/link references and HTML <img src=> tags
    that point at 'data/...' or 'img/...' to GitHub raw URLs."""
    def _md_sub(m: re.Match) -> str:
        prefix, subdir, rest = m.group(1), m.group(2), m.group(3)
        url = build_raw_url(module, f"{subdir}/{rest}")
        return f"{prefix}({url})"

    def _html_sub(m: re.Match) -> str:
        attr, quote, subdir, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        url = build_raw_url(module, f"{subdir}/{rest}")
        return f"{attr}{quote}{url}{quote}"

    out = _MD_IMAGE_RE.sub(_md_sub, source)
    out = _HTML_IMG_RE.sub(_html_sub, out)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: rewrite data/img paths in markdown and HTML img tags"
```

---

## Task 5: Notebook metadata cleaning

**Files:**
- Modify: `tools/build_colab.py`
- Modify: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Append failing tests**

```python
import nbformat
from tools.build_colab import strip_widgets_metadata, clear_outputs


def _nb_with_widgets():
    nb = nbformat.v4.new_notebook()
    nb.metadata["widgets"] = {"application/vnd.jupyter.widget-state+json": {}}
    return nb


def test_strip_widgets_removes_key():
    nb = _nb_with_widgets()
    strip_widgets_metadata(nb)
    assert "widgets" not in nb.metadata


def test_strip_widgets_no_op_if_absent():
    nb = nbformat.v4.new_notebook()
    strip_widgets_metadata(nb)
    assert "widgets" not in nb.metadata


def test_clear_outputs_empties_code_cell_outputs():
    nb = nbformat.v4.new_notebook()
    cell = nbformat.v4.new_code_cell("print('hi')")
    cell.outputs = [{"output_type": "stream", "name": "stdout", "text": "hi\n"}]
    cell.execution_count = 3
    nb.cells.append(cell)
    clear_outputs(nb)
    assert nb.cells[0].outputs == []
    assert nb.cells[0].execution_count is None
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tools/tests/test_build_colab.py -v -k "strip_widgets or clear_outputs"`
Expected: 3 failing with ImportError.

- [ ] **Step 3: Add implementation**

```python
def strip_widgets_metadata(nb) -> None:
    """Remove the 'widgets' notebook-level metadata key, which is a legacy
    JupyterLab artifact that can crash Colab's renderer."""
    nb.metadata.pop("widgets", None)


def clear_outputs(nb) -> None:
    """Clear outputs and execution counts from all code cells."""
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: add widgets-metadata stripping and output clearing"
```

---

## Task 6: Header markdown cell builder

**Files:**
- Modify: `tools/build_colab.py`
- Modify: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Append failing tests**

```python
from tools.build_colab import build_header_cell


def test_header_cell_is_markdown():
    cell = build_header_cell(module=7, notebook_name="7_PandasDataStructure.ipynb",
                             title="Pandas Data Structures")
    assert cell.cell_type == "markdown"


def test_header_cell_contains_title():
    cell = build_header_cell(module=7, notebook_name="7_PandasDataStructure.ipynb",
                             title="Pandas Data Structures")
    assert "# Pandas Data Structures" in cell.source


def test_header_cell_contains_colab_badge():
    cell = build_header_cell(module=13, notebook_name="13_Cartopy.ipynb",
                             title="Cartopy")
    assert "colab.research.google.com/github/ixnix/" in cell.source
    assert "colab/module_13/13_Cartopy.ipynb" in cell.source
    # Standard Colab badge image
    assert "colab-badge.svg" in cell.source


def test_header_cell_mentions_zero_setup():
    cell = build_header_cell(module=1, notebook_name="1_Overview.ipynb",
                             title="Course Overview")
    assert "Google Colab" in cell.source
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tools/tests/test_build_colab.py -v -k header_cell`
Expected: ImportError for all 4.

- [ ] **Step 3: Add implementation**

```python
import nbformat


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 21 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: add Colab-badge header cell builder"
```

---

## Task 7: Cartopy install cell

**Files:**
- Modify: `tools/build_colab.py`
- Modify: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Append failing tests**

```python
from tools.build_colab import build_cartopy_install_cell


def test_cartopy_install_cell_is_code():
    cell = build_cartopy_install_cell()
    assert cell.cell_type == "code"


def test_cartopy_install_cell_runs_pip():
    cell = build_cartopy_install_cell()
    assert "!pip install" in cell.source
    assert "cartopy" in cell.source
```

- [ ] **Step 2: Run to verify failure**

Expected: ImportError.

- [ ] **Step 3: Add implementation**

```python
def build_cartopy_install_cell():
    """Build the code cell that installs cartopy — used for module 13 only."""
    return nbformat.v4.new_code_cell("!pip install -q cartopy")
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 23 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: add cartopy install cell for module 13"
```

---

## Task 8: Full notebook transform pipeline

**Files:**
- Modify: `tools/build_colab.py`
- Modify: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Append failing integration test**

```python
import nbformat
from tools.build_colab import transform_notebook


def test_transform_notebook_end_to_end(sample_notebook_path, tmp_path):
    dest = tmp_path / "out.ipynb"
    transform_notebook(
        source=sample_notebook_path,
        dest=dest,
        module=7,
        notebook_name="out.ipynb",
        title="Sample Lecture",
        include_cartopy_install=False,
    )

    nb = nbformat.read(dest, as_version=4)

    # Header cell injected at index 0.
    assert nb.cells[0].cell_type == "markdown"
    assert "# Sample Lecture" in nb.cells[0].source
    assert "colab.research.google.com" in nb.cells[0].source

    # No cartopy cell (include_cartopy_install=False).
    assert "!pip install" not in nb.cells[1].source

    # data/* and img/* have been rewritten everywhere they appeared.
    all_src = "\n".join(c.source for c in nb.cells)
    assert "data/things.csv" not in all_src.split("raw.githubusercontent.com")[0]
    assert "raw.githubusercontent.com/ixnix/GE5280PythonGeosciences" in all_src
    # Write path NOT rewritten.
    assert '"output.csv"' in all_src

    # Outputs cleared.
    for cell in nb.cells:
        if cell.cell_type == "code":
            assert cell.outputs == []
            assert cell.execution_count is None

    # Widgets metadata absent.
    assert "widgets" not in nb.metadata


def test_transform_notebook_with_cartopy(sample_notebook_path, tmp_path):
    dest = tmp_path / "out.ipynb"
    transform_notebook(
        source=sample_notebook_path,
        dest=dest,
        module=13,
        notebook_name="out.ipynb",
        title="Cartopy",
        include_cartopy_install=True,
    )
    nb = nbformat.read(dest, as_version=4)
    # Cartopy install cell injected at index 1 (right after header).
    assert nb.cells[1].cell_type == "code"
    assert "!pip install -q cartopy" in nb.cells[1].source
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tools/tests/test_build_colab.py::test_transform_notebook_end_to_end -v`
Expected: ImportError.

- [ ] **Step 3: Add implementation**

```python
from pathlib import Path


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

    # Rewrite existing cells.
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.source = rewrite_code_string_paths(cell.source, module)
        elif cell.cell_type == "markdown":
            cell.source = rewrite_markdown_paths(cell.source, module)

    # Clean metadata + outputs.
    strip_widgets_metadata(nb)
    clear_outputs(nb)

    # Inject header (always) and cartopy install (conditional).
    injected = [build_header_cell(module, notebook_name, title)]
    if include_cartopy_install:
        injected.append(build_cartopy_install_cell())
    nb.cells = injected + nb.cells

    dest.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, dest)
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 25 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: assemble full notebook transform pipeline"
```

---

## Task 9: Pre-flight validation of referenced files

**Files:**
- Modify: `tools/build_colab.py`
- Modify: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Append failing tests**

```python
import pytest
from tools.build_colab import collect_referenced_paths, validate_references


def test_collect_references_finds_code_and_markdown_paths(sample_notebook_path):
    refs = collect_referenced_paths(sample_notebook_path)
    assert "data/things.csv" in refs
    assert "img/foo.png" in refs
    assert "img/bar.jpg" in refs
    assert "img/baz.png" in refs
    # Write paths (without data/ or img/ prefix) are not treated as references.
    assert "output.csv" not in refs


def test_validate_references_raises_on_missing(tmp_path):
    module_dir = tmp_path / "module_7"
    (module_dir / "data").mkdir(parents=True)
    # NB references "data/missing.csv" but we didn't create it.
    with pytest.raises(FileNotFoundError, match="module_7.*missing.csv"):
        validate_references({"data/missing.csv"}, module_dir)


def test_validate_references_passes_when_present(tmp_path):
    module_dir = tmp_path / "module_7"
    (module_dir / "data").mkdir(parents=True)
    (module_dir / "data" / "x.csv").write_text("")
    validate_references({"data/x.csv"}, module_dir)  # no exception
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tools/tests/test_build_colab.py -v -k "references"`
Expected: 3 failing with ImportError.

- [ ] **Step 3: Add implementation**

```python
def collect_referenced_paths(source: Path) -> set[str]:
    """Scan a notebook for every 'data/...' or 'img/...' string/link.
    Returns a set of relative paths (e.g., {'data/foo.csv', 'img/bar.png'})."""
    nb = nbformat.read(source, as_version=4)
    refs: set[str] = set()
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


def validate_references(refs: set[str], module_dir: Path) -> None:
    """Raise FileNotFoundError if any referenced path is missing on disk."""
    missing = [r for r in refs if not (module_dir / r).exists()]
    if missing:
        raise FileNotFoundError(
            f"{module_dir}: referenced file(s) missing: {sorted(missing)}"
        )
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 28 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: validate referenced data/img files exist before rewriting"
```

---

## Task 10: Landing page generator

**Files:**
- Modify: `tools/build_colab.py`
- Modify: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Append failing tests**

```python
from tools.build_colab import build_landing_page, MODULES


def test_modules_list_is_complete():
    # 14 modules, each with a lecture notebook name and a topic title.
    assert len(MODULES) == 14
    assert MODULES[0]["number"] == 1
    assert MODULES[13]["number"] == 14


def test_landing_page_has_all_modules():
    md = build_landing_page()
    for i in range(1, 15):
        assert f"module_{i}/" in md


def test_landing_page_has_open_in_colab_links():
    md = build_landing_page()
    assert md.count("colab.research.google.com/github/ixnix") >= 28
    assert "colab/module_13/13_Cartopy.ipynb" in md


def test_landing_page_mentions_syllabus():
    md = build_landing_page()
    assert "Syllabus.ipynb" in md
```

- [ ] **Step 2: Run to verify failure**

Expected: ImportError.

- [ ] **Step 3: Add implementation**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 32 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: generate colab/README.md landing page"
```

---

## Task 11: CLI and orchestration

**Files:**
- Modify: `tools/build_colab.py`
- Modify: `tools/tests/test_build_colab.py`

- [ ] **Step 1: Append failing tests**

```python
import subprocess
import sys
from pathlib import Path
from tools.build_colab import build_all, MODULES

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_all_produces_expected_files(tmp_path, monkeypatch):
    # Run against the real repo, write output to tmp_path.
    build_all(
        repo_root=REPO_ROOT,
        output_dir=tmp_path,
        only_module=None,
    )
    assert (tmp_path / "README.md").exists()
    # Lecture + assignment for every module.
    for m in MODULES:
        num = m["number"]
        assert (tmp_path / f"module_{num}" / m["lecture"]).exists()
        assert (tmp_path / f"module_{num}" / f"Assignment_{num}.ipynb").exists()
    # Syllabus in module 1.
    assert (tmp_path / "module_1" / "Syllabus.ipynb").exists()


def test_build_all_only_module(tmp_path):
    build_all(repo_root=REPO_ROOT, output_dir=tmp_path, only_module=2)
    assert (tmp_path / "module_2" / "2_Variables.ipynb").exists()
    # Other modules absent.
    assert not (tmp_path / "module_3").exists()


def test_cli_dry_run_writes_nothing(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "tools.build_colab",
         "--dry-run", "--output-dir", str(tmp_path)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0
    # --dry-run reports planned actions but creates nothing.
    assert not any(tmp_path.iterdir())
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tools/tests/test_build_colab.py -v -k "build_all or cli"`
Expected: 3 failing with ImportError.

- [ ] **Step 3: Add implementation**

```python
import argparse
import shutil
import sys


def _lecture_notebooks_for(module: dict) -> list[tuple[str, str, bool]]:
    """Return list of (notebook_name, title, include_cartopy) for one module.
    Covers lecture, any extras (e.g., Syllabus), and the matching assignment."""
    num = module["number"]
    include_cartopy = (num == 13)
    items: list[tuple[str, str, bool]] = []
    items.append((module["lecture"], module["title"], include_cartopy))
    for extra in module.get("extras", []):
        # Title for the extra — drop the .ipynb and prettify.
        items.append((extra, extra.replace(".ipynb", ""), include_cartopy))
    assignment = f"Assignment_{num}.ipynb"
    items.append((assignment, f"Assignment {num}: {module['title']}",
                  include_cartopy))
    return items


def build_all(repo_root: Path, output_dir: Path, only_module: int | None) -> None:
    """Generate all Colab copies. If output_dir exists, it will be replaced."""
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


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Colab-ready notebook copies.")
    p.add_argument("--module", type=int, default=None,
                   help="Only rebuild this module (1-14).")
    p.add_argument("--output-dir", type=Path, default=Path("colab"),
                   help="Where to write output (default: ./colab).")
    p.add_argument("--dry-run", action="store_true",
                   help="List planned actions, write nothing.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_build_colab.py -v`
Expected: 35 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build_colab.py tools/tests/test_build_colab.py
git commit -m "tools: add build_colab.py CLI and directory orchestration"
```

---

## Task 12: First real build and manual smoke check

**Files:**
- Create: `colab/` (via running the generator)

- [ ] **Step 1: Run the generator on the actual repo**

Run: `python -m tools.build_colab`
Expected: prints `Wrote Colab copies to colab`; no errors.

- [ ] **Step 2: Sanity check the output tree**

Run: `find colab -type f | sort`
Expected: 29 `.ipynb` files + `colab/README.md` = 30 files. Specifically:
- `colab/module_1/1_Overview.ipynb`, `Syllabus.ipynb`, `Assignment_1.ipynb`
- `colab/module_2/2_Variables.ipynb`, `Assignment_2.ipynb`
- ... (one lecture + one assignment per module, plus Syllabus in module_1)
- `colab/README.md`

- [ ] **Step 3: Spot-check a data-heavy notebook**

Open `colab/module_7/7_PandasDataStructure.ipynb` in any viewer (VS Code, JupyterLab, `less`). Verify:
- First cell is a markdown cell starting with `# Pandas Data Structures` and the Open-in-Colab badge.
- No `!pip install` cell (module 7 doesn't need cartopy).
- Every `pd.read_csv("data/...")` has been rewritten to `pd.read_csv("https://raw.githubusercontent.com/ixnix/...")`.
- Markdown image references point to raw.githubusercontent.com URLs.
- File-write paths like `"PSArrival.csv"` are unchanged.

- [ ] **Step 4: Spot-check module 13 (cartopy)**

Open `colab/module_13/13_Cartopy.ipynb`. Verify:
- Cell 0: header markdown.
- Cell 1: `!pip install -q cartopy` code cell.
- Cells 2+: rewritten original content.

- [ ] **Step 5: Spot-check the landing page**

Open `colab/README.md`. Verify:
- 15 table rows (14 modules + 1 Syllabus extra in module 1).
- Every "Open in Colab" link contains `colab.research.google.com/github/ixnix/GE5280PythonGeosciences/blob/main/colab/module_N/...`.

If any spot-check fails, fix the generator, re-run, and spot-check again before committing.

- [ ] **Step 6: Commit generated output**

```bash
git add colab/
git commit -m "tools: first generated Colab-ready notebook copies"
```

---

## Task 13: URL extractor for the tester

**Files:**
- Create: `tools/test_colab.py`
- Create: `tools/tests/test_test_colab.py`

- [ ] **Step 1: Write failing tests in `tools/tests/test_test_colab.py`**

```python
import nbformat
from pathlib import Path
from tools.test_colab import extract_urls


def test_extract_urls_from_code_cell(tmp_path):
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell(
        'pd.read_csv("https://raw.githubusercontent.com/ixnix/GE5280Py'
        'thonGeosciences/main/module_7/data/earthquake.txt")'
    ))
    path = tmp_path / "n.ipynb"
    nbformat.write(nb, path)
    urls = extract_urls(path)
    assert any("raw.githubusercontent.com" in u for u in urls)


def test_extract_urls_from_markdown(tmp_path):
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_markdown_cell(
        "![badge](https://colab.research.google.com/assets/colab-badge.svg)\n"
        "[Open in Colab](https://colab.research.google.com/github/foo/bar/blob/main/x.ipynb)"
    ))
    path = tmp_path / "n.ipynb"
    nbformat.write(nb, path)
    urls = extract_urls(path)
    assert any("colab-badge.svg" in u for u in urls)
    assert any("colab.research.google.com/github/foo" in u for u in urls)


def test_extract_urls_deduplicates(tmp_path):
    nb = nbformat.v4.new_notebook()
    url = "https://raw.githubusercontent.com/a/b/main/c.csv"
    nb.cells.append(nbformat.v4.new_code_cell(f'x = "{url}"\ny = "{url}"'))
    path = tmp_path / "n.ipynb"
    nbformat.write(nb, path)
    urls = extract_urls(path)
    assert urls.count(url) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tools/tests/test_test_colab.py -v`
Expected: collection / import error.

- [ ] **Step 3: Create `tools/test_colab.py` with the minimal implementation**

```python
"""Tester for Colab-ready notebook copies.

Two phases:
  1. URL reachability  — HEAD every raw/Colab URL, verify 2xx.
  2. Execution         — run each notebook in a Colab-like venv via nbconvert.
"""
from __future__ import annotations

import re
from pathlib import Path

import nbformat

_URL_RE = re.compile(r"https?://[^\s'\"<>)\]]+")


def extract_urls(notebook_path: Path) -> list[str]:
    """Return a de-duplicated, source-order list of URLs in a notebook."""
    nb = nbformat.read(notebook_path, as_version=4)
    seen: set[str] = set()
    ordered: list[str] = []
    for cell in nb.cells:
        for m in _URL_RE.finditer(cell.source):
            url = m.group(0).rstrip(".,)")
            if url not in seen:
                seen.add(url)
                ordered.append(url)
    return ordered
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_test_colab.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/test_colab.py tools/tests/test_test_colab.py
git commit -m "tools: add URL extractor for test_colab"
```

---

## Task 14: URL reachability check

**Files:**
- Modify: `tools/test_colab.py`
- Modify: `tools/tests/test_test_colab.py`

- [ ] **Step 1: Append failing tests**

```python
from unittest.mock import patch, Mock
from tools.test_colab import check_url_reachable


def test_check_url_ok_head():
    resp = Mock(status_code=200)
    with patch("tools.test_colab.requests.head", return_value=resp) as mhead:
        assert check_url_reachable("https://x/y.csv") is True
        mhead.assert_called_once()


def test_check_url_falls_back_to_get_on_405():
    head_resp = Mock(status_code=405)
    get_resp = Mock(status_code=200)
    with patch("tools.test_colab.requests.head", return_value=head_resp), \
         patch("tools.test_colab.requests.get", return_value=get_resp) as mget:
        assert check_url_reachable("https://x/y.csv") is True
        mget.assert_called_once()


def test_check_url_404_is_false():
    resp = Mock(status_code=404)
    with patch("tools.test_colab.requests.head", return_value=resp):
        assert check_url_reachable("https://x/y.csv") is False


def test_check_url_retries_once_on_exception():
    import requests as _requests
    side_effects = [_requests.ConnectionError("flake"), Mock(status_code=200)]
    with patch("tools.test_colab.requests.head", side_effect=side_effects) as mhead:
        assert check_url_reachable("https://x/y.csv") is True
        assert mhead.call_count == 2
```

- [ ] **Step 2: Run to verify failure**

Expected: ImportError.

- [ ] **Step 3: Add implementation**

```python
import requests


def check_url_reachable(url: str, *, timeout: float = 10.0) -> bool:
    """HEAD the URL, falling back to a tiny GET if HEAD is rejected.
    One retry on connection error. Returns True on 2xx, False otherwise."""
    for attempt in range(2):
        try:
            resp = requests.head(url, allow_redirects=True, timeout=timeout)
            if resp.status_code == 405:  # method not allowed → try GET
                resp = requests.get(url, stream=True, timeout=timeout)
            return 200 <= resp.status_code < 300
        except requests.RequestException:
            if attempt == 1:
                return False
    return False
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_test_colab.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/test_colab.py tools/tests/test_test_colab.py
git commit -m "tools: add URL reachability check with GET fallback and retry"
```

---

## Task 15: Private-repo 404 banner detection

**Files:**
- Modify: `tools/test_colab.py`
- Modify: `tools/tests/test_test_colab.py`

- [ ] **Step 1: Append failing tests**

```python
from tools.test_colab import looks_like_private_repo


def test_private_repo_banner_triggers_when_majority_raw_404():
    results = [
        ("https://raw.githubusercontent.com/x/y/main/a", False),
        ("https://raw.githubusercontent.com/x/y/main/b", False),
        ("https://raw.githubusercontent.com/x/y/main/c", False),
        ("https://colab.research.google.com/github/x/y/blob/main/a", True),
    ]
    assert looks_like_private_repo(results) is True


def test_private_repo_banner_does_not_trigger_when_most_pass():
    results = [
        ("https://raw.githubusercontent.com/x/y/main/a", True),
        ("https://raw.githubusercontent.com/x/y/main/b", True),
        ("https://raw.githubusercontent.com/x/y/main/c", False),
    ]
    assert looks_like_private_repo(results) is False


def test_private_repo_banner_ignores_non_raw_urls():
    results = [
        ("https://example.com/a", False),
        ("https://example.com/b", False),
    ]
    assert looks_like_private_repo(results) is False
```

- [ ] **Step 2: Run to verify failure**

Expected: ImportError.

- [ ] **Step 3: Add implementation**

```python
def looks_like_private_repo(results: list[tuple[str, bool]]) -> bool:
    """Given [(url, reachable), ...] results, return True if a majority of
    raw.githubusercontent.com URLs failed — the signature of a private repo."""
    raw = [ok for url, ok in results if "raw.githubusercontent.com" in url]
    if not raw:
        return False
    failures = sum(1 for ok in raw if not ok)
    return failures > len(raw) / 2
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_test_colab.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/test_colab.py tools/tests/test_test_colab.py
git commit -m "tools: detect private-repo 404 pattern and warn user"
```

---

## Task 16: colab_requirements.txt (pinned venv)

**Files:**
- Create: `tools/colab_requirements.txt`

- [ ] **Step 1: Look up current Colab package versions**

Open a fresh Colab notebook in a browser, run in separate cells:

```python
import numpy, pandas, matplotlib, seaborn, scipy, IPython
for m in (numpy, pandas, matplotlib, seaborn, scipy, IPython):
    print(m.__name__, m.__version__)
!pip show cartopy | grep -E '^(Name|Version):' || echo "cartopy not preinstalled"
```

Record the printed versions.

- [ ] **Step 2: Write `tools/colab_requirements.txt`**

Use the versions recorded in step 1. Template:

```
# Versions pinned to match Google Colab defaults as of 2026-04-21.
# Update by rerunning the version-check snippet in tools/README.md.
numpy==<record-version>
pandas==<record-version>
matplotlib==<record-version>
seaborn==<record-version>
scipy==<record-version>
ipython==<record-version>
# jupyter ecosystem — pinned to stable recent versions, doesn't need to match Colab exactly
jupyter==1.1.1
nbconvert==7.16.4
nbformat==5.10.4
# module 13 only
cartopy==<record-version>
```

- [ ] **Step 3: Commit**

```bash
git add tools/colab_requirements.txt
git commit -m "tools: pin Colab-equivalent package versions for local testing"
```

---

## Task 17: Venv bootstrap

**Files:**
- Modify: `tools/test_colab.py`
- Modify: `tools/tests/test_test_colab.py`

- [ ] **Step 1: Append failing tests**

```python
from unittest.mock import patch
from tools.test_colab import ensure_venv


def test_ensure_venv_skips_when_exists(tmp_path):
    venv_dir = tmp_path / ".venv"
    # Simulate an already-installed venv by creating the marker.
    venv_dir.mkdir()
    (venv_dir / "bin").mkdir()
    (venv_dir / "bin" / "python").touch()
    with patch("tools.test_colab.subprocess.run") as mrun:
        ensure_venv(venv_dir=venv_dir, requirements=tmp_path / "req.txt")
        mrun.assert_not_called()


def test_ensure_venv_creates_and_installs(tmp_path):
    venv_dir = tmp_path / ".venv"
    req = tmp_path / "req.txt"
    req.write_text("numpy==2.0.0\n")

    def fake_run(cmd, *args, **kwargs):
        # Simulate that venv creation produces the python binary.
        if "venv" in cmd:
            (venv_dir / "bin").mkdir(parents=True, exist_ok=True)
            (venv_dir / "bin" / "python").touch()
        from types import SimpleNamespace
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch("tools.test_colab.subprocess.run", side_effect=fake_run) as mrun:
        ensure_venv(venv_dir=venv_dir, requirements=req)
        # Expect two calls: create venv, pip install.
        assert mrun.call_count == 2
```

- [ ] **Step 2: Run to verify failure**

Expected: ImportError.

- [ ] **Step 3: Add implementation**

```python
import subprocess
import sys as _sys


def _venv_python(venv_dir: Path) -> Path:
    if _sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_venv(venv_dir: Path, requirements: Path) -> Path:
    """Create the Colab-like venv and install requirements if not present.
    Returns the path to the venv's python interpreter."""
    python = _venv_python(venv_dir)
    if python.exists():
        return python

    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
    )
    subprocess.run(
        [str(python), "-m", "pip", "install", "-q", "-r", str(requirements)],
        check=True,
    )
    return python
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_test_colab.py -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/test_colab.py tools/tests/test_test_colab.py
git commit -m "tools: bootstrap Colab-like venv on first run"
```

---

## Task 18: Notebook execution phase

**Files:**
- Modify: `tools/test_colab.py`
- Modify: `tools/tests/test_test_colab.py`

- [ ] **Step 1: Append failing tests**

```python
from tools.test_colab import execute_notebook, ExecutionResult


def test_execute_notebook_success(tmp_path):
    nb_path = tmp_path / "n.ipynb"
    nb_path.write_text("{}")  # not actually run; subprocess is mocked

    from types import SimpleNamespace
    fake_result = SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch("tools.test_colab.subprocess.run", return_value=fake_result):
        res = execute_notebook(nb_path, python=Path("/fake/python"), timeout=120)
    assert isinstance(res, ExecutionResult)
    assert res.ok is True
    assert res.error == ""


def test_execute_notebook_failure_captures_stderr(tmp_path):
    nb_path = tmp_path / "n.ipynb"
    nb_path.write_text("{}")
    from types import SimpleNamespace
    fake_result = SimpleNamespace(
        returncode=1, stdout="", stderr="CellExecutionError: NameError: 'foo'\n"
    )
    with patch("tools.test_colab.subprocess.run", return_value=fake_result):
        res = execute_notebook(nb_path, python=Path("/fake/python"), timeout=120)
    assert res.ok is False
    assert "NameError" in res.error
```

- [ ] **Step 2: Run to verify failure**

Expected: ImportError.

- [ ] **Step 3: Add implementation**

```python
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    notebook: Path
    ok: bool
    error: str  # first line of stderr if failed, else ""


def execute_notebook(notebook: Path, *, python: Path, timeout: int) -> ExecutionResult:
    """Run a notebook with `nbconvert --execute` using the given python.
    Returns ExecutionResult(ok, error)."""
    cmd = [
        str(python), "-m", "nbconvert",
        "--to", "notebook",
        "--execute",
        "--output", f"/tmp/exec_{notebook.stem}.ipynb",
        f"--ExecutePreprocessor.timeout={timeout}",
        str(notebook),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode == 0:
        return ExecutionResult(notebook=notebook, ok=True, error="")
    err = completed.stderr.strip().splitlines()
    first = err[-1] if err else "unknown execution error"
    return ExecutionResult(notebook=notebook, ok=False, error=first)
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_test_colab.py -v`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/test_colab.py tools/tests/test_test_colab.py
git commit -m "tools: execute notebooks via nbconvert and capture errors"
```

---

## Task 19: Report generator

**Files:**
- Modify: `tools/test_colab.py`
- Modify: `tools/tests/test_test_colab.py`

- [ ] **Step 1: Append failing tests**

```python
from tools.test_colab import format_report, ExecutionResult


def test_report_has_header_row():
    md = format_report(url_results=[], exec_results=[])
    assert "| Notebook |" in md
    assert "| URL |" in md
    assert "| Exec |" in md


def test_report_marks_url_failures(tmp_path):
    md = format_report(
        url_results=[("https://a.com", False), ("https://b.com", True)],
        exec_results=[],
    )
    assert "FAIL" in md
    assert "https://a.com" in md


def test_report_marks_exec_failures(tmp_path):
    results = [
        ExecutionResult(notebook=Path("colab/module_3/x.ipynb"),
                        ok=False, error="NameError: 'foo'"),
        ExecutionResult(notebook=Path("colab/module_4/y.ipynb"),
                        ok=True, error=""),
    ]
    md = format_report(url_results=[], exec_results=results)
    assert "module_3/x.ipynb" in md
    assert "NameError" in md
    assert "PASS" in md
```

- [ ] **Step 2: Run to verify failure**

Expected: ImportError.

- [ ] **Step 3: Add implementation**

```python
def format_report(url_results: list[tuple[str, bool]],
                  exec_results: list[ExecutionResult]) -> str:
    lines = ["# Colab Tester Report", ""]

    if url_results:
        lines.append("## URL reachability")
        lines.append("")
        lines.append("| URL | Status |")
        lines.append("|-----|--------|")
        for url, ok in url_results:
            status = "PASS" if ok else "**FAIL**"
            lines.append(f"| `{url}` | {status} |")
        lines.append("")

    if exec_results:
        lines.append("## Notebook execution")
        lines.append("")
        lines.append("| Notebook | Exec | Error |")
        lines.append("|----------|------|-------|")
        for r in exec_results:
            status = "PASS" if r.ok else "**FAIL**"
            err = r.error.replace("|", "\\|")
            lines.append(f"| `{r.notebook}` | {status} | {err} |")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests**

Run: `pytest tools/tests/test_test_colab.py -v`
Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/test_colab.py tools/tests/test_test_colab.py
git commit -m "tools: format test results as markdown report"
```

---

## Task 20: Tester CLI and main

**Files:**
- Modify: `tools/test_colab.py`

- [ ] **Step 1: Add the CLI glue**

Append to `tools/test_colab.py`:

```python
import argparse


def _find_notebooks(colab_dir: Path, only_module: int | None) -> list[Path]:
    if only_module is not None:
        return sorted((colab_dir / f"module_{only_module}").glob("*.ipynb"))
    out: list[Path] = []
    for module_dir in sorted(colab_dir.glob("module_*")):
        out.extend(sorted(module_dir.glob("*.ipynb")))
    return out


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Test Colab-ready notebooks.")
    p.add_argument("--colab-dir", type=Path, default=Path("colab"))
    p.add_argument("--venv-dir", type=Path, default=Path("tools/.colab_venv"))
    p.add_argument("--requirements", type=Path,
                   default=Path("tools/colab_requirements.txt"))
    p.add_argument("--urls-only", action="store_true")
    p.add_argument("--exec-only", action="store_true")
    p.add_argument("--module", type=int, default=None)
    p.add_argument("--timeout", type=int, default=120)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else _sys.argv[1:])
    notebooks = _find_notebooks(args.colab_dir, args.module)
    if not notebooks:
        print(f"No notebooks found under {args.colab_dir}.")
        return 1

    url_results: list[tuple[str, bool]] = []
    exec_results: list[ExecutionResult] = []
    any_fail = False

    if not args.exec_only:
        print(f"Checking URLs in {len(notebooks)} notebooks...")
        all_urls: list[str] = []
        for nb in notebooks:
            all_urls.extend(extract_urls(nb))
        # Deduplicate preserving order.
        seen: set[str] = set()
        unique = [u for u in all_urls if not (u in seen or seen.add(u))]
        for url in unique:
            ok = check_url_reachable(url)
            url_results.append((url, ok))
            if not ok:
                any_fail = True
                print(f"  FAIL {url}")
        if looks_like_private_repo(url_results):
            print(
                "\n!! Most raw.githubusercontent.com URLs 404'd. "
                "The repo may still be private — make it public, or URL "
                "checks will always fail.\n"
            )

    if not args.urls_only:
        python = ensure_venv(args.venv_dir, args.requirements)
        print(f"Executing {len(notebooks)} notebooks in {python}...")
        for nb in notebooks:
            print(f"  Running {nb}")
            res = execute_notebook(nb, python=python, timeout=args.timeout)
            exec_results.append(res)
            if not res.ok:
                any_fail = True
                print(f"  FAIL {nb}: {res.error}")

    report = format_report(url_results, exec_results)
    report_path = args.colab_dir / "test_report.md"
    report_path.write_text(report)
    print(f"Wrote report to {report_path}")
    return 1 if any_fail else 0


if __name__ == "__main__":
    _sys.exit(main())
```

- [ ] **Step 2: Smoke-test the CLI with `--urls-only`**

Run: `python -m tools.test_colab --urls-only`
Expected: prints URL-check output. If the repo is still private, you'll see the private-repo banner — that's expected. The command exits nonzero if any URL failed, which is fine at this stage.

- [ ] **Step 3: Commit**

```bash
git add tools/test_colab.py
git commit -m "tools: add test_colab.py CLI main"
```

---

## Task 21: tools/README.md

**Files:**
- Create: `tools/README.md`

- [ ] **Step 1: Write `tools/README.md`**

```markdown
# Course Tooling

Two scripts generate and test Colab-ready copies of the course notebooks.

## Prerequisites

- Python 3.10+
- `pip install -r tools/dev_requirements.txt` in your main environment
- Internet access (for URL checks and venv install)
- **The repo must be public on GitHub** — Colab can only open and `raw.githubusercontent.com` can only serve public repos without extra auth.

## `tools/build_colab.py` — generator

Reads the originals in `module_1/ ... module_14/` and writes Colab-ready copies
to `colab/`. Rewrites `data/*` and `img/*` references to GitHub raw URLs,
injects an Open-in-Colab badge header, and (for module 13 only) adds a
`!pip install cartopy` cell.

```bash
# Rebuild everything
python -m tools.build_colab

# Rebuild one module while iterating
python -m tools.build_colab --module 13

# Report what would be done without writing anything
python -m tools.build_colab --dry-run
```

The generator always does a full rebuild of the chosen scope: the target
directory under `colab/` is deleted and regenerated.

## `tools/test_colab.py` — tester

Two phases, both run by default:

1. **URL reachability** — HEADs every raw and Colab URL in the generated
   notebooks. If most raw URLs 404, you'll get a banner telling you to check
   whether the repo is public.
2. **Notebook execution** — runs each generated notebook via
   `nbconvert --execute` inside a pinned venv (see below).

```bash
# Full test (both phases)
python -m tools.test_colab

# Fast: URL check only
python -m tools.test_colab --urls-only

# Skip URL check (e.g., offline or during dev before making repo public)
python -m tools.test_colab --exec-only

# One module
python -m tools.test_colab --module 13
```

Results are written to `colab/test_report.md`. Exit code is nonzero if
any check failed.

## The Colab-like venv

`tools/colab_requirements.txt` pins a small set of packages to Google
Colab's current defaults. The tester creates `tools/.colab_venv/` on first
run (~1 min). Delete that directory to force a rebuild, e.g., after bumping
versions.

### Bumping pinned versions

Open a new Colab notebook, paste:

```python
import numpy, pandas, matplotlib, seaborn, scipy, IPython
for m in (numpy, pandas, matplotlib, seaborn, scipy, IPython):
    print(m.__name__, m.__version__)
!pip show cartopy | grep -E '^(Name|Version):' || echo "cartopy not preinstalled"
```

Record the versions and update `colab_requirements.txt`.

## Known caveats

- The local venv is not byte-identical to Colab. It catches 90% of issues
  (broken URLs, missing packages, bad paths, pandas/numpy runtime errors)
  but can't catch every rendering or cartopy-on-Ubuntu quirk.
- After the tester passes, **do a one-time manual run-all in real Colab
  for module 13** (the cartopy module) to confirm the cartopy install cell
  works and the maps render.
- Cartopy local install on macOS sometimes requires `brew install geos
  proj` before pip will build the wheel. If the venv bootstrap fails on
  that, run the tester with `--urls-only` until you have time to fix it,
  or run the execution phase from a Linux machine / Docker.
```

- [ ] **Step 2: Commit**

```bash
git add tools/README.md
git commit -m "tools: document how to run build_colab and test_colab"
```

---

## Task 22: Final validation and sign-off

**Files:**
- None (manual verification)

- [ ] **Step 1: Confirm the repo is public**

Go to https://github.com/ixnix/GE5280PythonGeosciences/settings and flip
the repo visibility to Public. Without this, nothing downstream works.

- [ ] **Step 2: Push the branch**

```bash
git push
```

- [ ] **Step 3: Run the full URL check**

Run: `python -m tools.test_colab --urls-only`
Expected: every URL 200. If any 404, the private-repo banner or a
path-rewrite bug is at fault — fix before continuing.

- [ ] **Step 4: Run the full execution phase**

Run: `python -m tools.test_colab --exec-only`
Expected: all 29 notebooks pass. Cartopy failures on macOS are the
likely hiccup; see `tools/README.md` caveats.

- [ ] **Step 5: Manual Colab smoke test — module 13 (cartopy)**

Open `colab/README.md` on GitHub in a browser. Click the Open-in-Colab
link for module 13. In Colab, click Runtime → Run all. Wait ~1 minute
for the cartopy install. Verify the maps render.

- [ ] **Step 6: Manual Colab spot-check — 2 or 3 other modules**

Pick two or three of: module 1 (uses images), module 7 (uses both data
and images), module 14 (uses seaborn + images). Open each in Colab and
run all cells. Verify plots and images render.

- [ ] **Step 7: Add README link (one-time)**

Edit the root `README.md` to add a new section near the top:

```markdown
## Run in Google Colab

Every module is available as a Colab-ready notebook with zero setup.
See [`colab/README.md`](colab/README.md) for the full list of
**Open in Colab** links.
```

Commit:

```bash
git add README.md
git commit -m "docs: link to Colab-ready notebooks from root README"
git push
```

- [ ] **Step 8: Final commit for the generated `colab/` directory** (if updates from iteration)

```bash
git status
# If there are uncommitted colab/ changes from fixes during Tasks 1-21:
git add colab/
git commit -m "tools: regenerate Colab copies after final fixes"
git push
```

---

## Notes for the implementer

- **Order matters:** Tasks 2-11 can be done in the listed order with no shortcuts — later tasks import from earlier ones. Task 12 (first real build) is the first point where you'll see real output.
- **TDD discipline:** Every task writes a failing test before the implementation. Don't skip this. The regexes in Tasks 3-4 are the places where a missed edge case will silently produce broken notebooks for students.
- **When a test fails unexpectedly:** Don't try to make the test pass by changing the expected value. Either the implementation or the test-intended behavior is wrong — decide which before editing.
- **Commits:** One per task (some tasks might do multiple if a fix is needed after an integration check).
- **Don't touch originals:** `module_1/ ... module_14/` must never be modified by any script or command in this plan. The generator's blast radius is strictly limited to `colab/`.
