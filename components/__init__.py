"""Kubeflow Pipelines Components - Core Components Package

This module auto-imports all components for clean usage:
    from kfp_components.components import training
    from kfp_components.components import evaluation
    from kfp_components.components import data_processing
    from kfp_components.components import deployment
"""

from . import training
from . import evaluation
from . import data_processing
from . import deployment
