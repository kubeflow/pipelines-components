RUFF ?= uv run ruff
MARKDOWNLINT ?= markdownlint
YAMLLINT ?= uv run yamllint
PYTHON ?= uv run python
PYTEST ?= uv run pytest

.PHONY: format lint lint-format lint-python lint-markdown lint-yaml lint-imports test test-coverage

format:
	$(RUFF) format components pipelines scripts
	$(RUFF) check --fix components pipelines scripts

lint: lint-format lint-python lint-markdown lint-yaml lint-imports

lint-format:
	$(RUFF) format --check components pipelines scripts

lint-python:
	$(RUFF) check components pipelines scripts

lint-markdown:
	$(MARKDOWNLINT) -c .markdownlint.json .

lint-yaml:
	$(YAMLLINT) -c .yamllint.yml .

lint-imports:
	$(PYTHON) .github/scripts/check_imports/check_imports.py --config .github/scripts/check_imports/import_exceptions.json components pipelines

test:
	cd .github/scripts && $(PYTEST) */tests/ -v $(ARGS)

test-coverage:
	cd .github/scripts && $(PYTEST) */tests/ --cov=. --cov-report=term-missing -v $(ARGS)

