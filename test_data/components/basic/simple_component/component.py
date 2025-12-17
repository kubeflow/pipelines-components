"""Simple component for testing."""

from kfp import dsl


@dsl.component
def simple_component(input_text: str, count: int) -> str:
    """Processes input text a specified number of times.

    This is a simple component used for testing the README generator.

    Args:
        input_text: The text to process.
        count: Number of times to repeat the operation.

    Returns:
        The processed result.
    """
    return input_text * count
