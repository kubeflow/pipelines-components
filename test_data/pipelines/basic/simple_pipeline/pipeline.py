"""Simple pipeline for testing."""

from kfp import dsl


@dsl.pipeline(name="simple-pipeline")
def simple_pipeline(input_text: str, iterations: int = 3):
    """A simple test pipeline.

    This pipeline demonstrates basic pipeline structure for
    testing the README generator.

    Args:
        input_text: The input text to process.
        iterations: Number of iterations to run.
    """
    pass
