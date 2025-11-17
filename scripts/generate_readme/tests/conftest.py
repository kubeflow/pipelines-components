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
def sample_component_code():
    """Sample KFP component code without kfp imports."""
    return '''"""Sample component for testing."""

# Mock decorator to avoid kfp import
class component:
    def __init__(self, func):
        self.python_func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
    def __call__(self, *args, **kwargs):
        return self.python_func(*args, **kwargs)

@component
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
'''


@pytest.fixture
def sample_pipeline_code():
    """Sample KFP pipeline code without kfp imports."""
    return '''"""Sample pipeline for testing."""

# Mock decorator to avoid kfp import
class pipeline:
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', '')
        self.description = kwargs.get('description', '')
    def __call__(self, func):
        wrapper = type('PipelineWrapper', (), {
            'pipeline_func': func,
            '__name__': func.__name__,
            '__doc__': func.__doc__,
            'name': self.name,
            'description': self.description
        })()
        return wrapper

@pipeline(
    name='sample-pipeline',
    description='A sample pipeline for testing'
)
def sample_pipeline(
    data_path: str,
    model_name: str = "default-model"
) -> str:
    """A sample pipeline for testing.
    
    This pipeline demonstrates basic pipeline structure.
    
    Args:
        data_path: Path to training data.
        model_name: Name of the model to train. Defaults to "default-model".
        
    Returns:
        Model identifier.
    """
    return f"model-{model_name}"
'''


@pytest.fixture
def sample_component_metadata():
    """Sample component metadata.yaml content."""
    return """tier: core
name: sample_component
stability: stable
dependencies:
  kubeflow:
    - name: Pipelines
      version: '>=2.5'
    - name: Trainer
      version: '>=2.0'
  external_services:
    - name: Some External Service
      version: "1.0"
tags:
  - testing
  - sample
lastVerified: 2025-11-13T00:00:00Z
ci:
  skip_dependency_probe: false
  pytest: optional
links:
  documentation: https://example.com/components/sample-component/
  issue_tracker: https://github.com/example/repo/issues
"""


@pytest.fixture
def sample_pipeline_metadata():
    """Sample pipeline metadata.yaml content."""
    return """name: sample_pipeline
description: A sample pipeline for testing
components:
  - sample_component
image: mock-registry.example.com/mock-image:latest
tier: core
stability: stable
dependencies:
  kubeflow:
    - name: Pipelines
      version: ">=2.5"
    - name: Trainer
      version: '>=2.0'
  external_services:
    - name: Some External Service
      version: "1.0"
tags:
  - testing
  - pipeline
lastVerified: "2025-11-14 00:00:00+00:00"
links:
  documentation: https://example.com/pipelines/sample-pipeline/
  issue_tracker: https://github.com/example/repo/issues
ci:
  skip_dependency_probe: false
  pytest: optional
"""


@pytest.fixture
def component_dir(temp_dir, sample_component_code, sample_component_metadata):
    """Create a complete component directory structure."""
    comp_dir = temp_dir / "test_component"
    comp_dir.mkdir()
    
    # Write component.py
    (comp_dir / "component.py").write_text(sample_component_code)
    
    # Write metadata.yaml
    (comp_dir / "metadata.yaml").write_text(sample_component_metadata)
    
    # Write __init__.py
    (comp_dir / "__init__.py").write_text("")
    
    return comp_dir


@pytest.fixture
def pipeline_dir(temp_dir, sample_pipeline_code, sample_pipeline_metadata):
    """Create a complete pipeline directory structure."""
    pipe_dir = temp_dir / "test_pipeline"
    pipe_dir.mkdir()
    
    # Write pipeline.py
    (pipe_dir / "pipeline.py").write_text(sample_pipeline_code)
    
    # Write metadata.yaml
    (pipe_dir / "metadata.yaml").write_text(sample_pipeline_metadata)
    
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

