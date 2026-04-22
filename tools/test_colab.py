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
