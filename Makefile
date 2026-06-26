VENV=.venv
PY=$(shell test -x $(VENV)/bin/python && echo $(VENV)/bin/python || echo python3)
PIP=$(VENV)/bin/pip

.PHONY: init preprints build cv validate operation-audit site-visual-qa serve dv-export dv-build dv-validate dv-serve dv-test dv-audit dv-screenshots dv-release

init:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

cv:
	cd cv && latexmk -pdf -interaction=nonstopmode -halt-on-error Vargo_CV.tex

preprints:
	$(PY) src/sync_preprints.py --input cv/Vargo_CV.tex --csv preprints.csv

build:
	$(PY) src/build.py --input cv/Vargo_CV.tex --preprints preprints.csv --out dist

validate:
	$(PY) src/validate_build.py --dist dist --site-url https://chrisjvargo.com

operation-audit:
	$(PY) src/system_operation_audit.py --dist dist --out-md SYSTEM_OPERATION_GAP_REVIEW.md --out-json dist/system_operation_audit.json

site-visual-qa:
	$(PY) src/site_visual_qa.py --dist dist --out-dir dv_publication/screenshots --report dv_publication/root_cv_visual_qa_report.json --manifest dv_publication/root_cv_screenshot_manifest.csv

serve:
	cd dist && python3 -m http.server 8000

dv-export:
	test -f data/dv_public_release/release.json
	test -f data/dv_public_release/claims.json
	test -f data/dv_public_release/hypothesis_verification.csv
	test -f data/dv_public_release/SHA256SUMS

dv-build: dv-export build

dv-validate: validate

dv-serve: dv-build
	cd dist && python3 -m http.server 8000

dv-test:
	$(PY) -m unittest discover -s tests/dv -p 'test_*.py'

dv-audit: dv-test dv-build dv-validate site-visual-qa operation-audit

dv-screenshots:
	mkdir -p dv_publication/screenshots
	printf 'Screenshots are generated during browser audit runs. See dv_publication/screenshot_manifest.csv.\n' > dv_publication/screenshots/README.txt

dv-release: dv-audit
	$(PY) src/dv/hash_publication_audit.py
