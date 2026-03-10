# Tabular Train Test Split ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Splits a tabular (CSV) dataset into train and test sets for AutoML workflows.

The Train Test Split component takes a single CSV dataset and splits it into training and test sets using scikit-learn's
`train_test_split`. For **regression** tasks the split is random; for **binary** and **multiclass** tasks the split is
**stratified** by the label column by default, so that class proportions are preserved in both splits. The component
writes the train and test CSVs to the output artifacts and returns a sample row (from the test set) and the split
configuration.

By default, the split configuration uses: - `test_size`: 0.3 (30% of data for testing) - `random_state`: 42 (for
reproducibility) - `stratify`: True for "binary" and "multiclass" tasks, otherwise None

You can override these by providing the `split_config` dictionary with the corresponding keys.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dataset` | `dsl.Input[dsl.Dataset]` | `None` | Input CSV dataset to split. |
| `label_column` | `str` | `None` | Name of the label/target column. |
| `sampled_train_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output dataset artifact for the train split. |
| `sampled_test_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output dataset artifact for the test split. |
| `split_config` | `Optional[dict]` | `None` | Split configuration dictionary. Available keys: "test_size" (float), "random_state" (int), "stratify" (bool). |
| `task_type` | `str` | `regression` | Machine learning task type: "binary", "multiclass", or "regression" (default). |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `NamedTuple('outputs', sample_row=str, split_config=dict)` | Contains a sample row and a split configuration dictionary. |

## Metadata 🗂️

- **Name**: tabular_train_test_split
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
    - LukaszCmielowski
  - Reviewers:
    - Mateusz-Switala
    - DorotaDR

<!-- custom-content -->
## Split Configuration

The `split_config` dictionary parameter supports:

```python
{
    "test_size": 0.3,       # Proportion of dataset for test split (default: 0.3)
    "random_state": 42,     # Random seed for reproducibility (default: 42)
    "stratify": True        # Use stratified split for binary/multiclass (default: True)
}
```

- **Regression**: `stratify` is ignored; the split is always random.
- **Binary / multiclass**: If `stratify` is `True` (default), the split is stratified by `label_column`; if `False`, the split is random.

## Usage Examples 💡

### Regression (random split)

```python
from kfp import dsl
from kfp_components.components.data_processing.automl.tabular_train_test_split import tabular_train_test_split

@dsl.pipeline(name="train-test-split-regression-pipeline")
def my_pipeline(dataset):
    split_task = tabular_train_test_split(
        dataset=dataset,
        task_type="regression",
        label_column="price",
        split_config={"test_size": 0.3, "random_state": 42},
    )
    return split_task
```

### Classification (stratified split)

```python
@dsl.pipeline(name="train-test-split-classification-pipeline")
def my_pipeline(dataset):
    split_task = tabular_train_test_split(
        dataset=dataset,
        task_type="multiclass",
        label_column="target",
        split_config={"test_size": 0.2, "random_state": 42, "stratify": True},
    )
    return split_task
```

### Binary classification with custom test size

```python
@dsl.pipeline(name="train-test-split-binary-pipeline")
def my_pipeline(dataset):
    split_task = tabular_train_test_split(
        dataset=dataset,
        task_type="binary",
        label_column="label",
        split_config={"test_size": 0.25, "random_state": 42},
    )
    return split_task
```

### Classification with random (non-stratified) split

```python
@dsl.pipeline(name="train-test-split-random-classification-pipeline")
def my_pipeline(dataset):
    split_task = tabular_train_test_split(
        dataset=dataset,
        task_type="multiclass",
        label_column="target",
        split_config={"test_size": 0.2, "stratify": False},
    )
    return split_task
```

## Notes 📝

- **Stratified split**: Used by default for `task_type="binary"` and `"multiclass"` when `split_config["stratify"]` is `True` (default) to preserve class distribution in train and test sets.
- **Reproducibility**: Pass `random_state` in `split_config` (default: 42) for consistent splits.
- **Output format**: Train and test artifacts are written as CSV files; the component appends `.csv` to the output artifact URIs.

## Additional Resources 📚

- **AutoML Documentation**: [AutoML README](https://github.com/LukaszCmielowski/architecture-decision-records/blob/autox_arch_docs/documentation/components/automl/README.md)
- **Components Documentation**: [Components Structure](https://github.com/LukaszCmielowski/architecture-decision-records/blob/autox_arch_docs/documentation/components/automl/components.md)
- **Issue Tracker**: [GitHub Issues](https://github.com/kubeflow/pipelines-components/issues)
