# AI Agent Context Guide

*This guide provides context and information for AI agents working with the Kubeflow Pipelines Components Repository.*

See also:

- [Contributing Guide](docs/CONTRIBUTING.md)
- [Governance Guide](docs/GOVERNANCE.md)

## Sources of truth (keep this doc aligned)

If this guide conflicts with repository enforcement or process docs, treat these as sources of truth:

This guide is expected to stay current; when repository enforcement, CI, or contribution process changes (or when a
difference is noted), update `AGENTS.md` alongside the change.

- [`CONTRIBUTING.md`](docs/CONTRIBUTING.md) (required files, workflow, required metadata fields)
- [`GOVERNANCE.md`](docs/GOVERNANCE.md) (roles, ownership, lifecycle)
- [`CONTRIBUTING.md` (metadata.yaml schema)](docs/CONTRIBUTING.md#metadatayaml-schema)
- [`scripts/validate_base_images/README.md`](scripts/validate_base_images/README.md) (base image policy)
- [`CONTRIBUTING.md` (Testing and Quality)](docs/CONTRIBUTING.md#testing-and-quality)
- CI workflows live under `.github/workflows/` (example: [`.github/workflows/python-lint.yml`](.github/workflows/python-lint.yml))

## Agent modes

Agents typically interact with this repository in three modes. Use the mode to decide what you should optimize for.

1. **Contributing a component or pipeline** (authoring new assets or changing existing ones)
2. **End user building pipelines** from published components (consumption only; no repo changes)
3. **Maintaining/contributing to the repository** (scripts, tests, CI, automation)

## Quickstart (all agents)

- **Reuse-first**: search `components/<category>/` and `pipelines/<category>/` for similar functionality; prefer
  extending/composing instead of duplicating.
- **Create scaffolding**: use the Make targets in `Makefile`:
  - `make component CATEGORY=<cat> NAME=<name> [SUBCATEGORY=<sub>] [NO_TESTS=true] [CREATE_SHARED=true]`
  - `make pipeline CATEGORY=<cat> NAME=<name> [SUBCATEGORY=<sub>] [NO_TESTS=true] [CREATE_SHARED=true]`
  - `make tests TYPE=component|pipeline CATEGORY=<cat> NAME=<name> [SUBCATEGORY=<sub>]`
  - `make readme TYPE=component|pipeline CATEGORY=<cat> NAME=<name> [SUBCATEGORY=<sub>]`
- **Validate like CI**: follow [`CONTRIBUTING.md` (Testing and Quality)](docs/CONTRIBUTING.md#testing-and-quality) and
  reference the workflows under `.github/workflows/` (example: [`.github/workflows/python-lint.yml`](.github/workflows/python-lint.yml)).
- **New assets require approval**: for initial contributions (introducing a new component/pipeline to the catalog),
  follow the approval process in [`GOVERNANCE.md`](docs/GOVERNANCE.md).

## Mode 1: Contributing a component or pipeline

Goal: add or update an asset under `components/` or `pipelines/` that is reusable and passes repo validations.

### Before you generate code

#### Reuse-first: search for existing components/pipelines

Before adding anything new:

- Search under `components/<category>/` and `pipelines/<category>/` for similar functionality.
- Prefer extending or composing existing assets instead of duplicating.

Good places to look:

- `components/` and `pipelines/` category directories for similar patterns and reusable building blocks (example:
  `components/data_processing/yoda_data_processor`)
- `scripts/generate_skeleton/` (canonical templates)
- `scripts/generate_readme/` (README generation expectations)

#### Establish the target location and naming

- Components live under `components/<category>/<component_name>/`.
- Components can optionally use subcategories: `components/<category>/<subcategory>/<component_name>/`.
- Pipelines live under `pipelines/<category>/<pipeline_name>/`.
- Pipelines can optionally use subcategories: `pipelines/<category>/<subcategory>/<pipeline_name>/`.
- Use `snake_case` directory names (per `CONTRIBUTING.md`).

### Required files

When the agent changes or adds a component/pipeline directory, follow
[the required files list](docs/CONTRIBUTING.md#required-files).

### Initial contributions: Pipelines Working Group approval

For initial contributions (e.g., a new component/pipeline being introduced to the catalog), the repo requires
Pipelines Working Group approval.

For context on repository roles, decision-making, and approvals, see [`GOVERNANCE.md`](docs/GOVERNANCE.md).

Process (expected for agents):

- Open a submission issue using `.github/ISSUE_TEMPLATE/component_submission.md`.
- Get Pipelines Working Group approval in that issue (link it from the PR).
- Open a PR with the implementation.
- Follow the repo’s OWNERS-based review flow described in `CONTRIBUTING.md` (`/lgtm` + `/approve`).

### Example prompts (Mode 1)

#### Add a new component (reuse-first, compliant)

Use this prompt pattern:

"Search `components/` for similar functionality and reuse if possible. If a new component is needed, create it under
`components/<category>/<name>/` using `make component CATEGORY=<cat> NAME=<name> [NO_TESTS=true]`, then implement
`component.py` following repository lint rules (including import guard). Create `metadata.yaml` that conforms to
the metadata schema defined in [`CONTRIBUTING.md`](docs/CONTRIBUTING.md#metadatayaml-schema) (required field order, fresh `lastVerified`). Generate/validate
`README.md` using `make readme TYPE=component CATEGORY=<cat> NAME=<name>`. Add unit tests using `.python_func()` and a
LocalRunner test using `setup_and_teardown_subprocess_runner` (you can generate tests via
`make tests TYPE=component CATEGORY=<cat> NAME=<name>`). Reference an existing component like
`components/data_processing/yoda_data_processor/` for patterns."

#### Add a component in a subcategory

Use this prompt pattern when creating related components that should share ownership or utilities:

"Create a component in a subcategory using `make component CATEGORY=<cat> SUBCATEGORY=<sub> NAME=<name>`. This
automatically creates the subcategory structure with OWNERS and README.md if it doesn't exist. For shared utilities,
add `CREATE_SHARED=true` to create a `shared/` package. Update the subcategory OWNERS and README.md with appropriate
maintainers and documentation. Follow the same component implementation patterns as above."

#### Add a new pipeline (reuse-first, compliant)

Use this prompt pattern:

"Search `pipelines/` for similar functionality and reuse if possible. If a new pipeline is needed, create it under
`pipelines/<category>/<name>/` using `make pipeline CATEGORY=<cat> NAME=<name> [NO_TESTS=true]`, then implement
`pipeline.py` following repository lint rules (including import guard). Create `metadata.yaml` that conforms to the
metadata schema defined in [`CONTRIBUTING.md`](docs/CONTRIBUTING.md#metadatayaml-schema) (required field order, fresh
`lastVerified`). Generate/validate `README.md` using `make readme TYPE=pipeline CATEGORY=<cat> NAME=<name>`. Add tests
(you can generate tests via `make tests TYPE=pipeline CATEGORY=<cat> NAME=<name>`)."

#### Add a pipeline in a subcategory

Use this prompt pattern when creating related pipelines that should share ownership or utilities:

"Create a pipeline in a subcategory using `make pipeline CATEGORY=<cat> SUBCATEGORY=<sub> NAME=<name>`. This
automatically creates the subcategory structure with OWNERS and README.md if it doesn't exist. For shared utilities,
add `CREATE_SHARED=true` to create a `shared/` package. Update the subcategory OWNERS and README.md with appropriate
maintainers and documentation. Follow the same pipeline implementation patterns as above."

#### Update an existing component safely

"Find the existing component directory. Make the minimal change needed. Update docstrings and regenerate the README
if the interface changed (`make readme TYPE=component CATEGORY=<cat> NAME=<name>`). Update `metadata.yaml` only if
needed and keep `lastVerified` fresh. Add/adjust unit tests and LocalRunner tests. Ensure import guard compliance."

## Mode 2: End user building pipelines from these components

Goal: compose pipelines using components/pipelines from this repository without changing repository content.

Recommended references:

- [`README.md`](README.md) (repository overview / usage entry point)
- Component and pipeline READMEs under `components/<category>/` and `pipelines/<category>/`
- Kubeflow Pipelines docs (usage and authoring concepts): `https://www.kubeflow.org/docs/components/pipelines/`

## Mode 3: Maintaining/contributing to the repository (scripts, tests, CI)

Goal: improve repository automation and tooling under `scripts/`, `.github/scripts/`, and `.github/workflows/`.

Canonical references:

- [`scripts/README.md`](scripts/README.md)
- [`.github/scripts/README.md`](.github/scripts/README.md)
- [`.github/actions/detect-changed-assets/README.md`](.github/actions/detect-changed-assets/README.md) (run work only for changed assets in CI)

Use the same validations section below; it applies to repository maintenance changes as well.

## Repository validations an agent must satisfy

### Dependencies and pre-commit

Follow [`CONTRIBUTING.md`](docs/CONTRIBUTING.md#dependency-management-uvlock) for dependency and lockfile management, and
[`CONTRIBUTING.md`](docs/CONTRIBUTING.md#pre-commit-validation) for pre-commit guidance.

### Python lint and formatting

Python lint/format is enforced by CI on pull requests and runs against **changed files**:

- Workflow: [`.github/workflows/python-lint.yml`](.github/workflows/python-lint.yml)

This uses Ruff formatting and linting (see `pyproject.toml` for configuration).

### Markdown lint

Markdown is linted in CI on pull requests and runs against **changed files**:

- Workflow: [`.github/workflows/markdown-lint.yml`](.github/workflows/markdown-lint.yml)
- Config: [`.markdownlint.json`](.markdownlint.json)

### YAML lint

YAML is linted in CI on pull requests and runs against **changed files**:

- Workflow: [`.github/workflows/yaml-lint.yml`](.github/workflows/yaml-lint.yml)
- Config: [`.yamllint.yml`](.yamllint.yml)

### Import guard (components/pipelines)

Follow [`CONTRIBUTING.md` (Testing and Quality)](docs/CONTRIBUTING.md#testing-and-quality).
Allowlisted exceptions are defined in
[`.github/scripts/check_imports/import_exceptions.yaml`](.github/scripts/check_imports/import_exceptions.yaml).

### Metadata schema validation

Follow the canonical schema requirements in
[`CONTRIBUTING.md` (metadata.yaml schema)](docs/CONTRIBUTING.md#metadatayaml-schema).

CI workflow (reference): [`.github/workflows/validate-metadata-schema.yml`](.github/workflows/validate-metadata-schema.yml).

### Base image validation

Follow the canonical policy in
[`scripts/validate_base_images/README.md`](scripts/validate_base_images/README.md).

CI workflow (reference): [`.github/workflows/base-image-check.yml`](.github/workflows/base-image-check.yml).

### README generation and sync

Follow the canonical generator behavior in
[`scripts/generate_readme/README.md`](scripts/generate_readme/README.md) and keep READMEs in sync.

CI workflow (reference): [`.github/workflows/readme-check.yml`](.github/workflows/readme-check.yml).

### Tests

Follow the canonical testing guidance:

- Component/pipeline tests: [`CONTRIBUTING.md` (Component Testing Guide)](docs/CONTRIBUTING.md#component-testing-guide)
- Scripts tests: [`scripts/README.md`](scripts/README.md) and [`.github/scripts/README.md`](.github/scripts/README.md)

Workflow references:

- Component/pipeline tests: [`.github/workflows/component-pipeline-tests.yml`](.github/workflows/component-pipeline-tests.yml)
- Scripts tests: [`.github/workflows/scripts-tests.yml`](.github/workflows/scripts-tests.yml)
