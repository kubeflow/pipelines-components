"""Test component without a custom base image (uses default)."""

from kfp import dsl


@dsl.component
def load_data(input_path: str) -> str:
    """Load data using default base image."""
    print(f"Loading from {input_path}")
    return input_path

