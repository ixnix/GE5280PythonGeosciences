# Colab-Ready Notebook Copies — Design Spec

**Date:** 2026-04-21
**Owner:** Xin Xi
**Course:** GE5280 — Python Programming for Geosciences
**Repo:** `ixnix/GE5280PythonGeosciences` (currently private; must be public for this to work)

## Problem

GE5280 is taught fully online to graduate students with no prior programming experience. Setting up a local Python environment (Anaconda, Jupyter, package installs) is the single biggest source of friction and support requests. We want students to open any lecture or assignment notebook in Google Colab with one click and zero setup, running on Google's infrastructure instead of their own laptops or university desktops.

## Goal

Produce a parallel `colab/` directory in the repo containing Colab-ready copies of all 29 notebooks (14 lectures + 14 assignments + 1 Syllabus). Originals remain untouched so the existing Jupyter Book build and local-Jupyter workflows keep working. Each Colab copy includes an "Open in Colab" badge; data and image references resolve to GitHub raw URLs; the one package not preinstalled on Colab (`cartopy`, module 13) gets an install cell.

A generator script builds the `colab/` copies from the originals; a tester script validates that all generated notebooks execute cleanly and that all rewritten URLs resolve.

## Non-goals

- CI/CD for automatic testing on push. Tester is run manually by the author. May be added later.
- A separate `colab` git branch. Everything lives on `main`.
- Modifying the Jupyter Book TOC to surface Colab copies. Originals remain the canonical teaching source; `colab/README.md` is the discovery point.
- Hidden solution cells in assignments, autograding, or other pedagogy features.
- Supporting JupyterLite, Binder, or other non-Colab online environments.

## Audit summary (why this design is scoped this way)

A full audit of all 29 notebooks identified exactly these Colab-incompatibilities:

- **1 non-preinstalled package:** `cartopy` (module 13 only). Everything else (numpy, pandas, matplotlib, seaborn, scipy, IPython) is on Colab by default.
- **16 data file references** across modules 6, 7, 8, 9, 10, 13, 14 — all in `module_N/data/`.
- **11 image references** (mix of markdown `![]()`, HTML `<img>`, and `IPython.display.Image(filename=...)`) across modules 1, 7, 8, 9, 14 — all in `module_N/img/`.
- **File writes** in modules 6 and 7 (e.g., `seismogram.png`, `PSArrival.csv`). Colab's CWD is `/content`, so relative-path writes work unchanged — no rewrite needed.
- **`%%writefile`** cells in modules 5 and 12 create local `.py` files (`myfuncs.py`, `Shapes.py`). Fully supported by Colab — no rewrite needed.
- **No Colab-specific anti-patterns:** no `%matplotlib notebook`, no ipywidgets, no `__file__` usage, no cross-module relative imports, no hard-coded absolute paths.

The design exploits this: the transformation is narrow (inject header, inject one install cell for module 13, rewrite strings that match `data/...` or `img/...`), so a single small generator can handle all 29 notebooks uniformly.

## Architecture

```
GE5280/
├── module_1/ ... module_14/       # originals, never modified
├── colab/                          # generated, committed to git
│   ├── README.md                   # landing page with table of Colab links
│   ├── module_1/
│   │   ├── 1_Overview.ipynb
│   │   ├── Syllabus.ipynb
│   │   └── Assignment_1.ipynb
│   ├── module_2/ ...
│   └── module_14/
├── tools/
│   ├── build_colab.py              # the generator
│   ├── test_colab.py               # URL check + execution test
│   ├── colab_requirements.txt      # pinned Colab-like venv
│   └── README.md                   # how to run
└── docs/superpowers/specs/
    └── 2026-04-21-colab-ready-notebooks-design.md  # this file
```

- `colab/` is generated output *committed to git* so Colab can open files directly from `main`.
- `tools/` is self-contained; run with `python tools/build_colab.py` and `python tools/test_colab.py`.

## Components

### 1. `tools/build_colab.py` (generator)

