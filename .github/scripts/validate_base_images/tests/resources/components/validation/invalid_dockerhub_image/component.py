"""Test component with an invalid Docker Hub base image."""

from kfp import dsl


@dsl.component(base_image="docker.io/custom:latest")
def invalid_dockerhub_component(input_path: str) -> str:
    """Component with invalid Docker Hub base image."""
    print(f"Processing {input_path}")
    return f"{input_path}/output"

