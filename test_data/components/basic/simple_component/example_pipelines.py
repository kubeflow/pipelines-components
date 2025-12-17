"""Example pipelines demonstrating usage of simple_component."""

from kfp import dsl
from kfp_components.components.basic.simple_component import simple_component


@dsl.pipeline(name="simple-component-example")
def example_pipeline(text: str = "hello", repeat_count: int = 3):
    """Example pipeline using simple_component.

    Args:
        text: Text to process.
        repeat_count: Number of times to repeat.
    """
    simple_component(input_text=text, count=repeat_count)
