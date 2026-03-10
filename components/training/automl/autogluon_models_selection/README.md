# Autogluon Models Selection ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Build multiple AutoGluon models and select top performers.

This component trains multiple machine learning models using AutoGluon's ensembling approach (stacking and bagging) on
sampled training data, then evaluates them on test data to identify the top N performing models.

The component uses AutoGluon's TabularPredictor which automatically trains various model types (neural networks,
tree-based models, linear models, etc.) and combines them using stacking with multiple levels and bagging. After
training, models are evaluated on the test dataset and ranked by performance. The top N models are selected and their
names are returned for use in subsequent refitting stages. The predictor is saved under workspace_path.

This component is part of a two-stage training pipeline where models are first built and evaluated on sampled data (for
efficiency), then the best candidates are refitted on the full dataset for optimal performance.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `label_column` | `str` | `None` | Name of the target/label column in train and test datasets. |
| `task_type` | `str` | `None` | ML task type: "binary", "multiclass", or "regression"; drives metrics and model types. |
| `top_n` | `int` | `None` | Number of top-performing models to select from the leaderboard (positive integer). |
| `train_data` | `dsl.Input[dsl.Dataset]` | `None` | Dataset artifact (CSV) with training data; must include label_column and features. |
| `test_data` | `dsl.Input[dsl.Dataset]` | `None` | Dataset artifact (CSV) for evaluation and leaderboard; schema must match train_data. |
| `workspace_path` | `str` | `None` | Workspace directory where TabularPredictor is saved (workspace_path/autogluon_predictor). |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `NamedTuple('outputs', top_models=List[str], eval_metric=str, predictor_path=str, model_config=dict)` | top_models, eval_metric, predictor_path, model_config (preset, metric, time_limit). |

## Metadata 🗂️

- **Name**: autogluon_models_selection
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
- **Tags**:
  - training
  - automl
  - autogluon-models-selection
- **Last Verified**: 2026-03-06 11:05:29+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - Mateusz-Switala
    - DorotaDR

<!-- custom-content -->
## Usage Examples 💡

### Basic usage (regression)

Train multiple AutoGluon models on train/test splits and select the top N performers; use `dsl.WORKSPACE_PATH_PLACEHOLDER` for workspace in a pipeline:

```python
from kfp import dsl
from kfp_components.components.training.automl.autogluon_models_selection import models_selection

@dsl.pipeline(name="automl-models-selection-pipeline")
def my_pipeline(train_dataset, test_dataset):
    selection_task = models_selection(
        label_column="price",
        task_type="regression",
        top_n=3,
        train_data=train_dataset,
        test_data=test_dataset,
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
    )
    return selection_task.outputs["top_models"], selection_task.outputs["predictor_path"]
```

### Classification (binary / multiclass)

```python
selection_task = models_selection(
    label_column="target",
    task_type="multiclass",
    top_n=5,
    train_data=train_test_split_task.outputs["sampled_train_dataset"],
    test_data=train_test_split_task.outputs["sampled_test_dataset"],
    workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
)
# Use selection_task.outputs["top_models"], selection_task.outputs["eval_metric"],
# selection_task.outputs["predictor_path"] for downstream refit and leaderboard.
```
