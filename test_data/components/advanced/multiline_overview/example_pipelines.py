"""Example pipelines demonstrating usage of process_data."""

from kfp import dsl
from kfp_components.components.advanced.multiline_overview import process_data


@dsl.pipeline(name="process-data-example")
def example_pipeline(data: str = "sample data"):
    """Example pipeline using process_data.

    This demonstrates the multiline overview component in action.

    Args:
        data: Input data to process.
    """
    process_data(input_data=data)


@dsl.pipeline(name="multi-step-processing")
def multi_step_example():
    """Example with multiple processing steps."""
    process_data(input_data="first")
    process_data(input_data="second")
    process_data(input_data="third")
