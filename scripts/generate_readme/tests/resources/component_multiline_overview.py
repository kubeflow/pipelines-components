from kfp import dsl


@dsl.component
def test_comp(text: str) -> str:
    """First line of overview.

    This is a longer description that should not
    appear in the category index.

    Args:
        text: Input text.

    Returns:
        Output text.
    """
    return text
