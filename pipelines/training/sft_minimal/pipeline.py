"""SFT Minimal Pipeline - Placeholder.

A minimal version of the SFT pipeline with fewer stages for quick testing.
This is a placeholder for future implementation.
"""

from kfp import dsl


@dsl.component(base_image="python:3.11")
def placeholder_task() -> str:
    """Placeholder task for pipeline structure."""
    return "SFT Minimal pipeline placeholder - to be implemented"


@dsl.pipeline(
    name="sft-minimal-pipeline",
    description="SFT Minimal Pipeline - Placeholder for future implementation",
)
def sft_minimal_pipeline():
    """Minimal SFT pipeline placeholder.

    A lightweight version of the full SFT pipeline for quick testing.
    To be implemented in a follow-up PR.
    """
    placeholder_task()
