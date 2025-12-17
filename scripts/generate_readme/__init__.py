"""Generate README.md documentation for Kubeflow Pipelines components and pipelines.

This package introspects Python functions decorated with @dsl.component or @dsl.pipeline
to extract function metadata and generate comprehensive README documentation
"""

from .metadata_parser import MetadataParser
from .writer import ReadmeWriter

__all__ = [
    "ReadmeWriter",
    "MetadataParser",
]
