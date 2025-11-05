"""Third-Party Pipelines Package

This module provides access to third-party contributed pipelines.
These pipelines are not maintained by the Kubeflow community.

Usage:
    from kfp_components_third_party.pipelines import training
    from kfp_components_third_party.pipelines import evaluation
    from kfp_components_third_party.pipelines import data_processing
"""

from . import training
from . import evaluation
from . import data_processing
