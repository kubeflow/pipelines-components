# Leaderboard Evaluation ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Evaluate multiple AutoGluon models and generate a leaderboard.

This component aggregates evaluation results from a list of Model artifacts (reading pre-computed metrics from JSON) and generates an HTML-formatted leaderboard ranking the models by their performance metrics. Each model artifact is expected to contain metrics at model.path /
model.metadata["display_name"] / metrics / metrics.json.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `models` | `List[dsl.Model]` | `None` | List of Model artifacts with "display_name" in metadata and metrics at model.path/model_name/metrics/metrics.json. |
| `eval_metric` | `str` | `None` | Metric name for ranking (e.g. "accuracy", "root_mean_squared_error"); leaderboard sorted by it descending. |
| `html_artifact` | `dsl.Output[dsl.HTML]` | `None` | Output artifact for the HTML-formatted leaderboard (model names and metrics). |
| `embedded_artifact` | `dsl.EmbeddedInput[dsl.Artifact]` | `None` | Embedded component files (injected by runtime from embedded_artifact_path); provides leaderboard_html_template.html. |

## Outputs 📤

| Name | Type | Description |
| ---- | ---- | ----------- |
| Output | `NamedTuple('outputs', best_model=str)` |  |

## Metadata 🗂️

- **Name**: leaderboard_evaluation
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
- **Tags**:
  - leaderboard
  - automl
- **Last Verified**: 2026-03-06 11:05:29+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - Mateusz-Switala
    - DorotaDR

<!-- custom-content -->
## Usage Examples 💡

### Basic usage with collected refit model artifacts

Typical use after refitting multiple models: collect model artifacts and pass the evaluation metric from the selection stage:

```python
from kfp import dsl
from kfp_components.components.training.automl.autogluon_leaderboard_evaluation import leaderboard_evaluation

@dsl.pipeline(name="automl-leaderboard-pipeline")
def my_pipeline(refit_tasks, eval_metric):
    leaderboard_evaluation(
        models=dsl.Collected(refit_tasks.outputs["model_artifact"]),
        eval_metric=eval_metric,
    )
```

### Classification (accuracy)

```python
leaderboard_evaluation(
    models=dsl.Collected(refit_full_task.outputs["model_artifact"]),
    eval_metric="accuracy",
)
```

### Regression (RMSE)

```python
leaderboard_evaluation(
    models=dsl.Collected(refit_full_task.outputs["model_artifact"]),
    eval_metric="root_mean_squared_error",
)
```
