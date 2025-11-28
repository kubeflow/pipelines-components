"""Test component with a custom base image."""

from kfp import dsl


@dsl.component(base_image="ghcr.io/kubeflow/ml-training:v1.0.0")
def train_model(
    dataset_path: str,
    epochs: int = 10,
) -> str:
    """Train a model with custom base image."""
    print(f"Training on {dataset_path} for {epochs} epochs")
    return "/output/model.pt"

