"""
Kubeflow Pipelines Components

A collection of reusable components and pipelines for Kubeflow Pipelines.

Usage:
    from kfp_components import components, pipelines
    from kfp_components.components import training
    from kfp_components.pipelines import evaluation
"""

# Import submodules - required to enable the usage patterns shown above
# Without these, "from kfp_components import components, pipelines" would fail
from . import components
from . import pipelines
