"""Test component with a valid ghcr.io/kubeflow base image."""

from kfp import dsl


@dsl.component(base_image="ghcr.io/kubeflow/pipelines-components-example:v1.0.0")
def example_component(input_path: str) -> str:
    """Example component with valid Kubeflow base image."""
    print(f"Processing {input_path}")
    return f"{input_path}/output"

