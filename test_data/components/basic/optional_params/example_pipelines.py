"""Example pipelines demonstrating usage of optional_params."""

from kfp import dsl
from kfp_components.components.basic.optional_params import optional_params


@dsl.pipeline(name="optional-params-example")
def example_pipeline(input: str = "test"):
    """Example pipeline using optional_params.

    Args:
        input: Input text to process.
    """
    # Example 1: Using only required parameter
    optional_params(required_param=input)

    # Example 2: Using optional parameters
    optional_params(required_param=input, optional_text=" suffix", max_length=50)
