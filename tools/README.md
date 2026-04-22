# Course Tooling

Two scripts generate and test Colab-ready copies of the course notebooks.

## Prerequisites

- **Python 3.11+ for `test_colab.py`** — the Colab-like venv pins scipy/pandas/matplotlib versions that require 3.10+, and cartopy wheels need 3.11+. Run the tester with a 3.11+ interpreter, e.g. `~/miniconda3/envs/pythongis/bin/python -m tools.test_colab`. The generator itself works on any 3.9+.
- `pip install -r tools/dev_requirements.txt` in your main environment (for the generator and unit tests)
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

1. **URL reachability** — HEADs every URL in the generated notebooks. If
   most raw URLs 404, you'll get a banner telling you to check whether the
   repo is public.
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

By default the tester passes `--allow-errors` to nbconvert because several
lecture notebooks intentionally demonstrate Python errors as teaching
examples (e.g., `int + str` raising TypeError in module 2). The tester
verifies "does the notebook run end-to-end" — individual in-cell errors
are preserved in the output for you to review. Use `--strict` to fail on
any in-cell error.

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
- The tester HEADs every URL it finds, including external reference links
  in the lecture notes (e.g., Wikipedia, third-party tutorials). External
  404s are informational, not actual Colab-compatibility problems.
