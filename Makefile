VENV=.venv
PY=$(shell test -x $(VENV)/bin/python && echo $(VENV)/bin/python || echo python3)
PIP=$(VENV)/bin/pip

.PHONY: init preprints build cv validate site-visual-qa serve

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

site-visual-qa:
	$(PY) src/site_visual_qa.py --dist dist --out-dir site_qa/runtime/root_cv_screenshots --report site_qa/root_cv_visual_qa_report.json --manifest site_qa/root_cv_screenshot_manifest.csv

serve:
	cd dist && python3 -m http.server 8000
