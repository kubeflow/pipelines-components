"""Kubeflow Pipelines Components - Core Components Package

This module auto-imports all components for clean usage:
    from kubeflow.pipelines.components import training
    from kubeflow.pipelines.components import evaluation
    from kubeflow.pipelines.components import data_processing
    from kubeflow.pipelines.components import deployment
"""

from . import training
from . import evaluation
from . import data_processing
from . import deployment
