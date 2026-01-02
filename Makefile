MARKDOWNLINT ?= markdownlint
UVRUN ?= uv run
RUFF ?= $(UVRUN) ruff
YAMLLINT ?= $(UVRUN) yamllint
PYTEST ?= $(UVRUN) pytest

.PHONY: format fix lint lint-format lint-python lint-markdown lint-yaml lint-imports test test-coverage component pipeline tests readme

format:
	$(RUFF) format components pipelines scripts
	$(RUFF) check --fix components pipelines scripts

fix: format
	@echo "Auto-fixing Python formatting and lint issues..."
	@echo "Note: Markdown and YAML issues may need manual fixes"

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
	$(UVRUN) .github/scripts/check_imports/check_imports.py --config .github/scripts/check_imports/import_exceptions.yaml components pipelines

test:
	cd .github/scripts && $(PYTEST) */tests/ -v $(ARGS)

test-coverage:
	cd .github/scripts && $(PYTEST) */tests/ --cov=. --cov-report=term-missing -v $(ARGS)

component:
	@if [ -z "$(CATEGORY)" ]; then echo "Error: CATEGORY is required. Usage: make component CATEGORY=data_processing NAME=my_component [NO_TESTS]"; exit 1; fi
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Usage: make component CATEGORY=data_processing NAME=my_component [NO_TESTS]"; exit 1; fi
	@if [ -n "$(NO_TESTS)" ]; then \
		$(UVRUN) scripts/generate_skeleton/generate_skeleton.py --type=component --category=$(CATEGORY) --name=$(NAME) --no-tests; \
	else \
		$(UVRUN) scripts/generate_skeleton/generate_skeleton.py --type=component --category=$(CATEGORY) --name=$(NAME); \
	fi

pipeline:
	@if [ -z "$(CATEGORY)" ]; then echo "Error: CATEGORY is required. Usage: make pipeline CATEGORY=training NAME=my_pipeline [NO_TESTS]"; exit 1; fi
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Usage: make pipeline CATEGORY=training NAME=my_pipeline [NO_TESTS]"; exit 1; fi
	@if [ -n "$(NO_TESTS)" ]; then \
		$(UVRUN) scripts/generate_skeleton/generate_skeleton.py --type=pipeline --category=$(CATEGORY) --name=$(NAME) --no-tests; \
	else \
		$(UVRUN) scripts/generate_skeleton/generate_skeleton.py --type=pipeline --category=$(CATEGORY) --name=$(NAME); \
	fi

tests:
	@if [ -z "$(TYPE)" ]; then echo "Error: TYPE is required. Usage: make tests TYPE=component|pipeline CATEGORY=data_processing NAME=my_component"; exit 1; fi
	@if [ -z "$(CATEGORY)" ]; then echo "Error: CATEGORY is required. Usage: make tests TYPE=component|pipeline CATEGORY=data_processing NAME=my_component"; exit 1; fi
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Usage: make tests TYPE=component|pipeline CATEGORY=data_processing NAME=my_component"; exit 1; fi
	$(UVRUN) scripts/generate_skeleton/generate_skeleton.py --type=$(TYPE) --category=$(CATEGORY) --name=$(NAME) --tests-only

readme:
	@if [ -z "$(TYPE)" ]; then echo "Error: TYPE is required. Usage: make readme TYPE=component|pipeline CATEGORY=data_processing NAME=my_component"; exit 1; fi
	@if [ -z "$(CATEGORY)" ]; then echo "Error: CATEGORY is required. Usage: make readme TYPE=component|pipeline CATEGORY=data_processing NAME=my_component"; exit 1; fi
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Usage: make readme TYPE=component|pipeline CATEGORY=data_processing NAME=my_component"; exit 1; fi
	@if [ "$(TYPE)" = "component" ]; then \
		$(UVRUN) -m scripts.generate_readme --component $(TYPE)s/$(CATEGORY)/$(NAME) --fix; \
	elif [ "$(TYPE)" = "pipeline" ]; then \
		$(UVRUN) -m scripts.generate_readme --pipeline $(TYPE)s/$(CATEGORY)/$(NAME) --fix; \
	else \
		echo "Error: TYPE must be either 'component' or 'pipeline'"; exit 1; \
	fi
