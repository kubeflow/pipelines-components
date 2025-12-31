# Component Development Best Practices

This guide captures **best practices for authoring Kubeflow Pipelines components and pipelines in this repository**.
It is grounded in the repository's **actual structure, validators, and CI checks**, and references real assets as
examples.

See also:

- [Contributing Guide](CONTRIBUTING.md)
- [Governance Guide](GOVERNANCE.md)
- [Agents Guide](AGENTS.md)

## Sources of truth (keep this doc aligned)

When this guide conflicts with other docs or enforcement, treat these as sources of truth:

- **Contribution workflow + required files**: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **Ownership / lifecycle**: [`GOVERNANCE.md`](GOVERNANCE.md)
- **Metadata requirements**: [`CONTRIBUTING.md` (metadata.yaml schema)](CONTRIBUTING.md#metadatayaml-schema) and [`GOVERNANCE.md` (verification and removal)](GOVERNANCE.md#verification-and-removal)
- **Base image policy**: [`scripts/validate_base_images/README.md`](../scripts/validate_base_images/README.md)
- **Import guard**: [`CONTRIBUTING.md` (Testing and Quality)](CONTRIBUTING.md#testing-and-quality)
- **README sync**: [`.github/workflows/readme-check.yml`](../.github/workflows/readme-check.yml) and [`scripts/generate_readme/README.md`](../scripts/generate_readme/README.md)

## Component design patterns

### Single responsibility and composability

- **Single responsibility**: a component should do one job well (download data, preprocess, train, evaluate, etc.).
- **Composable interfaces**: choose inputs/outputs that make your component reusable as a building block.
  - Prefer **typed parameters** for small values (strings, ints, floats, bools).
  - Prefer **artifacts** for files/datasets/models (e.g., `dsl.Output[dsl.Dataset]`).

Example: `components/data_processing/yoda_data_processor/component.py` writes outputs to artifact paths.

### Parameterize; avoid hidden global state

- **Parameterize configuration**: paths, thresholds, split ratios, and other knobs should be parameters.
- **Avoid implicit state**: do not rely on environment-specific defaults (cluster-specific paths, hardcoded secrets).

### Determinism and reproducibility

- **Make behavior deterministic** when possible: fixed random seeds, deterministic splits, stable ordering.
- **Record provenance**: if you load external data or models, document the source and versioning expectations.

Example: `prepare_yoda_dataset` uses a fixed seed for `train_test_split` in
`components/data_processing/yoda_data_processor/component.py`.

## Error handling

### Fail fast with actionable errors

- Prefer raising exceptions with messages that are immediately actionable for users.
- Validate inputs early (e.g., range checks like `0 <= train_split_ratio <= 1`).
- Avoid swallowing exceptions; if you catch exceptions, re-raise with context.

### Clean boundaries for external systems

- If a component calls external services (data stores, model registries, APIs), keep that logic behind an interface so
  it can be mocked in unit tests.
- Document external dependencies in `metadata.yaml` under `dependencies.external_services`.

## Logging

### Prefer structured, standard logging

- Use Python's `logging` module (stdlib) instead of ad-hoc prints when possible.
- Log high-signal events: start/end, inputs summary (no secrets), key counts, output paths, durations.
- Keep logs safe: do not log secrets, tokens, or raw user data.

Note: printing to stdout also works in KFP, and existing components use `print(...)` (e.g., `yoda_data_processor`).
For new components, prefer `logging` unless you have a reason to match an existing style in that module.

## Testing strategies

Testing in this repository falls into two categories:

- **Component/pipeline tests**: validate authored components and pipelines under `components/` and `pipelines/`.
- **Scripts tests**: validate repository tooling under `scripts/` and `.github/scripts/`.

### Component/pipeline tests

Follow the canonical testing guidance in [`CONTRIBUTING.md` (Component Testing Guide)](CONTRIBUTING.md#component-testing-guide).

Workflow reference: [`.github/workflows/component-pipeline-tests.yml`](../.github/workflows/component-pipeline-tests.yml).

Keep component/pipeline tests lightweight and maintainable:

- Put tests under `tests/` next to the asset directory (e.g., `components/<category>/<name>/tests/`).
- Prefer fast smoke coverage that completes quickly in CI.
- Keep dependencies limited to stdlib + `pytest` unless the asset truly requires more.

Example pipelines:

- If you provide example pipelines, keep them in `example_pipelines.py` next to the asset and ensure pipelines are
  decorated with `@dsl.pipeline`.
- CI validates example pipelines for changed assets via `.github/workflows/component-pipeline-tests.yml`.

### Scripts tests (repo tooling)

Follow the canonical scripts testing guidance:

- [`scripts/README.md`](../scripts/README.md)
- [`.github/scripts/README.md`](../.github/scripts/README.md)

Workflow reference: [`.github/workflows/scripts-tests.yml`](../.github/workflows/scripts-tests.yml).

## Dependency management

### Keep dependencies minimal and explicit

- Prefer minimal dependencies.
- Pin versions when possible to avoid unexpected runtime drift.

### `packages_to_install` vs custom images

- If you only need a small set of Python dependencies, prefer `@dsl.component(packages_to_install=[...])`.
- Use a custom image when:
  - You need OS-level dependencies (system packages).
  - You need a curated, reproducible environment shared across multiple components.
  - You need large dependencies that are too slow or fragile to install at runtime.

### Import guard: no non-stdlib imports at module scope

This repository enforces an import guard for `components/**` and `pipelines/**`:

- Top-level imports must be limited to **stdlib** (with allowlisted exceptions; see [`.github/scripts/check_imports/import_exceptions.yaml`](../.github/scripts/check_imports/import_exceptions.yaml)).
- Import heavy dependencies inside the component/pipeline function body.

Canonical guidance: [`CONTRIBUTING.md` (Testing and Quality)](CONTRIBUTING.md#testing-and-quality).

## Container images and base image usage

### Base image policy

Base image policy and validation rules are defined in
[`scripts/validate_base_images/README.md`](../scripts/validate_base_images/README.md).

If you need to request an exception, update the allowlist at
[`scripts/validate_base_images/base_image_allowlist.yaml`](../scripts/validate_base_images/base_image_allowlist.yaml).

### When to set `base_image`

- If the KFP SDK default image is enough, **leave `base_image` unset**.
- If you set `base_image`, ensure it passes [base image validation](../scripts/validate_base_images/README.md) and is justified by your dependencies.

## `metadata.yaml` guidelines

`metadata.yaml` defines both the technical schema for an asset and its lifecycle/verification expectations in this
repository. Use the following documents as the canonical sources of truth:

- [`CONTRIBUTING.md` (metadata.yaml schema)](CONTRIBUTING.md#metadatayaml-schema)
- [`GOVERNANCE.md` (verification and removal)](GOVERNANCE.md#verification-and-removal)

Example: `components/data_processing/yoda_data_processor/metadata.yaml`.

## Documentation requirements

### README.md is expected and is validated for sync

- Keep `README.md` in sync with component/pipeline code and metadata.
- Use the [README generator](../scripts/generate_readme/README.md) and commit the generated result (CI enforces README sync).

Tools:

- `make readme TYPE=component CATEGORY=<cat> NAME=<name>`
- `make readme TYPE=pipeline CATEGORY=<cat> NAME=<name>`

Implementation details:

- Generator module: `scripts/generate_readme/`
- Custom content marker: `<!-- custom-content -->` (preserved on regeneration)
