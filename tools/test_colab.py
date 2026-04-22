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
