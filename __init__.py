"""Kubeflow Pipelines Components

A collection of reusable components and pipelines for Kubeflow Pipelines.

Usage:
    from kfp_components import components, pipelines
    from kfp_components.components import training
    from kfp_components.pipelines import evaluation
"""

# Import submodules to enable the convenient import patterns shown above
# These imports ensure reliable access to submodules and better IDE support
try:
    # Try relative imports first (works when installed as package)
    from . import components, pipelines
except ImportError:
    # Fallback to absolute imports (works during testing with sys.path modification)
    import components  # noqa: F401
    import pipelines  # noqa: F401

__all__ = ["components", "pipelines"]
