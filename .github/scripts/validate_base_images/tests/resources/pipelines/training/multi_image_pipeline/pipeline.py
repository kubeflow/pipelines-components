"""Test pipeline with multiple components using different base images."""

from kfp import dsl


@dsl.component
def preprocess_data(data_path: str) -> str:
    """Preprocess data without custom base image."""
    return f"{data_path}/processed"


@dsl.component(base_image="python:3.11-slim")
def train_step(data_path: str) -> str:
    """Train model with custom base image."""
    return f"/models/trained"


@dsl.component(base_image="ghcr.io/kubeflow/evaluation:v2.0.0")
def evaluate_model(model_path: str) -> float:
    """Evaluate model with another custom base image."""
    return 0.95


@dsl.pipeline(name="multi-image-pipeline")
def training_pipeline(input_data: str = "gs://bucket/data") -> float:
    """A pipeline with multiple base images."""
    preprocess_task = preprocess_data(data_path=input_data)
    train_task = train_step(data_path=preprocess_task.output)
    eval_task = evaluate_model(model_path=train_task.output)
    return eval_task.output

