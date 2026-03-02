# Autogluon Models Full Refit ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Refit a specific AutoGluon model on the full training dataset.

This component takes a trained AutoGluon TabularPredictor, loaded from predictor_path, and refits a specific model,
identified by model_name, on the full training data. By default AutoGluon refit_full uses the predictor's training and
validation data; the test_dataset is used for evaluation and for writing metrics. The refitted model is saved with the
suffix "_FULL" appended to model_name.

The component clones the predictor to model_artifact.path / model_name_FULL / predictor, keeps only the specified model
and its refitted version, sets the refitted model as best, and saves space by removing other models. Evaluation metrics,
feature importance, and (for classification) confusion matrix are written under model_artifact.path / model_name_FULL /
metrics. A Jupyter notebook (automl_predictor_notebook.ipynb) is written under model_artifact.path / model_name_FULL /
notebooks for inference and exploration; pipeline_name, run_id, and sample_row are used to fill in run context and
example input (the label column is stripped from sample_row in the notebook). Artifact metadata includes display_name,
context (data_config, task_type, label_column, model_config, location, metrics), and context.location.notebook.
Supported problem types are regression, binary, and multiclass; any other type raises ValueError.

This component is typically used in a two-stage training pipeline where models are first trained on sampled data for
exploration, then the best candidates are refitted on the full dataset for optimal performance.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_name` | `str` | `None` | Name of the model to refit (must exist in predictor); refitted model saved with "_FULL" suffix. |
| `test_dataset` | `dsl.Input[dsl.Dataset]` | `None` | Dataset artifact (CSV) for evaluation and metrics; format should match initial training data. |
| `predictor_path` | `str` | `None` | Path to the trained TabularPredictor containing model_name. |
| `sampling_config` | `dict` | `None` | Data sampling config (stored in artifact metadata). |
| `split_config` | `dict` | `None` | Data split config (stored in artifact metadata). |
| `model_config` | `dict` | `None` | Model training config (stored in artifact metadata). |
| `pipeline_name` | `str` | `None` | Pipeline run name; last hyphen-separated segment used in the generated notebook. |
| `run_id` | `str` | `None` | Pipeline run ID (used in the generated notebook). |
| `sample_row` | `str` | `None` | JSON list of row objects for example input in the notebook; label column is stripped. |
| `model_artifact` | `dsl.Output[dsl.Model]` | `None` | Output Model; refitted predictor, metrics, and notebook under model_artifact.path/model_name_FULL. |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `NamedTuple('outputs', model_name=str)` | NamedTuple with model_name (refitted name with "_FULL" suffix); artifacts written to model_artifact. |

## Metadata 🗂️

- **Name**: autogluon_models_full_refit
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.14.4
- **Tags**:
  - training
  - automl
  - autogluon-full-refit
- **Last Verified**: 2026-01-22 10:31:36+00:00
- **Owners**:
  - Approvers:
    - None
  - Reviewers:
    - None

<!-- custom-content -->
## Usage Examples 💡

### Refit a single model (typical in a ParallelFor)

Usually used after `models_selection`; refit each top model with the test dataset used for evaluation. Use pipeline placeholders for name and run ID:

```python
from kfp import dsl
from kfp_components.components.training.automl.autogluon_models_full_refit import autogluon_models_full_refit

@dsl.pipeline(name="automl-full-refit-pipeline")
def my_pipeline(selection_task, split_task, loader_task):
    with dsl.ParallelFor(items=selection_task.outputs["top_models"], parallelism=2) as model_name:
        refit_task = autogluon_models_full_refit(
            model_name=model_name,
            test_dataset=split_task.outputs["sampled_test_dataset"],
            predictor_path=selection_task.outputs["predictor_path"],
            sampling_config=loader_task.outputs["sample_config"],
            split_config=split_task.outputs["split_config"],
            model_config=selection_task.outputs["model_config"],
            pipeline_name=dsl.PIPELINE_JOB_RESOURCE_NAME_PLACEHOLDER,
            run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER,
            sample_row=split_task.outputs["sample_row"],
        )
    return refit_task
```

### Refit with explicit config dicts

```python
refit_task = autogluon_models_full_refit(
    model_name="LightGBM_BAG_L1",
    test_dataset=test_dataset,
    predictor_path="/workspace/autogluon_predictor",
    sampling_config={"n_samples": 10000},
    split_config={"test_size": 0.2, "random_state": 42},
    model_config={"eval_metric": "r2", "time_limit": 300},
    pipeline_name="my-automl-pipeline",
    run_id="run-123",
    sample_row='[{"feature1": 1.0, "target": 0.5}]',
)
```
