"""Example pipelines demonstrating usage of autogluon_timeseries_models_full_refit."""

from kfp import dsl
from kfp_components.components.training.automl.autogluon_timeseries_models_full_refit import (
    autogluon_timeseries_models_full_refit,
)


@dsl.pipeline(name="autogluon-timeseries-models-full-refit-example")
def example_pipeline(
    model_name: str = "WeightedEnsemble",
    predictor_path: str = "/tmp/predictor",
    sampling_config: dict = {},
    split_config: dict = {},
    model_config: dict = {},
    pipeline_name: str = "timeseries-pipeline",
    run_id: str = "run-001",
    models_selection_train_data_path: str = "/tmp/train_data",
    extra_train_data_path: str = "",
    sample_rows: str = '{"item_id": "A", "timestamp": "2024-01-01", "value": 1.0}',
):
    """Example pipeline using autogluon_timeseries_models_full_refit.

    Args:
        model_name: Name of the model to refit.
        predictor_path: Path to the predictor.
        sampling_config: Sampling configuration.
        split_config: Data split configuration.
        model_config: Model configuration.
        pipeline_name: Name of the pipeline.
        run_id: Unique run identifier.
        models_selection_train_data_path: Path to training data from model selection.
        extra_train_data_path: Path to extra training data.
        sample_rows: JSON string of sample rows.
    """
    test_dataset = dsl.importer(
        artifact_uri="gs://placeholder/test_dataset",
        artifact_class=dsl.Dataset,
    )
    autogluon_timeseries_models_full_refit(
        model_name=model_name,
        test_dataset=test_dataset.output,
        predictor_path=predictor_path,
        sampling_config=sampling_config,
        split_config=split_config,
        model_config=model_config,
        pipeline_name=pipeline_name,
        run_id=run_id,
        models_selection_train_data_path=models_selection_train_data_path,
        extra_train_data_path=extra_train_data_path,
        sample_rows=sample_rows,
    )
