from kfp import dsl

@dsl.component
def dummy_component(text: str) -> str:
    """Dummy component for testing."""
    return text

@dsl.pipeline
def hello_pipeline(greeting: str):
    """Simple hello world pipeline that demonstrates basic structure.
    
    This is additional information about the pipeline.
    
    Args:
        greeting: Greeting message to use.
    """
    dummy_component(text=greeting)

