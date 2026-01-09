# Component Development Best Practices

The sections below capture the minimum expectations for component and pipeline
authors. Additional guidance will be added over time as the repository matures.

## Writing Component/Pipeline Smoke Tests

- Keep test dependencies limited to `pytest` and the Python standard library.
- Place tests in a `tests/` folder that sits next to the component or pipeline
  (for example `components/training/my_component/tests/`).
- Aim for fast smoke coverage (import checks, signature validation, lightweight
  golden tests) that finishes well under the two-minute timeout enforced by
  CI.
- Run `python scripts/tests/run_component_tests.py <path-to-component>` locally
  to execute only the suites you are touching. The helper automatically enforces
  the `pytest-timeout` guardrail used in CI.

## Validating Example Pipelines

- Keep example pipelines in an `example_pipelines.py` module beside the asset.
  Every pipeline exported from the module must be decorated with
  `@dsl.pipeline`.
- The CI workflow imports each module by running
  `python -m scripts.validate_examples <paths>` for
  every changed component or pipeline and compiles the matching sample pipelines
  using `kfp.compiler`. Run the same command locally (with or without explicit
  paths) before submitting a PR to catch syntax or dependency regressions early.
- Keep the examples dependency-light; they should compile without extra
  installations beyond the repo's base tooling (`kfp`, `pytest`, stdlib).
- Import guard applies: avoid importing non-stdlib modules at module scope (with
  limited exceptions like `kfp`; `kfp_components` is allowlisted for `pipelines/**`).
  Import runtime dependencies inside the function body instead.

## Additional Topics (Coming Soon)

Future revisions of this guide will capture:

- Component design patterns
- Performance optimization
- Security best practices
- Error handling strategies
- Documentation standards
- Testing methodologies
- Container optimization
- Resource management

---

For immediate guidance, see:

- [Contributing Guide](CONTRIBUTING.md) - Complete guide with testing, setup, and workflow
- [Governance Guide](GOVERNANCE.md) - Repository policies and ownership
