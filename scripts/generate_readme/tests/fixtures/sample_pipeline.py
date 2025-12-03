"""Sample pipeline for testing."""

from kfp import dsl

@dsl.component
def dummy_task(text: str) -> str:
    """Dummy task for pipeline testing."""
    return text

@dsl.pipeline(
    name='sample-pipeline',
    description='A sample pipeline for testing'
)
def sample_pipeline(
    data_path: str,
    model_name: str = "default-model"
):
    """A sample pipeline for testing.
    
    This pipeline demonstrates basic pipeline structure.
    
    Args:
        data_path: Path to training data.
        model_name: Name of the model to train. Defaults to "default-model".
    """
    # Pipelines need at least one task
    dummy_task(text=f"Processing {data_path} with {model_name}")

