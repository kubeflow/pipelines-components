# Autogluon Models Full Refit ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Refit a specific AutoGluon model on the full training dataset.

This component takes a trained AutoGluon TabularPredictor, loaded from predictor_path, and refits a specific model,
identified by model_name, on the full training data. When extra_train_data_path is provided, the extra training data is
loaded and passed to refit_full as train_data_extra. The test_dataset is used for evaluation and for writing metrics.
The refitted model is saved with the suffix "_FULL" appended to model_name.

Artifacts are written under model_artifact.path in a directory named <model_name>_FULL (e.g. LightGBM_BAG_L1_FULL). The
layout is:

- model_artifact.path / <model_name>_FULL / predictor / TabularPredictor (predictor.pkl inside); clone with only the
refitted model.

- model_artifact.path / <model_name>_FULL / metrics / metrics.json (evaluation results; leaderboard component reads this
via display_name/metrics/metrics.json).

- model_artifact.path / <model_name>_FULL / metrics / feature_importance.json

- model_artifact.path / <model_name>_FULL / metrics / confusion_matrix.json (classification only).

- model_artifact.path / <model_name>_FULL / notebooks / automl_predictor_notebook.ipynb

Artifact metadata: display_name (<model_name>_FULL), context (data_config, task_type, label_column, model_config,
location, metrics), and context.location.notebook (path to the notebook). Supported problem types: regression, binary,
multiclass; any other raises ValueError.

This component is typically used in a two-stage training pipeline where models are first trained on sampled data for
exploration, then the best candidates are refitted on the full dataset for optimal performance.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_name` | `str` | `None` | Name of the model to refit (must exist in predictor); refitted model saved with "_FULL" suffix. |
| `test_dataset` | `dsl.Input[dsl.Dataset]` | `None` | Dataset artifact (CSV) for evaluation and metrics; format should match initial training data. |
| `predictor_path` | `str` | `None` | Path to the trained TabularPredictor containing model_name. |
| `pipeline_name` | `str` | `None` | Pipeline run name; last hyphen-separated segment used in the generated notebook. |
| `run_id` | `str` | `None` | Pipeline run ID (used in the generated notebook). |
| `sample_row` | `str` | `None` | JSON list of row objects for example input in the notebook; label column is stripped. |
| `model_artifact` | `dsl.Output[dsl.Model]` | `None` | Output Model; artifacts under model_artifact.path/<model_name>_FULL (predictor/, metrics/, notebooks/). |
| `notebooks` | `dsl.EmbeddedInput[dsl.Dataset]` | `None` | Embedded notebook templates (injected by the runtime from the component's embedded_artifact_path). |
| `sampling_config` | `Optional[dict]` | `None` | Data sampling config (stored in artifact metadata). |
| `split_config` | `Optional[dict]` | `None` | Data split config (stored in artifact metadata). |
| `model_config` | `Optional[dict]` | `None` | Model training config (stored in artifact metadata). |
| `extra_train_data_path` | `str` | `""` | Optional path to extra training data CSV (on PVC workspace) passed to refit_full. |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `NamedTuple('outputs', model_name=str)` | NamedTuple with model_name (refitted name with "_FULL" suffix); artifacts written to model_artifact. |

## Metadata 🗂️

- **Name**: autogluon_models_full_refit
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
- **Tags**:
  - training
  - automl
  - autogluon-full-refit
- **Last Verified**: 2026-03-12 19:53:22+00:00
- **Owners**:
  - Approvers:
    - mprahl
    - nsingla
  - Reviewers:
    - HumairAK

<!-- custom-content -->
## Usage Examples 💡

### Refit top models in a pipeline (ParallelFor)

Use after the **models_selection** component: iterate over `top_models` and refit each on the same test dataset used for evaluation. Pass through config and sample row from the data loader and train/test split tasks. Use pipeline placeholders so the generated notebook shows the current run:

```python
from kfp import dsl
from kfp_components.components.training.automl.autogluon_models_full_refit import autogluon_models_full_refit

@dsl.pipeline(name="automl-full-refit-pipeline")
def my_pipeline(loader_task, split_task, selection_task):
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
            extra_train_data_path=split_task.outputs["extra_train_data_path"],
        )
    # refit_task.outputs["model_artifact"] and refit_task.outputs["model_name"] per iteration
    return refit_task
```

### Refit a single model with explicit config (regression)

Use when you have a predictor path and test dataset from earlier steps and want to refit one model by name. Config dicts are stored in artifact metadata for traceability:

```python
refit_task = autogluon_models_full_refit(
    model_name="LightGBM_BAG_L1",
    test_dataset=test_dataset_artifact,
    predictor_path="/workspace/predictor",
    sampling_config={"max_size_mb": 1024},
    split_config={"test_size": 0.2, "random_state": 42},
    model_config={"eval_metric": "root_mean_squared_error", "time_limit": 300},
    pipeline_name="my-automl-pipeline",
    run_id="run-123",
    sample_row='[{"feature1": 1.0, "target": 0.5}]',
    extra_train_data_path="/workspace/datasets/extra_train_dataset.csv",
)
```

### Refit without extra training data

When `extra_train_data_path` is empty (default), `refit_full` uses only the predictor's training and validation data:

```python
refit_task = autogluon_models_full_refit(
    model_name="LightGBM_BAG_L1",
    test_dataset=test_dataset,
    predictor_path="/workspace/autogluon_predictor",
    pipeline_name="my-automl-pipeline",
    run_id="run-123",
    sample_row='[{"feature1": 1.0, "target": 0.5}]',
)
```
