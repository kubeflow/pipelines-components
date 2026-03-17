# Autogluon Tabular Training Pipeline ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

AutoGluon Tabular Training Pipeline.

This pipeline implements an efficient two-stage training approach for AutoGluon tabular models that balances
computational cost with model quality. The pipeline automates the complete machine learning workflow from data loading
to final model evaluation.

**Storage strategy:**

Training datasets are stored on a PVC workspace (not S3 artifacts) so that all pipeline steps sharing the workspace can
access them without extra downloads. Only the test dataset is written to an S3 artifact (for use by the leaderboard
evaluation component). The workspace is provisioned via ``PipelineConfig.workspace``.

**Pipeline Stages:**

1. **Data Loading & Splitting**: Loads tabular (CSV) data from an S3-compatible object storage bucket using AWS
credentials configured via Kubernetes secrets. The component samples the data (up to 1GB), then performs a two-stage
split: *Primary split** (default 80/20): separates a *test set* (20%, written to an S3 artifact) from the *train
portion* (80%). **Secondary split** (default 30/70 of the train portion): produces
``models_selection_train_dataset.csv`` (30%, used for model selection) and ``extra_train_dataset.csv`` (70%, passed to
``refit_full`` as extra data). Both train CSVs are written to the PVC workspace under ``{workspace_path}/datasets/``.
For classification tasks the splits are stratified by the label column.

2. **Model Selection**: Trains multiple AutoGluon models on the *selection train* data using AutoGluon's ensembling
approach (stacking with 3 levels and bagging with 2 folds). The component automatically trains various model types
including neural networks, tree-based models (XGBoost, LightGBM, CatBoost), and linear models. All models are evaluated
on the test set and ranked by performance. The top N models are selected for the refitting stage.

3. **Model Refitting**: Refits each of the top N selected models on the predictor's training and validation data,
augmented with the *extra train* split via ``refit_full(train_data_extra=...)``. This stage runs in parallel (with
parallelism of 2) to efficiently retrain multiple models. Each refitted model is saved with a "_FULL" suffix and
optimized for deployment by removing unnecessary models and files.

4. **Leaderboard Evaluation**: Aggregates evaluation results from all refitted model artifacts (each refit component
writes metrics to model_artifact.path / model_name_FULL / metrics). The leaderboard component reads these pre-computed
metrics and generates an HTML-formatted leaderboard ranking models by their performance metrics for comparison and
selection.

**Two-Stage Training Benefits:**

- **Efficient Exploration:** Initial model training uses a smaller selection-train split with efficient ensembling
rather than expensive hyperparameter optimization.

- **Optimal Performance:** Final models are refitted (``refit_full``) on the predictor's training and validation data
plus the extra-train split, maximizing the amount of data seen during the final fit.

- **Parallel Efficiency:** Top models are refitted in parallel to minimize total pipeline execution time.

- **Production-Ready:** Refitted models are AutoGluon Predictors optimized and ready for deployment.

**AutoGluon Ensembling Approach:**

The pipeline leverages AutoGluon's unique ensembling strategy that combines multiple model types using stacking and
bagging rather than traditional hyperparameter optimization. This approach is more efficient and typically produces
better results for tabular data by automatically:

- Training diverse model families

- Combining predictions using multi-level stacking

- Using bootstrap aggregation (bagging) for robustness

- Selecting optimal ensemble configurations

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `train_data_secret_name` | `str` | `None` | Kubernetes secret name with S3 credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, AWS_DEFAULT_REGION). |
| `train_data_bucket_name` | `str` | `None` | S3-compatible bucket name containing the tabular data file. |
| `train_data_file_key` | `str` | `None` | S3 object key of the CSV file (features and target column). |
| `label_column` | `str` | `None` | Name of the target/label column in the dataset. |
| `task_type` | `str` | `None` | "binary", "multiclass", or "regression"; drives metrics and model types. |
| `top_n` | `int` | `3` | Number of top models to select and refit (default: 3); positive integer. |

## Metadata 🗂️

- **Name**: autogluon_tabular_training_pipeline
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
    - Name: Kubernetes, Version: >=1.28.0
