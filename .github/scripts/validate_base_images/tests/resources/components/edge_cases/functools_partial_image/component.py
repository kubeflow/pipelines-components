"""Test component with base_image set via functools.partial wrapper.

This demonstrates an edge case where the component decorator is wrapped
with functools.partial to set a default base_image. Individual decorators
don't show the base_image, but compilation resolves it correctly.
"""

import functools

from kfp import dsl

CUSTOM_BASE_IMAGE = "quay.io/myorg/python:3.11"

custom_component = functools.partial(dsl.component, base_image=CUSTOM_BASE_IMAGE)


@custom_component
def component_with_partial_wrapper(input_path: str) -> str:
    """Component with base_image set via functools.partial wrapper."""
    print(f"Processing {input_path}")
    return f"{input_path}/output"

