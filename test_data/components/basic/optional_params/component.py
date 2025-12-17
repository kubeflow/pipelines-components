"""Component with optional parameters."""

from typing import Optional

from kfp import dsl


@dsl.component
def optional_params(required_param: str, optional_text: Optional[str] = None, max_length: int = 100) -> str:
    """Processes text with optional configuration.

    This component demonstrates optional parameters with defaults.

    Args:
        required_param: This parameter is required.
        optional_text: Optional text to append.
        max_length: Maximum length of output.

    Returns:
        The processed text.
    """
    result = required_param
    if optional_text:
        result += optional_text
    return result[:max_length]