- **Tags**:
  - training
  - pipeline
  - automl
  - autogluon-tabular-training-pipeline
- **Last Verified**: 2026-03-12 19:53:22+00:00
- **Owners**:
  - Approvers:
    - mprahl
    - nsingla
  - Reviewers:
    - HumairAK

<!-- custom-content -->
### Storage layout

The pipeline writes data to two storage locations:

1. **PVC workspace** — training datasets and the AutoGluon predictor are stored on a shared PVC so that all pipeline steps can access them without extra S3 downloads.
2. **S3 artifact store** — the test dataset, refitted model artifacts, and the HTML leaderboard are written to S3-compatible storage configured for Kubeflow Pipelines.

#### PVC workspace layout

```text
{workspace_path}/
└── datasets/
    ├── models_selection_train_dataset.csv    # 30% of the train portion (used for model selection)
    └── extra_train_dataset.csv       # 70% of the train portion (passed to refit_full)
```

#### S3 artifact store layout

```text
<pipeline_name>/
└── <run_id>/
    ├── leaderboard-evaluation/
    │   └── <task_id>/
    │       └── html_artifact                     # HTML leaderboard (model names + metrics)
    ├── autogluon-models-full-refit/
    │   └── <task_id>/                           # one per top-N model
    │       └── model_artifact/
    │           └── <ModelName>_FULL/            # e.g. LightGBM_BAG_L1_FULL
    │               ├── predictor/               # AutoGluon TabularPredictor files
    │               ├── metrics/
    │               │   ├── metrics.json         # model evaluation metrics (eval_metric, etc.)
    │               │   ├── feature_importance.json
    │               │   └── confusion_matrix.json  # for classification tasks only
    │               └── notebooks/
    │                   └── automl_predictor_notebook.ipynb   # Jupyter notebook for inference & exploration
    └── automl-data-loader/
        └── <task_id>/
            └── sampled_test_dataset/            # Test split (S3 artifact)
```

- **leaderboard-evaluation**: Contains the HTML leaderboard artifact summarizing all model results.
- **autogluon-models-full-refit**: Each top-N model refit task writes its model artifact here, under `<ModelName>_FULL`, including the saved TabularPredictor and associated metrics.
- **automl-data-loader**: Stores the test dataset S3 artifact used for evaluation; the training splits live on the PVC workspace instead.

*Note*: There is one `autogluon-models-full-refit/<task_id>/model_artifact/<ModelName>_FULL` directory for each selected top-N model (parallel execution). Each contains an independently saved and refitted AutoGluon predictor.

For loading:

- Load a refitted model for deployment or notebook exploration using `TabularPredictor.load(<.../model_artifact/<ModelName>_FULL>/predictor)`.
- Model metrics and feature importances are always at `metrics/` under each model directory.
- The leaderboard HTML is at `leaderboard-evaluation/<task_id>/html_artifact`.

### Model Artifact metadata

Each refit task writes a Model artifact whose `metadata` is set by the autogluon_models_full_refit component. Downstream components (e.g. leaderboard evaluation) and consumers can rely on this structure:

| Key | Type | Description |
| ----- | ------ | ----------- |
| `display_name` | `str` | Model name with `_FULL` suffix (e.g. `"LightGBM_BAG_L1_FULL"`). Used by the leaderboard to identify the model and to resolve metrics at `model.path / display_name / metrics / metrics.json`. |
| `context` | `dict` | Run and model context (see below). |

**`context`** contains:

| Key | Type | Description |
| ----- | ------ | ----------- |
| `data_config` | `dict` | `sampling_config` and `split_config` from the data loader component. |
| `task_type` | `str` | Problem type: `"regression"`, `"binary"`, or `"multiclass"`. |
| `label_column` | `str` | Name of the target/label column. |
| `model_config` | `dict` | Model training configuration (e.g. preset, eval_metric, time limit) from the selection stage. |
| `location` | `dict` | Paths relative to the artifact root: `model_directory` (e.g. `"LightGBM_BAG_L1_FULL"`), `predictor` (e.g. `"LightGBM_BAG_L1_FULL/predictor/predictor.pkl"`), `notebook` (e.g. `"LightGBM_BAG_L1_FULL/notebooks/automl_predictor_notebook.ipynb"`). |
| `metrics` | `dict` | Evaluation results on the test dataset: `test_data` holds the AutoGluon evaluation dict (metric names and values, e.g. `root_mean_squared_error`, `r2` for regression). |

