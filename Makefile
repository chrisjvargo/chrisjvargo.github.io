VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: init preprints build cv validate serve

init:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

cv:
	latexmk -pdf -interaction=nonstopmode -halt-on-error cv/Vargo_CV.tex

preprints:
	$(PY) src/sync_preprints.py --input cv/Vargo_CV.tex --csv preprints.csv

build:
	$(PY) src/build.py --input cv/Vargo_CV.tex --preprints preprints.csv --out dist

validate:
	$(PY) src/validate_build.py --dist dist --site-url https://chrisjvargo.com

serve:
	cd dist && python3 -m http.server 8000
