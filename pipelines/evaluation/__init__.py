"""Evaluation Pipelines Module.

Re-exports pipelines for easy import:
    from kfp_components.pipelines.evaluation import my_pipeline
"""

from __future__ import annotations

from ..._reexports import eager_reexport_pkg_callables

__all__ = eager_reexport_pkg_callables(
    package=__name__,
    package_path=__path__,
    globals_dict=globals(),
)
