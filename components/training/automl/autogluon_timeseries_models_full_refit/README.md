# Autogluon Timeseries Models Full Refit ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Refit a single AutoGluon timeseries model on full training data.

This component takes a model selected during the selection phase and refits it on the full training dataset (selection + extra train data) for improved performance. The refitted model is optimized and saved for deployment.

The component uses a simplified/mocked implementation for demonstration.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `model_name` | `str` | `None` | Name of the model to refit. |
| `test_dataset` | `dsl.Input[dsl.Dataset]` | `None` | Test dataset artifact for evaluation. |
| `predictor_path` | `str` | `None` | Path to the predictor from selection phase. |
| `sampling_config` | `dict` | `None` | Configuration used for data sampling. |
| `split_config` | `dict` | `None` | Configuration used for data splitting. |
| `model_config` | `dict` | `None` | Model configuration from selection phase. |
| `pipeline_name` | `str` | `None` | Pipeline name for metadata. |
| `run_id` | `str` | `None` | Pipeline run ID for metadata. |
| `models_selection_train_data_path` | `str` | `None` | Path to the model-selection train split CSV (earlier segment of the train portion). |
| `extra_train_data_path` | `str` | `None` | Path to the extra train split CSV (later segment of the train portion). |
| `sample_rows` | `str` | `None` | Sample rows from test dataset as JSON string. |
| `notebooks` | `dsl.EmbeddedInput[dsl.Dataset]` | `None` | Embedded notebook templates (injected by the runtime from the component's embedded_artifact_path). |
| `model_artifact` | `dsl.Output[dsl.Model]` | `None` | Output artifact for the refitted model. |

## Metadata 🗂️

- **Name**: autogluon_timeseries_models_full_refit
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
- **Tags**:
  - training
  - timeseries
  - automl
  - model-refit
- **Last Verified**: 2026-03-25 12:00:00+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - Mateusz-Switala
    - DorotaDR
