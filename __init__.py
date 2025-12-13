"""
Kubeflow Pipelines Components

A collection of reusable components and pipelines for Kubeflow Pipelines.

Usage:
    from kfp_components import components, pipelines
    from kfp_components.components import training
    from kfp_components.pipelines import evaluation
"""

# Import submodules to enable the convenient import patterns shown above.
# When this module is imported as part of the installed package the relative
# imports below work naturally. During certain tooling scenarios (e.g. pytest
# collecting this file directly from the repo root) Python treats this module
# as top-level and `__package__` is empty, so we fall back to absolute imports.
if __package__ in (None, ""):
    from importlib import import_module

    components = import_module("kubeflow.pipelines.components.components")
    pipelines = import_module("kubeflow.pipelines.components.pipelines")
else:
    from . import components  # type: ignore[F401]  # re-export for consumers
    from . import pipelines  # type: ignore[F401]
