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


def extract_urls(notebook_path: Path):
    """Return a de-duplicated, source-order list of URLs in a notebook."""
    nb = nbformat.read(notebook_path, as_version=4)
    seen: set = set()
    ordered: list = []
    for cell in nb.cells:
        for m in _URL_RE.finditer(cell.source):
            url = m.group(0).rstrip(".,)")
            if url not in seen:
                seen.add(url)
                ordered.append(url)
    return ordered


import requests


def check_url_reachable(url: str, *, timeout: float = 10.0) -> bool:
    """HEAD the URL, falling back to GET if HEAD is rejected.
    One retry on connection error. Returns True on 2xx, False otherwise."""
    for attempt in range(2):
        try:
            resp = requests.head(url, allow_redirects=True, timeout=timeout)
            if resp.status_code == 405:
                resp = requests.get(url, stream=True, timeout=timeout)
            return 200 <= resp.status_code < 300
        except requests.RequestException:
            if attempt == 1:
                return False
    return False


def looks_like_private_repo(results) -> bool:
    """Given [(url, reachable), ...] results, return True if a majority of
    raw.githubusercontent.com URLs failed — the signature of a private repo."""
    raw = [ok for url, ok in results if "raw.githubusercontent.com" in url]
    if not raw:
        return False
    failures = sum(1 for ok in raw if not ok)
    return failures > len(raw) / 2


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


from dataclasses import dataclass


@dataclass
class ExecutionResult:
    notebook: Path
    ok: bool
    error: str


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


def format_report(url_results, exec_results) -> str:
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


import argparse


def _find_notebooks(colab_dir: Path, only_module):
    if only_module is not None:
        return sorted((colab_dir / f"module_{only_module}").glob("*.ipynb"))
    out = []
    for module_dir in sorted(colab_dir.glob("module_*")):
        out.extend(sorted(module_dir.glob("*.ipynb")))
    return out


def _parse_args(argv):
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


def main(argv=None) -> int:
    args = _parse_args(argv if argv is not None else _sys.argv[1:])
    notebooks = _find_notebooks(args.colab_dir, args.module)
    if not notebooks:
        print(f"No notebooks found under {args.colab_dir}.")
        return 1

    url_results = []
    exec_results = []
    any_fail = False

    if not args.exec_only:
        print(f"Checking URLs in {len(notebooks)} notebooks...")
        all_urls = []
        for nb in notebooks:
            all_urls.extend(extract_urls(nb))
        seen = set()
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
