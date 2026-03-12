# Tabular Train Test Split ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Splits a tabular (CSV) dataset into test, selection-train, and extra-train sets for AutoML workflows.

The Train Test Split component takes a single CSV dataset and splits it into three sets:

1. **Test set** (default 20%): written to the sampled_test_dataset S3 artifact for evaluation.

2. **Selection train set** (default 30% of the 80% train portion): written to the PVC workspace for model selection.

3. **Extra train set** (remaining 70% of the 80% train portion): written to the PVC workspace for refit_full.

For **regression** tasks the split is random; for **binary** and **multiclass** tasks the split is **stratified** by the
label column by default, so that class proportions are preserved in all splits.

By default, the split configuration uses:

- `test_size`: 0.2 (20% of data for testing)

- `random_state`: 42 (for reproducibility).

- `stratify`: True for "binary" and "multiclass" tasks, otherwise None

You can override these by providing the `split_config` dictionary with the corresponding keys.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dataset_path` | `str` | `None` | Path to the input CSV dataset (on PVC workspace). |
| `label_column` | `str` | `None` | Name of the label/target column. |
| `workspace_path` | `str` | `None` | PVC workspace directory where train CSVs will be written. |
| `sampled_test_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output dataset artifact for the test split. |
| `split_config` | `Optional[dict]` | `None` | Split configuration dictionary. Available keys: "test_size" (float), "random_state" (int), "stratify" (bool). |
| `task_type` | `str` | `regression` | Machine learning task type: "binary", "multiclass", or "regression" (default). |
| `selection_train_size` | `float` | `0.3` | Fraction of the train portion used for model selection (default 0.3). |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `NamedTuple('outputs', sample_row=str, split_config=dict, models_selection_train_path=str, extra_train_data_path=str)` | Contains a sample row, split config, and paths to selection-train and extra-train CSVs. |

## Metadata 🗂️

- **Name**: tabular_train_test_split
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
- **Tags**:
  - data-processing
- **Last Verified**: 2026-03-06 11:05:29+00:00
- **Owners**:
  - Approvers:
    - mprahl
    - nsingla
  - Reviewers:
    - HumairAK

<!-- custom-content -->
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

- 30% of train data goes to `models_selection_train.csv` (used for model selection).
- 70% of train data goes to `extra_train_dataset.csv` (passed to `refit_full` as extra training data).

## Usage Examples 💡

### Regression (random split)

```python
from kfp import dsl
from kfp_components.components.data_processing.automl.tabular_train_test_split import tabular_train_test_split

@dsl.pipeline(name="train-test-split-regression-pipeline")
def my_pipeline(dataset_path):
    split_task = tabular_train_test_split(
        dataset_path=dataset_path,
        task_type="regression",
        label_column="price",
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
        split_config={"test_size": 0.2, "random_state": 42},
    )
    # split_task.outputs["models_selection_train_path"] - PVC path for model selection training
    # split_task.outputs["extra_train_data_path"] - PVC path for extra training data (refit_full)
    # split_task.outputs["sampled_test_dataset"] - S3 artifact for test evaluation
    return split_task
```

### Classification (stratified split)

```python
@dsl.pipeline(name="train-test-split-classification-pipeline")
def my_pipeline(dataset_path):
    split_task = tabular_train_test_split(
        dataset_path=dataset_path,
        task_type="multiclass",
        label_column="target",
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
        split_config={"test_size": 0.2, "random_state": 42, "stratify": True},
    )
    return split_task
```

### Binary classification with custom test size

```python
@dsl.pipeline(name="train-test-split-binary-pipeline")
def my_pipeline(dataset_path):
    split_task = tabular_train_test_split(
        dataset_path=dataset_path,
        task_type="binary",
        label_column="label",
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
        split_config={"test_size": 0.25, "random_state": 42},
    )
    return split_task
```

### Classification with random (non-stratified) split

```python
@dsl.pipeline(name="train-test-split-random-classification-pipeline")
def my_pipeline(dataset_path):
    split_task = tabular_train_test_split(
        dataset_path=dataset_path,
        task_type="multiclass",
        label_column="target",
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
        split_config={"test_size": 0.2, "stratify": False},
    )
    return split_task
```

## Notes 📝

- **Stratified split**: Used by default for `task_type="binary"` and `"multiclass"` when `split_config["stratify"]` is `True` (default) to preserve class distribution in all splits.
- **Reproducibility**: Pass `random_state` in `split_config` (default: 42) for consistent splits.
- **Output format**: The test set is written as an S3 artifact (`.csv` appended to the URI). Selection-train and extra-train sets are written to the PVC workspace under `{workspace_path}/datasets/`.
- **Cleanup**: The input `full_dataset.csv` is deleted from the PVC workspace after splitting, since it is no longer needed and the split outputs replace it.

## Additional Resources 📚

- **AutoML Documentation**: [AutoML README](https://github.com/LukaszCmielowski/architecture-decision-records/blob/autox_arch_docs/documentation/components/automl/README.md)
- **Components Documentation**: [Components Structure](https://github.com/LukaszCmielowski/architecture-decision-records/blob/autox_arch_docs/documentation/components/automl/components.md)
- **Issue Tracker**: [GitHub Issues](https://github.com/kubeflow/pipelines-components/issues)