Reads originals from `module_*/`, writes Colab copies to `colab/module_*/`. Full rebuild by default: `colab/` is deleted and regenerated.

**Per-notebook pipeline:**

1. Load with `nbformat.read(..., as_version=4)`.
2. **Inject header cell** at index 0 — a markdown cell with:
   - H1 title (copied from the first heading in the original, or derived from filename).
   - "Open in Colab" badge linking to `https://colab.research.google.com/github/ixnix/GE5280PythonGeosciences/blob/main/colab/module_N/<notebook>.ipynb`.
   - One-line "Run on Google Colab — no setup required" note.
3. **Inject setup cell** at index 1 — only for `module_13/13_Cartopy.ipynb` and `module_13/Assignment_13.ipynb`: a code cell with `!pip install -q cartopy`.
4. **Rewrite code cell string literals.** Regex-replace quoted strings matching `(['"])(data|img)/(...)\1` with `https://raw.githubusercontent.com/ixnix/GE5280PythonGeosciences/main/module_N/{data|img}/...`. Works uniformly for `pd.read_csv`, `open`, `np.load`, `IPython.display.Image(filename=...)` because it targets the string literal, not the function call.
5. **Rewrite markdown cell image references:**
   - `![alt](img/foo.png)` → `![alt](https://raw.githubusercontent.com/...)`
   - `![alt](data/...)` → same
   - `<img src="img/foo.png">` → `<img src="https://raw.githubusercontent.com/...">`
6. **Leave file writes as-is.** Colab's CWD is `/content`, so `open('foo.csv', 'w')` writes to `/content/foo.csv` correctly. No rewrite required.
7. **Strip outputs** via `nbconvert.preprocessors.ClearOutputPreprocessor`.
8. **Remove the `widgets` notebook-metadata key** if present (a legacy JupyterLab artifact that can crash Colab).
9. **Write** to `colab/module_N/<name>.ipynb`.

**Landing page `colab/README.md`:** a markdown table with one row per module:

| Module | Topic | Lecture | Assignment |
|--------|-------|---------|------------|
| 1 | Course Overview | [Open in Colab](...) | [Open in Colab](...) |
| ... | ... | ... | ... |

Plus a short intro paragraph explaining what Colab is and how to use it (no account required beyond a Google login, free tier is more than enough for this course).

**Validation checks during generation (fail-fast):**
- Every `data/` or `img/` path referenced in any notebook must exist on disk in the corresponding `module_N/data/` or `module_N/img/` — otherwise the rewritten URL would be a 404. Fail with the offending notebook + path.
- `colab/` must be either absent or a directory with only generated content (refuse to delete if unexpected files are present).

**CLI:**
```
python tools/build_colab.py                # full rebuild
python tools/build_colab.py --module 13    # rebuild one module
python tools/build_colab.py --dry-run      # report planned actions, write nothing
```

### 2. `tools/test_colab.py` (tester)

Two phases. Exits nonzero on any failure. Writes `colab/test_report.md`.

**Phase 1 — URL reachability**
- Walk all notebooks in `colab/`.
- Extract every `https://raw.githubusercontent.com/...` URL and every `https://colab.research.google.com/github/...` URL.
- For each, issue `HEAD` (fallback to small `GET` if HEAD is rejected). One retry on network error.
- Fail any URL returning non-2xx.
- If a majority of `raw.githubusercontent.com` URLs return 404, print a banner: *"Repo may still be private — make it public, or URL checks will all fail."*

**Phase 2 — Execution in a Colab-like venv**
- On first run, create `tools/.colab_venv/` from `tools/colab_requirements.txt`:
  - Pinned versions matching Colab's current defaults (looked up at implementation time) for: `numpy`, `pandas`, `matplotlib`, `seaborn`, `scipy`, `ipython`, `jupyter`, `nbformat`, `nbconvert`, plus `cartopy` for module 13.
