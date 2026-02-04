"""Example pipelines demonstrating usage of linear_model."""

from kfp import dsl
from kfp_components.components.grouped.ml_models.linear_model import linear_model


@dsl.pipeline(name="linear-model-example")
def example_pipeline(data_path: str = "/data/train.csv", target_col: str = "price"):
    """Example pipeline using linear_model.

    Args:
        data_path: Path to training data.
        target_col: Target column name.
    """
    linear_model(features=data_path, target=target_col)
