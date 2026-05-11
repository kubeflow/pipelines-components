"""Kubeflow Pipelines Components

A collection of reusable components and pipelines for Kubeflow Pipelines.

Usage:
    from library import components, pipelines
    from library.components import training
    from library.pipelines import evaluation
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
#since the 
__all__ = ["pipelines", "components"]
