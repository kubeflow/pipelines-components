"""Component with multiline overview."""

from kfp import dsl


@dsl.component(name="multiline_overview")
def process_data(input_data: str) -> str:
    """Processes data with complex logic.

    This component demonstrates a multiline overview section.
    It handles various types of input data and applies
    transformations based on configurable rules.

    The component is designed for flexibility and can be
    used in multiple pipeline scenarios.

    Args:
        input_data: The data to process.

    Returns:
        The processed data.
    """
    return input_data.upper()
