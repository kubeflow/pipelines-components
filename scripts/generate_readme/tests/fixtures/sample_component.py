"""Sample component for testing."""

from kfp import dsl

@dsl.component
def sample_component(
    input_path: str,
    output_path: str,
    num_iterations: int = 10
) -> str:
    """A sample component for testing.
    
    This component demonstrates basic functionality.
    
    Args:
        input_path: Path to input file.
        output_path: Path to output file.
        num_iterations: Number of iterations to run. Defaults to 10.
        
    Returns:
        Status message indicating completion.
    """
    print(f"Processing {input_path}")
    return f"Processed {num_iterations} iterations"

