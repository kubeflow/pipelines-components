"""Example KFP pipelines demonstrating the SDG Hub component.

This module provides three example pipelines that showcase different usage patterns
for the SDG Hub component within Kubeflow Pipelines:

1. PVC Input Pipeline: Reads input data from a PVC, runs a flow with model configuration
2. PVC Export Pipeline: Same as #1 but also exports results to a PVC
3. Artifact Chaining Pipeline: Shows how to chain components by consuming upstream artifacts

Each pipeline demonstrates best practices for mounting PVCs, injecting secrets,
and configuring the SDG component for different scenarios.
"""

from kfp import dsl
from kfp_kubernetes import mount_pvc, use_secret_as_env

from .component import sdg


@dsl.pipeline(
    name="sdg-pvc-input-pipeline",
    description="SDG pipeline reading input from PVC with model configuration",
)
def sdg_pvc_input_pipeline(
    pvc_name: str = "data-pvc",
    input_file_path: str = "/mnt/data/input.jsonl",
    flow_id: str = "green-clay-812",
    model: str = "openai/gpt-4o-mini",
    max_concurrency: int = 10,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> None:
    """Run SDG flow with input data mounted from a PVC.

    This pipeline demonstrates the typical use case where:
    - Input data is stored on a PVC and mounted to the component
    - A built-in flow is selected by ID
    - Model configuration is provided for LLM-based flows
    - API credentials are injected via Kubernetes secrets

    Args:
        pvc_name: Name of the PVC containing input data.
        input_file_path: Path to the JSONL input file within the mounted PVC.
        flow_id: Built-in SDG Hub flow ID from the registry.
        model: LiteLLM model identifier (e.g., 'openai/gpt-4o-mini').
        max_concurrency: Maximum concurrent LLM requests.
        temperature: LLM sampling temperature (0.0-2.0).
        max_tokens: Maximum response tokens.

    Example:
        >>> from kfp import compiler
        >>> compiler.Compiler().compile(sdg_pvc_input_pipeline, package_path="sdg_pvc_input_pipeline.yaml")
    """
    sdg_task = sdg(
        input_pvc_path=input_file_path,
        flow_id=flow_id,
        model=model,
        max_concurrency=max_concurrency,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Mount PVC to access input data
    mount_pvc(
        task=sdg_task,
        pvc_name=pvc_name,
        mount_path="/mnt/data",
    )

    # Inject LLM API credentials from Kubernetes secret
    use_secret_as_env(
        task=sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={"OPENAI_APIKEY": "LLM_API_KEY"},
    )


@dsl.pipeline(
    name="sdg-pvc-export-pipeline",
    description="SDG pipeline with PVC input and export to PVC",
)
def sdg_pvc_export_pipeline(
    pvc_name: str = "data-pvc",
    input_file_path: str = "/mnt/data/input.jsonl",
    export_base_path: str = "/mnt/data/exports",
    flow_id: str = "green-clay-812",
    model: str = "openai/gpt-4o-mini",
    max_concurrency: int = 10,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> None:
    """Run SDG flow with PVC input and export results to PVC.

    This pipeline extends the basic PVC input pattern by also exporting
    the generated data back to a PVC. This is useful for:
    - Archiving generated datasets
    - Making results available to non-KFP systems
    - Creating timestamped backups of generated data

    The export creates a directory structure: {export_base_path}/{flow_id}/{timestamp}/generated.jsonl

    Args:
        pvc_name: Name of the PVC for input data and exports.
        input_file_path: Path to the JSONL input file within the mounted PVC.
        export_base_path: Base directory on PVC for exports.
        flow_id: Built-in SDG Hub flow ID from the registry.
        model: LiteLLM model identifier (e.g., 'openai/gpt-4o-mini').
        max_concurrency: Maximum concurrent LLM requests.
        temperature: LLM sampling temperature (0.0-2.0).
        max_tokens: Maximum response tokens.

    Example:
        >>> from kfp import compiler
        >>> compiler.Compiler().compile(sdg_pvc_export_pipeline, package_path="sdg_pvc_export_pipeline.yaml")
    """
    sdg_task = sdg(
        input_pvc_path=input_file_path,
        flow_id=flow_id,
        model=model,
        max_concurrency=max_concurrency,
        temperature=temperature,
        max_tokens=max_tokens,
        export_to_pvc=True,
        export_path=export_base_path,
    )

    # Mount PVC for both input and export
    mount_pvc(
        task=sdg_task,
        pvc_name=pvc_name,
        mount_path="/mnt/data",
    )

    # Inject LLM API credentials from Kubernetes secret
    use_secret_as_env(
        task=sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={"OPENAI_APIKEY": "LLM_API_KEY"},
    )


@dsl.component(
    packages_to_install=["pandas"],
)
def create_sample_data(output_data: dsl.Output[dsl.Dataset]) -> None:
    """Create a sample dataset for demonstration purposes.

    Generates a small JSONL dataset with sample questions that can be
    used as input to SDG flows for testing and demonstration.

    Args:
        output_data: KFP Dataset artifact containing the generated sample data.
    """
    import pandas as pd

    # Create sample data with questions
    data = [
        {"question": "What is machine learning?"},
        {"question": "How does a neural network work?"},
        {"question": "What is the difference between supervised and unsupervised learning?"},
    ]

    df = pd.DataFrame(data)
    df.to_json(output_data.path, orient="records", lines=True)


@dsl.pipeline(
    name="sdg-artifact-chaining-pipeline",
    description="SDG pipeline demonstrating artifact chaining between components",
)
def sdg_artifact_chaining_pipeline(
    flow_id: str = "green-clay-812",
    model: str = "openai/gpt-4o-mini",
    max_concurrency: int = 10,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> None:
    """Run SDG flow consuming an upstream component's output artifact.

    This pipeline demonstrates artifact chaining, where the SDG component
    consumes the output artifact from an upstream component. This pattern
    enables composable pipelines where data flows naturally between steps
    without requiring PVC mounts or intermediate storage.

    The pipeline structure:
    1. create_sample_data() generates a dataset
    2. sdg() consumes that dataset as input_artifact
    3. KFP handles artifact passing automatically

    Args:
        flow_id: Built-in SDG Hub flow ID from the registry.
        model: LiteLLM model identifier (e.g., 'openai/gpt-4o-mini').
        max_concurrency: Maximum concurrent LLM requests.
        temperature: LLM sampling temperature (0.0-2.0).
        max_tokens: Maximum response tokens.

    Example:
        >>> from kfp import compiler
        >>> compiler.Compiler().compile(
        ...     sdg_artifact_chaining_pipeline, package_path="sdg_artifact_chaining_pipeline.yaml"
        ... )
    """
    # Step 1: Create sample input data
    data_task = create_sample_data()

    # Step 2: Run SDG flow using the upstream artifact
    sdg_task = sdg(
        input_artifact=data_task.outputs["output_data"],
        flow_id=flow_id,
        model=model,
        max_concurrency=max_concurrency,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Inject LLM API credentials from Kubernetes secret
    use_secret_as_env(
        task=sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={"OPENAI_APIKEY": "LLM_API_KEY"},
    )


if __name__ == "__main__":
    """Compile all example pipelines to YAML files."""
    from kfp import compiler

    compiler.Compiler().compile(
        sdg_pvc_input_pipeline,
        package_path="sdg_pvc_input_pipeline.yaml",
    )
    print("Compiled: sdg_pvc_input_pipeline.yaml")

    compiler.Compiler().compile(
        sdg_pvc_export_pipeline,
        package_path="sdg_pvc_export_pipeline.yaml",
    )
    print("Compiled: sdg_pvc_export_pipeline.yaml")

    compiler.Compiler().compile(
        sdg_artifact_chaining_pipeline,
        package_path="sdg_artifact_chaining_pipeline.yaml",
    )
    print("Compiled: sdg_artifact_chaining_pipeline.yaml")
