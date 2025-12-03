"""Shared pytest fixtures for generate_readme tests."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def component_dir(temp_dir):
    """Create a complete component directory structure."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    comp_dir = temp_dir / "test_component"
    comp_dir.mkdir()
    
    # Write component.py
    component_code = (fixtures_dir / "sample_component.py").read_text()
    (comp_dir / "component.py").write_text(component_code)
    
    # Write metadata.yaml
    component_metadata = (fixtures_dir / "sample_component_metadata.yaml").read_text()
    (comp_dir / "metadata.yaml").write_text(component_metadata)
    
    # Write __init__.py
    (comp_dir / "__init__.py").write_text("")
    
    return comp_dir


@pytest.fixture
def pipeline_dir(temp_dir):
    """Create a complete pipeline directory structure."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    pipe_dir = temp_dir / "test_pipeline"
    pipe_dir.mkdir()
    
    # Write pipeline.py
    pipeline_code = (fixtures_dir / "sample_pipeline.py").read_text()
    (pipe_dir / "pipeline.py").write_text(pipeline_code)
    
    # Write metadata.yaml
    pipeline_metadata = (fixtures_dir / "sample_pipeline_metadata.yaml").read_text()
    (pipe_dir / "metadata.yaml").write_text(pipeline_metadata)
    
    # Write __init__.py
    (pipe_dir / "__init__.py").write_text("")
    
    return pipe_dir


@pytest.fixture
def sample_extracted_metadata():
    """Sample extracted metadata dictionary."""
    return {
        'name': 'sample_component',
        'docstring': 'A sample component for testing.\n\nThis component demonstrates basic functionality.',
        'overview': 'A sample component for testing.\n\nThis component demonstrates basic functionality.',
        'parameters': {
            'input_path': {
                'name': 'input_path',
                'type': 'str',
                'description': 'Path to input file.'
            },
            'output_path': {
                'name': 'output_path',
                'type': 'str',
                'description': 'Path to output file.'
            },
            'num_iterations': {
                'name': 'num_iterations',
                'type': 'int',
                'default': 10,
                'description': 'Number of iterations to run. Defaults to 10.'
            }
        },
        'returns': {
            'type': 'str',
            'description': 'Status message indicating completion.'
        }
    }

