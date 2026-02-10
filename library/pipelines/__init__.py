"""Kubeflow Pipelines Components - Core Pipelines Package

This module auto-imports all pipelines for clean usage:
    from kfp_components import pipelines
    from kfp_components.pipelines import training
    from kfp_components.pipelines import evaluation
    from kfp_components.pipelines import data_processing
    from kfp_components.pipelines import deployment
"""

from . import data_processing, deployment, evaluation, training

__all__ = ["data_processing", "deployment", "evaluation", "training"]
