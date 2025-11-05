"""Kubeflow Pipelines Components - Core Components Package

This module auto-imports all components for clean usage:
    from kfp_components import training
    from kfp_components import evaluation
    from kfp_components import data_processing
    from kfp_components import deployment
    from kfp_components import monitoring
"""

from . import training
from . import evaluation
from . import data_processing
from . import deployment
from . import monitoring
