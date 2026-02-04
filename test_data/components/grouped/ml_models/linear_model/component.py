"""Linear model component for testing subcategory support."""

from kfp import dsl


@dsl.component
def linear_model(features: str, target: str) -> str:
    """Trains a simple linear model on input data.

    This component trains a linear regression model used for testing
    subcategory README generation.

    Args:
        features: Path to the features dataset.
        target: Name of the target column.

    Returns:
        Path to the trained model artifact.
    """
    return f"model trained on {features} targeting {target}"
