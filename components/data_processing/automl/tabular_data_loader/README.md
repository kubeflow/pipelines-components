# Tabular Data Loader ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Automl Data Loader component.

Loads tabular (CSV) data from S3 in batches, sampling up to 1GB of data. The component reads data in chunks to
efficiently handle large files without loading the entire dataset into memory at once.

The Tabular Data Loader is typically the first step in the AutoML pipeline. It streams CSV data from an S3 bucket,
optionally samples it using one of the supported strategies, and writes the result to an output dataset artifact.
Authentication uses AWS-style credentials provided via environment variables (e.g. from a Kubernetes secret).

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_key` | `str` | `None` | S3 object key of the CSV file. |
| `bucket_name` | `str` | `None` | S3 bucket name containing the file. |
| `full_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output dataset artifact for the sampled data. |
| `sampling_method` | `Optional[str]` | `None` | "first_n_rows", "stratified", or "random"; if None, derived from task_type. |
| `label_column` | `Optional[str]` | `None` | Column name for labels/target (used for stratified sampling). |
| `task_type` | `str` | `regression` | "binary", "multiclass", or "regression" (default); used when sampling_method is None. |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `NamedTuple('outputs', sample_config=dict)` | Contains a sample configuration dictionary. |

## Metadata 🗂️

- **Name**: tabular_data_loader
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
- **Tags**:
  - data-processing
  - automl
- **Last Verified**: 2026-03-06 11:05:29+00:00
- **Owners**:
  - Approvers:
    - mprahl
    - nsingla
  - Reviewers:
    - HumairAK

<!-- custom-content -->
## Sampling strategies

Available values for the `sampling_method` parameter are:

- `"first_n_rows"`: Reads the first N rows from the file up to the component's memory limit (default 1GB).
- `"stratified"`: Samples the dataset in a way that preserves the distribution of the `label_column`. Only available if `label_column` is specified and task type is classification.
- `"random"`: Randomly samples rows from the dataset up to the size limit.

If `sampling_method` is not set, it is automatically derived from `task_type` (`"random"` for regression, `"stratified"` for classification).

## Credentials

S3 access uses environment variables (e.g. from a Kubernetes secret):

- `AWS_S3_ENDPOINT`, `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` — required for S3.

## Usage Examples 💡

### Basic usage (default: sampling from task_type)

With default parameters, `sampling_method` is derived from `task_type` (e.g. regression → random sampling):

```python
from kfp import dsl
from kfp_components.components.data_processing.automl.tabular_data_loader import automl_data_loader

@dsl.pipeline(name="automl-training-pipeline")
def my_pipeline():
    load_task = automl_data_loader(
        bucket_name="my-ml-bucket",
        file_key="data/train.csv",
        label_column="target",
        task_type="regression",
    )
    return load_task
```

### Explicit sampling method

```python
load_task = automl_data_loader(
    bucket_name="my-ml-bucket",
    file_key="data/train.csv",
    full_dataset=...,
    sampling_method="first_n_rows",
)
```

### Stratified sampling (classification)

```python
load_task = automl_data_loader(
    bucket_name="my-ml-bucket",
    file_key="data/train.csv",
    full_dataset=...,
    sampling_method="stratified",
    label_column="target",
)
```

## Supported formats and limits 📋

- **Format**: CSV only.
- **Size limit**: Up to 1GB of data in memory (sampled if larger).
- **Streaming**: Data is read in batches (10k rows per chunk) to handle large files.

## Logging 📝

The component logs at INFO level:

- Which sampling method is used (including when derived from `task_type`).
- Number of rows read and the S3 location (`bucket_name`, `file_key`).

## Additional resources 📚

- **AutoML Documentation**: [AutoML README](https://github.com/LukaszCmielowski/architecture-decision-records/blob/autox_arch_docs/documentation/components/automl/README.md)
- **Components Documentation**: [Components Structure](https://github.com/LukaszCmielowski/architecture-decision-records/blob/autox_arch_docs/documentation/components/automl/components.md)
- **Issue Tracker**: [GitHub Issues](https://github.com/kubeflow/pipelines-components/issues)
