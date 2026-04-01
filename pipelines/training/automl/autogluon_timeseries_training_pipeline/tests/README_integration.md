# AutoGluon time series integration tests (RHOAI)

These tests mirror the tabular integration test harness and use the same
`RHOAI_*` and `AWS_*` environment variable names so they can be configured in
the same CI jobs.
For full test configuration details, see the
[tabular integration test README](../../autogluon_tabular_training_pipeline/tests/README_integration.md).

## Run

```bash
uv run pytest pipelines/training/automl/autogluon_timeseries_training_pipeline/tests/test_pipeline_integration.py -m integration -v
```

Use `RHOAI_TEST_CONFIG_TAGS` to filter scenarios by tags.
