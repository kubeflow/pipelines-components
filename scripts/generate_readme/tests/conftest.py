"""Shared pytest fixtures for generate_readme tests."""

import tempfile
from pathlib import Path

import pytest


def create_component_dir(
    parent_dir: Path,
    name: str,
    component_code: str,
    metadata_content: str = None,
) -> Path:
    """Helper to create a component directory with files.
    
    Args:
        parent_dir: Parent directory to create the component in.
        name: Name of the component directory.
        component_code: Content for component.py.
        metadata_content: Optional content for metadata.yaml.
        
    Returns:
        Path to the created component directory.
    """
    comp_dir = parent_dir / name
    comp_dir.mkdir(parents=True, exist_ok=True)
    
    (comp_dir / "component.py").write_text(component_code)
    
    if metadata_content:
        (comp_dir / "metadata.yaml").write_text(metadata_content)
    
    (comp_dir / "__init__.py").write_text("")
    
    return comp_dir


def create_pipeline_dir(
    parent_dir: Path,
    name: str,
    pipeline_code: str,
    metadata_content: str = None,
) -> Path:
    """Helper to create a pipeline directory with files.
    
    Args:
        parent_dir: Parent directory to create the pipeline in.
        name: Name of the pipeline directory.
        pipeline_code: Content for pipeline.py.
        metadata_content: Optional content for metadata.yaml.
        
    Returns:
        Path to the created pipeline directory.
    """
    pipe_dir = parent_dir / name
    pipe_dir.mkdir(parents=True, exist_ok=True)
    
    (pipe_dir / "pipeline.py").write_text(pipeline_code)
    
    if metadata_content:
        (pipe_dir / "metadata.yaml").write_text(metadata_content)
    
    (pipe_dir / "__init__.py").write_text("")
    
    return pipe_dir


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_component_file():
    """Sample component file for testing."""
    fixture_path = Path(__file__).parent / "resources" / "sample_component.py"
    return fixture_path.read_text()


@pytest.fixture
def sample_pipeline_file():
    """Sample pipeline file for testing."""
    fixture_path = Path(__file__).parent / "resources" / "sample_pipeline.py"
    return fixture_path.read_text()


@pytest.fixture
def component_multiline_overview():
    """Component with multiline overview docstring."""
    fixture_path = Path(__file__).parent / "resources" / "component_multiline_overview.py"
    return fixture_path.read_text()


@pytest.fixture
def component_no_docstring():
    """Component without docstring."""
    fixture_path = Path(__file__).parent / "resources" / "component_no_docstring.py"
    return fixture_path.read_text()


@pytest.fixture
def sample_component_metadata():
    """Sample component metadata.yaml content."""
    fixture_path = Path(__file__).parent / "resources" / "sample_component_metadata.yaml"
    return fixture_path.read_text()


@pytest.fixture
def sample_pipeline_metadata():
    """Sample pipeline metadata.yaml content."""
    fixture_path = Path(__file__).parent / "resources" / "sample_pipeline_metadata.yaml"
    return fixture_path.read_text()


@pytest.fixture
def component_dir(temp_dir, sample_component_file, sample_component_metadata):
    """Create a complete component directory structure."""
    return create_component_dir(
        temp_dir,
        "test_component",
        sample_component_file,
        sample_component_metadata
    )


@pytest.fixture
def pipeline_dir(temp_dir, sample_pipeline_file, sample_pipeline_metadata):
    """Create a complete pipeline directory structure."""
    return create_pipeline_dir(
        temp_dir,
        "test_pipeline",
        sample_pipeline_file,
        sample_pipeline_metadata
    )


@pytest.fixture
def category_with_components(temp_dir, sample_component_file, sample_component_metadata):
    """Create a category directory with sample components.
    
    Returns a tuple of (category_dir, list of component directories).
    """
    category_dir = temp_dir / "components" / "dev"
    category_dir.mkdir(parents=True)
    
    comp1_dir = create_component_dir(category_dir, "component1", sample_component_file, sample_component_metadata)
    comp2_dir = create_component_dir(category_dir, "component2", sample_component_file, sample_component_metadata)
    
    return category_dir, [comp1_dir, comp2_dir]


@pytest.fixture
def category_with_pipelines(temp_dir, sample_pipeline_file, sample_pipeline_metadata):
    """Create a category directory with sample pipelines.
    
    Returns a tuple of (category_dir, list of pipeline directories).
    """
    category_dir = temp_dir / "pipelines" / "training"
    category_dir.mkdir(parents=True)
    
    pipe1_dir = create_pipeline_dir(category_dir, "pipeline1", sample_pipeline_file, sample_pipeline_metadata)
    pipe2_dir = create_pipeline_dir(category_dir, "pipeline2", sample_pipeline_file, sample_pipeline_metadata)
    
    return category_dir, [pipe1_dir, pipe2_dir]


@pytest.fixture
def sample_extracted_metadata():
    """Sample extracted metadata dictionary."""
    return {
        "name": "sample_component",
        "docstring": "A sample component for testing.\n\nThis component demonstrates basic functionality.",
        "overview": "A sample component for testing.\n\nThis component demonstrates basic functionality.",
        "parameters": {
            "input_path": {"name": "input_path", "type": "str", "description": "Path to input file."},
            "output_path": {"name": "output_path", "type": "str", "description": "Path to output file."},
            "num_iterations": {
                "name": "num_iterations",
                "type": "int",
                "default": 10,
                "description": "Number of iterations to run. Defaults to 10.",
            },
        },
        "returns": {"type": "str", "description": "Status message indicating completion."},
    }
