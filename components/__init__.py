"""Kubeflow Pipelines Components - Core Components Package.

This module auto-imports all components for clean usage:
    from kubeflow.pipelines.components import training
    from kubeflow.pipelines.components import evaluation
    from kubeflow.pipelines.components import data_processing
    from kubeflow.pipelines.components import deployment
"""

from . import data_processing, deployment, evaluation, training

__all__ = ["data_processing", "deployment", "evaluation", "training"]
