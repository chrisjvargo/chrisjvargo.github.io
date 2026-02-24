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
- `src/sync_preprints.py`: pulls source preprints, converts DOCX to hosted PDF, and verifies title/DOI match
- `src/templates/`: page templates
- `src/static/`: static assets
- `.github/workflows/pages.yml`: build and deploy workflow

The build generates publication detail pages at `/publications/<slug>/` and injects:
- Google Scholar/Highwire `citation_*` metadata
- Dublin Core `DC.*` metadata
- `schema.org/ScholarlyArticle` JSON-LD
- COinS (`Z3988`) metadata for Zotero/Mendeley
- Per-record downloadable citation files (`citation.bib`, `citation.ris`, `citation.json`)
- Site-wide citation exports (`/publications.bib`, `/publications.ris`, `/publications.json`)
- Atom feed (`/feed.xml`), sitemap (`/sitemap.xml`), robots (`/robots.txt`), and `/llms.txt`

## Publication Overrides
Optional file: `publication_overrides.json`

Use this to provide metadata that cannot be reliably inferred from CV citations, including:
- `abstract`, `keywords`, `no_abstract_ok`
- `online_date`, `publication_date`, `year`
- `publisher_url`, `doi`
- `version_label`
- `pdf.local_pdf_path`, `pdf.public_pdf_filename`, `pdf.external_pdf_url`
- `license.license_name`, `license.license_url`
- `open_resources.code_url`, `open_resources.data_url`, `open_resources.materials_url`

Matching keys can be set in either `by_slug` or `by_doi`.

## Preprint Mapping
File: `preprints.csv` (UTF-8, header required)

Columns:
- `doi` (optional)
- `title` (required if `doi` missing)
- `preprint_url` (required)
- `note` (optional)
- `source_url` (optional, used by sync script for provenance)
- `verify_status` (optional; only `verified`, `likely`, `manual_verified` are published)
- `verify_score` (optional)
- `verify_notes` (optional)

Matching rules:
1. DOI exact match first.
2. If no DOI, fuzzy title match against parsed CV title guess.
3. Threshold is `0.86`; ties or lower scores are left unmatched and reported.
4. Rows with `verify_status` outside `verified|likely|manual_verified` are excluded from live preprint linking.

## Make Commands
- `make init` - create `.venv`, install dependencies
- `make cv` - compile `cv/Vargo_CV.pdf` with `latexmk`
- `make preprints` - download/convert/verify preprints and rewrite `preprints.csv`
- `make build` - generate `dist/`
- `make validate` - run build output checks for required publication metadata
- `make serve` - local preview at `http://localhost:8000`

## Local Build
```bash
make init
make cv
make preprints
make build
make serve
```

## Update Workflow
1. Replace `cv/Vargo_CV.tex` with updated CV.
2. Update `preprints.csv` source links/titles as needed.
3. Run `make preprints` to host PDFs and update verification fields.
4. Run `make cv && make build`.
5. Commit and push to `main`; GitHub Actions deploys to Pages.
