# Timeseries Data Loader ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Load and split timeseries data from S3 for AutoGluon training.

This component loads time series data from S3, samples it (up to 1GB), and performs a two-stage **per-series temporal** split for efficient AutoGluon training: 1. Primary split (default 80/20): for each distinct ``id_column`` value, the earliest (1 - test_size) fraction of rows by
``timestamp_column`` goes to the train portion and the remainder to the test set (so every series with at least two rows contributes holdout data; single-row series stay in train only). 2. Secondary split (default 30/70 of each series' train rows): early segment to selection-train, later segment to
extra-train.

The test set is written to S3 artifact, while train CSVs are written to the PVC workspace for sharing across pipeline steps.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `file_key` | `str` | `None` | S3 object key of the CSV file containing time series data. |
| `bucket_name` | `str` | `None` | S3 bucket name containing the file. |
| `workspace_path` | `str` | `None` | PVC workspace directory where train CSVs will be written. |
| `target` | `str` | `None` | Name of the target column to forecast. |
| `id_column` | `str` | `None` | Name of the column identifying each time series (item_id). |
| `timestamp_column` | `str` | `None` | Name of the timestamp/datetime column. |
| `sampled_test_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output dataset artifact for the test split. |
| `selection_train_size` | `float` | `0.3` | Fraction of train portion for model selection (default: 0.3). |

## Outputs 📤

| Name | Type | Description |
| ---- | ---- | ----------- |
| Output | `NamedTuple('outputs', sample_config=dict, split_config=dict, sample_rows=str, models_selection_train_data_path=str, extra_train_data_path=str)` | sample_config, split_config, sample_rows, models_selection_train_data_path, extra_train_data_path. |

## Metadata 🗂️

- **Name**: timeseries_data_loader
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
- **Tags**:
  - data-processing
  - timeseries
  - automl
  - data-loading
- **Last Verified**: 2026-03-24 13:42:00+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - Mateusz-Switala
    - DorotaDR
