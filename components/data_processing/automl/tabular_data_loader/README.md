# Tabular Data Loader ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Automl Data Loader component.

Loads tabular (CSV) data from S3 in batches, sampling up to 1GB of data, then splits the sampled data into test,
selection-train, and extra-train sets.

The component reads data in chunks to efficiently handle large files without loading the entire dataset into memory at
once. After sampling, it performs a two-stage split:

1. **Primary split** (default 80/20): separates a *test set* (20%, written to the ``sampled_test_dataset`` S3 artifact)
from the *train portion* (80%).

2. **Secondary split** (default 30/70 of the train portion): produces ``models_selection_train_dataset.csv`` (30%, used
for model selection) and ``extra_train_dataset.csv`` (70%, passed to ``refit_full`` as extra data). Both are written to
the PVC workspace under ``{workspace_path}/datasets/``.

For **regression** tasks the split is random; for **binary** and **multiclass** tasks the split is **stratified** by the
label column by default.

Authentication uses AWS-style credentials provided via environment variables (e.g. from a Kubernetes secret).

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_key` | `str` | `None` | S3 object key of the CSV file. |
| `bucket_name` | `str` | `None` | S3 bucket name containing the file. |
| `workspace_path` | `str` | `None` | PVC workspace directory where train CSVs will be written. |
| `label_column` | `str` | `None` | Name of the label/target column in the dataset. |
| `sampled_test_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output dataset artifact for the test split. |
| `sampling_method` | `Optional[str]` | `None` | "first_n_rows", "stratified", or "random"; if None, derived from task_type. |
| `task_type` | `str` | `regression` | "binary", "multiclass", or "regression" (default); used when sampling_method is None. |
| `split_config` | `Optional[dict]` | `None` | Split configuration dictionary. Available keys: "test_size" (float), "random_state" (int), "stratify" (bool). |
| `selection_train_size` | `float` | `0.3` | Fraction of the train portion used for model selection (default 0.3). |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `NamedTuple('outputs', sample_config=dict, split_config=dict, sample_row=str, models_selection_train_data_path=str, extra_train_data_path=str)` | Contains sample config, split config, a sample row, and paths to selection-train and extra-train CSVs. |

## Metadata 🗂️

- **Name**: tabular_data_loader
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
- **Tags**:
  - data-processing
  - automl
- **Last Verified**: 2026-03-12 19:53:22+00:00
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

## Split Configuration

The `split_config` dictionary parameter supports:

```python
{
    "test_size": 0.2,       # Proportion of dataset for test split (default: 0.2)
    "random_state": 42,     # Random seed for reproducibility (default: 42)
    "stratify": True        # Use stratified split for binary/multiclass (default: True)
}
```

- **Regression**: `stratify` is ignored; the split is always random.
- **Binary / multiclass**: If `stratify` is `True` (default), the split is stratified by `label_column`; if `False`, the split is random.

The `selection_train_size` parameter (default: 0.3) controls the secondary split of the train portion:

- 30% of train data goes to `models_selection_train_data.csv` (used for model selection).
- 70% of train data goes to `extra_train_dataset.csv` (passed to `refit_full` as extra training data).

## Credentials

S3 access uses environment variables (e.g. from a Kubernetes secret):

- `AWS_S3_ENDPOINT`, `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` — required for S3.

## Usage Examples 💡

### Basic usage (regression)

With default parameters, `sampling_method` is derived from `task_type` (e.g. regression -> random sampling). The data is sampled from S3 and split into train/test sets:

```python
from kfp import dsl
from kfp_components.components.data_processing.automl.tabular_data_loader import automl_data_loader

@dsl.pipeline(name="automl-training-pipeline")
def my_pipeline():
    load_task = automl_data_loader(
        bucket_name="my-ml-bucket",
        file_key="data/train.csv",
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
        label_column="price",
        task_type="regression",
    )
    # load_task.outputs["models_selection_train_data_path"] - PVC path for model selection training
    # load_task.outputs["extra_train_data_path"] - PVC path for extra training data (refit_full)
    # load_task.outputs["sampled_test_dataset"] - S3 artifact for test evaluation
    # load_task.outputs["sample_row"] - JSON string with one sample row from test set
    return load_task
```

### Classification with stratified split

```python
load_task = automl_data_loader(
    bucket_name="my-ml-bucket",
    file_key="data/train.csv",
    workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
    label_column="target",
    task_type="binary",
    split_config={"test_size": 0.2, "stratify": True},
)
```

### Custom split configuration

```python
load_task = automl_data_loader(
    bucket_name="my-ml-bucket",
    file_key="data/train.csv",
    workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
    label_column="target",
    task_type="regression",
    split_config={"test_size": 0.25, "random_state": 123},
)
```

### Explicit sampling method

```python
load_task = automl_data_loader(
    bucket_name="my-ml-bucket",
    file_key="data/train.csv",
    workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
    label_column="target",
    sampling_method="first_n_rows",
)
```

### Stratified sampling (classification)

```python
load_task = automl_data_loader(
    bucket_name="my-ml-bucket",
    file_key="data/train.csv",
    workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
    sampling_method="stratified",
    label_column="target",
    task_type="binary",
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
