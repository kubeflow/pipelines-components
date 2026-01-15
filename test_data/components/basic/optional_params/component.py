"""Component with optional parameters."""

from typing import Optional

from kfp import dsl


@dsl.component
def optional_params(
    required_param: str, optional_text: Optional[str] = None, max_length: int = 100, separator: str = ""
) -> str:
    """Processes text with optional configuration.

    This component demonstrates optional parameters with defaults.

    Args:
        required_param: This parameter is required.
        optional_text: Optional text to append.
        max_length: Maximum length of output.
        separator: Separator between texts (empty by default).

    Returns:
        The processed text.
    """
    result = required_param
    if optional_text:
        result += separator + optional_text
    return result[:max_length]
