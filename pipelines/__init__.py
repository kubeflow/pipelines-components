"""Kubeflow Pipelines Components - Core Pipelines Package

This module auto-imports all pipelines for clean usage:
    from kubeflow.pipelines import pipelines
    from kubeflow.pipelines.pipelines import training
    from kubeflow.pipelines.pipelines import evaluation
    from kubeflow.pipelines.pipelines import data_processing
    from kubeflow.pipelines.pipelines import deployment
"""

from . import training
from . import evaluation
from . import data_processing
from . import deployment