- For each notebook in `colab/module_*/`: run `jupyter nbconvert --to notebook --execute --output /tmp/exec_<name>.ipynb --ExecutePreprocessor.timeout=120`.
- Capture stdout/stderr and exit status per notebook.
- Emit a results table: `module | notebook | url_check | exec_check | error (first line)`.

**CLI:**
```
python tools/test_colab.py                 # full: URLs + execution
python tools/test_colab.py --urls-only     # fast path
python tools/test_colab.py --exec-only     # skip URL check
python tools/test_colab.py --module 13     # one module
python tools/test_colab.py --timeout 300   # override cell timeout
```

### 3. `tools/colab_requirements.txt`

Pinned requirements file for the Colab-like venv. Versions chosen to match Colab's current preinstalled defaults at the time of implementation. Intentionally small — only packages the course actually uses.

### 4. `tools/README.md`

Short doc:
- Prerequisites (Python 3.10+, git, network).
- `pip install nbformat nbconvert requests` in the main env (for `build_colab.py`).
- How to run each tool.
- Known caveat: the local venv isn't byte-identical to Colab; after tests pass, do a one-time manual real-Colab run-all on module_13.

## Error handling & edge cases

**Generator:**
- Missing referenced file → fail loudly with notebook name + missing path.
- Non-UTF8 notebooks → fail loudly with filename (nbformat's native error message is fine).
- Refuse to delete `colab/` if it contains unexpected files.
- Never touches anything outside `colab/`; never calls git — staging and commits are manual.
- Unquoted references to `data/...` or `img/...` in markdown prose are deliberately left alone (safer than a global replace).

**Tester:**
- Venv bootstrap failure (common: cartopy on macOS) → print clear message, suggest `--urls-only` as fallback.
- Network flake during URL check → one retry, then report the URL as failed.
- Per-cell timeout 120s (override via `--timeout`).
- All-404 pattern on raw URLs → private-repo banner (see Phase 1).

**Not validated locally** (documented in `tools/README.md`):
- Colab's matplotlib rendering parity with local.
- Colab's exact package versions vs. the pinned venv.
- Cartopy-on-Colab-Ubuntu vs. cartopy-on-local-macOS. → Why module 13 requires a one-time manual real-Colab run-all.

## Student-facing workflow

1. Student lands on repo README or Jupyter Book.
2. README links to `colab/README.md`.
3. Student clicks the "Open in Colab" badge for their module.
4. Colab opens; student runs cells (or Runtime → Run all).
5. Zero installs, zero file uploads, zero Drive setup.
6. Module 13 only: extra ~30-60s while `!pip install cartopy` runs.

## Author workflow (updating a lecture)

```
# edit module_8/8_DataWrangling.ipynb
python tools/build_colab.py --module 8
python tools/test_colab.py --module 8
git add module_8/ colab/module_8/
git commit -m "Update DataWrangling examples"
git push
```

Generator: ≤10s per module. Tester: ~1-2 min per module (notebook execution).

## Prerequisites & one-time setup

1. **Make the repo public** on GitHub. Without this, raw URLs 404 and students can't open notebooks in Colab from the GitHub link. (Alternative for private repos requires Colab-side auth — not supported by this design.)
2. `pip install nbformat nbconvert requests` in the author's main Python environment.
3. First run of `test_colab.py` creates `tools/.colab_venv/` (~1 min).
4. Add a "Run in Google Colab" section to the root `README.md` linking to `colab/README.md`. One-time manual edit — the generator never touches the root README.

## Success criteria

1. `python tools/build_colab.py` produces 29 notebooks under `colab/` + `colab/README.md` with no errors.
2. `python tools/test_colab.py --urls-only` passes 100% after repo is public.
3. `python tools/test_colab.py` (full) passes 100% locally.
4. Manual: `colab/module_13/13_Cartopy.ipynb` runs end-to-end in real Colab via the "Open in Colab" badge.
5. Manual spot-check: 2-3 other lecture notebooks render plots and images correctly in real Colab.

## Open questions

None at spec-write time. Any discovered during implementation should be raised before merging rather than resolved silently.
