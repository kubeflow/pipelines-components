# Autogluon Timeseries Models Selection ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Train and select top N AutoGluon timeseries models based on leaderboard.

This component trains multiple AutoGluon TimeSeries models using TimeSeriesPredictor on the selection training data, evaluates them on the test set, and selects the top N performers based on the leaderboard ranking.

The TimeSeriesPredictor automatically trains various model types (DeepAR, TFT, ARIMA, ETS, Theta, etc.) and ranks them by the evaluation metric. This component selects the top N models from the leaderboard for refitting on the full dataset.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `target` | `str` | `None` | Name of the target column to forecast. |
| `id_column` | `str` | `None` | Name of the column identifying each time series (item_id). |
| `timestamp_column` | `str` | `None` | Name of the timestamp/datetime column. |
| `train_data_path` | `str` | `None` | Path to the selection training CSV file. |
| `test_data` | `dsl.Input[dsl.Dataset]` | `None` | Test dataset artifact for evaluation. |
| `top_n` | `int` | `None` | Number of top models to select for refitting. |
| `workspace_path` | `str` | `None` | Workspace directory where predictor will be saved. |
| `prediction_length` | `int` | `1` | Forecast horizon (number of timesteps). |
| `known_covariates_names` | `Optional[List[str]]` | `None` | Optional list of known covariate column names. |

## Outputs 📤

| Name | Type | Description |
| ---- | ---- | ----------- |
| Output | `NamedTuple('outputs', top_models=List[str], predictor_path=str, eval_metric_name=str, model_config=dict)` | top_models list, predictor_path, eval_metric_name, model_config. |

## Metadata 🗂️

- **Name**: autogluon_timeseries_models_selection
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
- **Tags**:
  - training
  - timeseries
  - automl
  - model-selection
- **Last Verified**: 2026-03-24 13:43:53+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - Mateusz-Switala
    - DorotaDR
