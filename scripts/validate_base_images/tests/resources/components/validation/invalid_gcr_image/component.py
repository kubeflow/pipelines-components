"""Test component with an invalid GCR base image."""

from kfp import dsl


@dsl.component(base_image="gcr.io/project/image:v1.0")
def invalid_gcr_component(input_path: str) -> str:
    """Component with invalid GCR base image."""
    print(f"Processing {input_path}")
    return f"{input_path}/output"

