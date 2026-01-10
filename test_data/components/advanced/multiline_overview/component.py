"""Component with multiline overview."""

from kfp import dsl


@dsl.component(name="multiline_overview")
def process_data(input_data: str) -> str:
    """This component processes various types of data including structured, semi-structured, and unstructured formats while applying complex transformations and business rules to ensure data quality and consistency across the entire pipeline workflow.

    This component demonstrates a multiline overview section.
    It handles various types of input data and applies
    transformations based on configurable rules.

    The component is designed for flexibility and can be
    used in multiple pipeline scenarios.

    Args:
        input_data: The data to process.

    Returns:
        The processed data.
    """  # noqa: E501   # Ignore line-too-long lint rule for multiline wrap testing
    return input_data.upper()
