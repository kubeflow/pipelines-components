from kfp import dsl
from kfp_components.components.data_processing.automl.tabular_data_loader import automl_data_loader
from kfp_components.components.data_processing.automl.tabular_train_test_split import tabular_train_test_split
from kfp_components.components.training.automl.autogluon_leaderboard_evaluation import leaderboard_evaluation
from kfp_components.components.training.automl.autogluon_models_full_refit import autogluon_models_full_refit
from kfp_components.components.training.automl.autogluon_models_selection import models_selection


@dsl.pipeline(
    name="autogluon-tabular-training-pipeline",
    description=(
        "End-to-end AutoGluon tabular training pipeline implementing a two-stage approach: "
        "first builds and selects top-performing models on sampled data, then refits them "
        "on the full dataset. The pipeline loads data from S3, splits it into train/test sets, "
        "trains multiple AutoGluon models using ensembling (stacking and bagging), selects the "
        "top N performers, refits each on the complete training data in parallel, and finally "
        "evaluates all refitted models to generate a comprehensive leaderboard with performance metrics."
    ),
    pipeline_config=dsl.PipelineConfig(
        workspace=dsl.WorkspaceConfig(
            size="1Gi",  # TODO: change to recommended size
            kubernetes=dsl.KubernetesWorkspaceConfig(
                pvcSpecPatch={
                    "storageClassName": "gp3-csi",  # or 'gp3', 'fast', etc.
                    "accessModes": ["ReadWriteOnce"],
                }
            ),
        ),
    ),
)
def autogluon_tabular_training_pipeline(
    train_data_secret_name: str,
    train_data_bucket_name: str,
    train_data_file_key: str,
    label_column: str,
    task_type: str,
    top_n: int = 3,
):
    """AutoGluon Tabular Training Pipeline.

    This pipeline implements an efficient two-stage training approach for AutoGluon tabular models
    that balances computational cost with model quality. The pipeline automates the complete
    machine learning workflow from data loading to final model evaluation.

    **Pipeline Stages:**

    1. **Data Loading**: Loads tabular data from an S3-compatible object storage bucket
       using AWS credentials configured via Kubernetes secrets. The component produces
       both a tabular_data artifact (for splitting) and a full_dataset artifact
       (for model refitting).

    2. **Data Splitting**: Splits the loaded tabular data into training and test sets
       using a configurable test size (default: 20% test, 80% train). The split is
       performed on the tabular_data artifact to create separate train and test
       datasets for model training and evaluation.

    3. **Model Selection**: Trains multiple AutoGluon models on the training data using
       AutoGluon's ensembling approach (stacking with 3 levels and bagging with 2 folds).
       The component automatically trains various model types including neural networks,
       tree-based models (XGBoost, LightGBM, CatBoost), and linear models. All models are
       evaluated on the test set and ranked by performance. The top N models are selected
       for the refitting stage.

    4. **Model Refitting**: Refits each of the top N selected models on the full dataset
       (the complete original dataset from the data loader). This stage runs in parallel
       (with parallelism of 2) to efficiently retrain multiple models. Each refitted model
       is saved with a "_FULL" suffix and optimized for deployment by removing unnecessary
       models and files.

    5. **Leaderboard Evaluation**: Aggregates evaluation results from all refitted model
       artifacts (each refit component writes metrics to model_artifact.path /
       model_name_FULL / metrics). The leaderboard component reads these pre-computed
       metrics and generates an HTML-formatted leaderboard ranking models by their
       performance metrics for comparison and selection.

    **Two-Stage Training Benefits:**

    - **Efficient Exploration**: Initial model training uses the split training data
      with efficient ensembling rather than expensive hyperparameter optimization
    - **Optimal Performance**: Final models are refitted on the complete original dataset
      for maximum performance
    - **Parallel Efficiency**: Top models are refitted in parallel to minimize total
      pipeline execution time
    - **Production-Ready**: Refitted models are AutoGluon Predictors optimized and ready
      for deployment

    **AutoGluon Ensembling Approach:**

    The pipeline leverages AutoGluon's unique ensembling strategy that combines multiple
    model types using stacking and bagging rather than traditional hyperparameter optimization.
    This approach is more efficient and typically produces better results for tabular data
    by automatically:
    - Training diverse model families
    - Combining predictions using multi-level stacking
    - Using bootstrap aggregation (bagging) for robustness
    - Selecting optimal ensemble configurations

    Args:
        train_data_secret_name: Kubernetes secret name with S3 credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, AWS_DEFAULT_REGION).
        train_data_bucket_name: S3-compatible bucket name containing the tabular data file.
        train_data_file_key: S3 object key of the CSV file (features and target column).
        label_column: Name of the target/label column in the dataset.
        task_type: "binary", "multiclass", or "regression"; drives metrics and model types.
        top_n: Number of top models to select and refit (default: 3); positive integer.

    Returns:
        HTML artifact with leaderboard of refitted models ranked by task_type metric (e.g. accuracy, r2).

    Raises:
        FileNotFoundError: If the S3 file cannot be found or accessed.
        ValueError: If label_column missing, task_type invalid, top_n not positive, or split fails.
        KeyError: If AWS credentials missing in secret or required component outputs unavailable.

    Example:
        from kfp import dsl
        from pipelines.training.automl.autogluon_tabular_training_pipeline import (
            autogluon_tabular_training_pipeline
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
    """  # noqa: E501
    from kfp.kubernetes import use_secret_as_env

    tabular_loader_task = automl_data_loader(
        bucket_name=train_data_bucket_name, file_key=train_data_file_key, label_column=label_column, task_type=task_type
    )

    use_secret_as_env(
        tabular_loader_task,
        secret_name=train_data_secret_name,
        secret_key_to_env={
            "AWS_ACCESS_KEY_ID": "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY",
            "AWS_S3_ENDPOINT": "AWS_S3_ENDPOINT",
            "AWS_DEFAULT_REGION": "AWS_DEFAULT_REGION",
        },
    )

    train_test_split_task = tabular_train_test_split(
        dataset=tabular_loader_task.outputs["full_dataset"],
        task_type=task_type,
        label_column=label_column,
        split_config={"test_size": 0.2},
    )

    # Stage 1: Model Selection
    # Train multiple models on sampled data and select top N performers

    selection_task = models_selection(
        label_column=label_column,
        task_type=task_type,
        train_data=train_test_split_task.outputs["sampled_train_dataset"],
        test_data=train_test_split_task.outputs["sampled_test_dataset"],
        top_n=top_n,
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
    )

    # Stage 2: Model Refitting
    # Refit each top model on the full training dataset

    with dsl.ParallelFor(items=selection_task.outputs["top_models"], parallelism=2) as model_name:
        refit_full_task = autogluon_models_full_refit(
            model_name=model_name,
            test_dataset=train_test_split_task.outputs["sampled_test_dataset"],
            predictor_path=selection_task.outputs["predictor_path"],
            sampling_config=tabular_loader_task.outputs["sample_config"],
            split_config=train_test_split_task.outputs["split_config"],
            model_config=selection_task.outputs["model_config"],
            pipeline_name=dsl.PIPELINE_JOB_RESOURCE_NAME_PLACEHOLDER,
            run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER,
            sample_row=train_test_split_task.outputs["sample_row"],
        )

    # Generate leaderboard
    leaderboard_evaluation(
        models=dsl.Collected(refit_full_task.outputs["model_artifact"]),
        eval_metric=selection_task.outputs["eval_metric"],
    )


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(
        autogluon_tabular_training_pipeline,
        package_path=__file__.replace(".py", "_pipeline.yaml"),
    )
