"""Kubeflow Pipelines Components - Third-Party Package

This module provides third-party contributed components and pipelines.
These are not maintained by the Kubeflow community.

Usage:
    from kubeflow.pipelines.components.third_party import components
    from kubeflow.pipelines.components.third_party import pipelines
"""

# Import submodules - required to enable the usage patterns
# Without these, "from third_party import components, pipelines" would fail
from . import components
from . import pipelines
