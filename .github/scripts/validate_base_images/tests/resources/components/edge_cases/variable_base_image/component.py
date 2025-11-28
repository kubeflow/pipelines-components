"""Test component with base_image set via variable reference.

This demonstrates an edge case where AST parsing would only see the variable
name, not the actual image value. Compilation resolves this correctly.
"""

from kfp import dsl

MY_CUSTOM_IMAGE = "docker.io/myorg/custom-python:3.11"


@dsl.component(base_image=MY_CUSTOM_IMAGE)
def component_with_variable_image(input_path: str) -> str:
    """Component with base_image set via variable."""
    print(f"Processing {input_path}")
    return f"{input_path}/output"

