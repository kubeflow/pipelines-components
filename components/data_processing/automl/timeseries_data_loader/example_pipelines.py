"""Example pipelines demonstrating usage of timeseries_data_loader."""

from kfp import dsl
from kfp_components.components.data_processing.automl.timeseries_data_loader import timeseries_data_loader


@dsl.pipeline(name="timeseries-data-loader-example")
def example_pipeline(
    file_key: str = "data/timeseries.csv",
    bucket_name: str = "my-bucket",
    workspace_path: str = "/tmp/workspace",
    target: str = "value",
    id_column: str = "item_id",
    timestamp_column: str = "timestamp",
    selection_train_size: float = 0.3,
):
    """Example pipeline using timeseries_data_loader.

    Args:
        file_key: S3 key of the data file.
        bucket_name: S3 bucket name.
        workspace_path: Path to the workspace directory.
        target: Name of the target column.
        id_column: Name of the ID column.
        timestamp_column: Name of the timestamp column.
        selection_train_size: Fraction of data for training.
    """
    timeseries_data_loader(
        file_key=file_key,
        bucket_name=bucket_name,
        workspace_path=workspace_path,
        target=target,
        id_column=id_column,
        timestamp_column=timestamp_column,
        selection_train_size=selection_train_size,
    )