Example (regression):

```json
{
  "display_name": "LightGBM_BAG_L1_FULL",
  "context": {
    "data_config": {
      "sampling_config": {"n_samples": 10000},
      "split_config": {"test_size": 0.2, "random_state": 42}
    },
    "task_type": "regression",
    "label_column": "price",
    "model_config": {"eval_metric": "r2", "time_limit": 300},
    "location": {
      "model_directory": "LightGBM_BAG_L1_FULL",
      "predictor": "LightGBM_BAG_L1_FULL/predictor/predictor.pkl",
      "notebook": "LightGBM_BAG_L1_FULL/notebooks/automl_predictor_notebook.ipynb"
    },
    "metrics": {
      "test_data": {
        "root_mean_squared_error": 0.42,
        "r2": 0.85
      }
    }
  }
}
```

## Usage Examples 💡

### Basic usage (regression)

Run the full two-stage pipeline with data from S3; credentials are provided via a Kubernetes secret:

```python
from kfp import dsl
from kfp_components.pipelines.training.automl.autogluon_tabular_training_pipeline import (
    autogluon_tabular_training_pipeline,
)

# Compile and run the pipeline
pipeline = autogluon_tabular_training_pipeline(
    train_data_secret_name="my-s3-secret",
    train_data_bucket_name="my-data-bucket",
    train_data_file_key="datasets/housing_prices.csv",
    label_column="price",
    task_type="regression",
    top_n=3,
)
```

### Classification (binary or multiclass)

```python
pipeline = autogluon_tabular_training_pipeline(
    train_data_secret_name="my-s3-secret",
    train_data_bucket_name="my-ml-bucket",
    train_data_file_key="data/train.csv",
    label_column="target",
    task_type="multiclass",
    top_n=5,
)
```

### Compile to YAML

```python
from kfp.compiler import Compiler
from kfp_components.pipelines.training.automl.autogluon_tabular_training_pipeline import (
    autogluon_tabular_training_pipeline,
)

Compiler().compile(
    autogluon_tabular_training_pipeline,
    package_path="autogluon_tabular_training_pipeline.yaml",
)
```

### Run pipeline using KFP SDK

Compile and submit a run using the KFP client. Configure the client for your cluster (e.g. `host`, or in-cluster auth). Pipeline parameters are passed as `arguments`:

```python
import kfp
from kfp_components.pipelines.training.automl.autogluon_tabular_training_pipeline import (
    autogluon_tabular_training_pipeline,
)

# Create client (customize host for your KFP instance)
client = kfp.Client(host="https://your-kfp-host/pipeline")

# Run the pipeline with parameters
run = client.create_run_from_pipeline_func(
    autogluon_tabular_training_pipeline,
    arguments={
        "train_data_secret_name": "my-s3-secret",
        "train_data_bucket_name": "my-data-bucket",
        "train_data_file_key": "datasets/housing_prices.csv",
        "label_column": "price",
        "task_type": "regression",
        "top_n": 3,
    },
)
print(f"Submitted run: {run.run_id}")
```

To run from a compiled YAML instead:

```python
from kfp.compiler import Compiler

Compiler().compile(
    autogluon_tabular_training_pipeline,
    package_path="autogluon_tabular_training_pipeline.yaml",
)
run = client.create_run_from_pipeline_package(
    "autogluon_tabular_training_pipeline.yaml",
    arguments={
        "train_data_secret_name": "my-s3-secret",
        "train_data_bucket_name": "my-data-bucket",
        "train_data_file_key": "datasets/housing_prices.csv",
        "label_column": "price",
        "task_type": "regression",
        "top_n": 3,
    },
)
```
