# chrisjvargo.github.io

Minimal static academic website with a LaTeX-style look (via LaTeX.css), generated from `cv/Vargo_CV.tex` and optional `preprints.csv` mappings.

## Stack
- Python 3
- Jinja2 templates
- Static HTML/CSS/JS
- GitHub Pages via GitHub Actions

No analytics, trackers, cookies, database, or client framework.

## Project Layout
- `cv/Vargo_CV.tex`: canonical LaTeX CV input
- `cv/Vargo_CV.pdf`: compiled PDF committed for lightweight CI
- `src/parse_cv.py`: parses CV into structured data
- `src/merge_preprints.py`: DOI + fuzzy title preprint matching
- `src/build.py`: renders site into `dist/`
- `src/templates/`: page templates
- `src/static/`: static assets
- `.github/workflows/pages.yml`: build and deploy workflow

## Preprint Mapping
File: `preprints.csv` (UTF-8, header required)

Columns:
- `doi` (optional)
- `title` (required if `doi` missing)
- `preprint_url` (required)
- `note` (optional)

Matching rules:
1. DOI exact match first.
2. If no DOI, fuzzy title match against parsed CV title guess.
3. Threshold is `0.86`; ties or lower scores are left unmatched and reported.

## Make Commands
- `make init` - create `.venv`, install dependencies
- `make cv` - compile `cv/Vargo_CV.pdf` with `latexmk`
- `make build` - generate `dist/`
- `make serve` - local preview at `http://localhost:8000`

## Local Build
```bash
make init
make cv
make build
make serve
```

## Update Workflow
1. Replace `cv/Vargo_CV.tex` with updated CV.
2. Update `preprints.csv`.
3. Run `make cv && make build`.
4. Commit and push to `main`; GitHub Actions deploys to Pages.
