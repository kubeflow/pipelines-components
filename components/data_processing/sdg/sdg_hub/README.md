# Sdg Hub ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Run an SDG Hub flow to generate synthetic data.

Loads input data, selects and configures a flow, executes it, and writes the output as a JSONL artifact with execution
metrics.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_artifact` | `dsl.Output[dsl.Dataset]` | `None` | KFP Dataset artifact for downstream components. |
| `output_metrics` | `dsl.Output[dsl.Metrics]` | `None` | KFP Metrics artifact with execution stats. |
| `input_artifact` | `dsl.Input[dsl.Dataset]` | `None` | KFP Dataset artifact from upstream component (optional). |
| `input_pvc_path` | `str` | `""` | Path to JSONL input file on a mounted PVC (optional). |
| `flow_id` | `str` | `""` | Built-in flow ID from the SDG Hub registry. |
| `flow_yaml_path` | `str` | `""` | Path to a custom flow YAML file. |
| `model` | `str` | `""` | LiteLLM model identifier (e.g. 'openai/gpt-4o-mini'). |
| `max_concurrency` | `int` | `10` | Maximum concurrent LLM requests. |
| `checkpoint_pvc_path` | `str` | `""` | PVC path for checkpoints (enables resume). |
| `save_freq` | `int` | `100` | Checkpoint save frequency (number of samples). |
| `log_level` | `str` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR). |
| `temperature` | `float` | `-1.0` | LLM sampling temperature (0.0-2.0). Use -1 for flow default. |
| `max_tokens` | `int` | `-1` | Maximum response tokens. Use -1 for flow default. |
| `export_to_pvc` | `bool` | `False` | Whether to export output to PVC (in addition to KFP artifact). |
| `export_path` | `str` | `""` | Base PVC path for exports (required if export_to_pvc is True). |
| `runtime_params` | `dict` | `{}` | Per-block parameter overrides as a dict of {block_name: {param: value}}. |

## Metadata 🗂️

- **Name**: sdg_hub
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: SDG Hub, Version: >=0.7.0
    - Name: LiteLLM, Version: >=1.0.0
- **Tags**:
  - sdg
  - synthetic_data_generation
  - llm
  - data_processing
- **Last Verified**: 2026-02-24 00:00:00+00:00
- **Owners**:
  - Approvers:
    - beatsmonster
    - shivchander
    - eshwarprasadS
    - abhi1092
  - Reviewers:
    - beatsmonster
    - shivchander
    - eshwarprasadS
    - abhi1092

## Additional Resources 📚

- **Documentation**: [https://github.com/Red-Hat-AI-Innovation-Team/sdg_hub](https://github.com/Red-Hat-AI-Innovation-Team/sdg_hub)

<!-- custom-content -->

## Outputs

- `output_artifact` (`Dataset`): JSONL file with generated synthetic data
- `output_metrics` (`Metrics`): Execution metrics — `input_rows`, `output_rows`, `execution_time_seconds`

## Usage

> **Note:** The import paths below assume you are compiling from the repo root with
> `PYTHONPATH=.`. If you installed `kfp-components` as a package, use
> `from kfp_components.components.data_processing.sdg.sdg_hub import sdg` instead.

### Basic PVC Input

```python
from components.data_processing.sdg.sdg_hub import sdg
from kfp import dsl
from kfp_kubernetes import mount_pvc, use_secret_as_env

@dsl.pipeline(name="sdg-pipeline")
def my_pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_id="green-clay-812",
        model="openai/gpt-4o-mini",
    )

    mount_pvc(task=sdg_task, pvc_name="data-pvc", mount_path="/mnt/data")
    use_secret_as_env(
        task=sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={"api_key": "LLM_API_KEY"},
    )
```

### Artifact Chaining

```python
from components.data_processing.sdg.sdg_hub import sdg
from kfp import dsl
from kfp_kubernetes import use_secret_as_env

@dsl.component(packages_to_install=["pandas"])
def preprocess_data(output_data: dsl.Output[dsl.Dataset]) -> None:
    import pandas as pd
    # ... preprocessing logic ...
    df.to_json(output_data.path, orient="records", lines=True)

@dsl.pipeline(name="sdg-chained-pipeline")
def chained_pipeline():
    preprocess_task = preprocess_data()
    sdg_task = sdg(
        input_artifact=preprocess_task.outputs["output_data"],
        flow_id="green-clay-812",
        model="openai/gpt-4o-mini",
    )
    use_secret_as_env(
        task=sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={"api_key": "LLM_API_KEY"},
    )
```

### PVC Export

```python
from components.data_processing.sdg.sdg_hub import sdg
from kfp import dsl
from kfp_kubernetes import mount_pvc, use_secret_as_env

@dsl.pipeline(name="sdg-export-pipeline")
def export_pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_id="green-clay-812",
        model="openai/gpt-4o-mini",
        export_to_pvc=True,
        export_path="/mnt/data/exports",
    )
    mount_pvc(task=sdg_task, pvc_name="data-pvc", mount_path="/mnt/data")
    use_secret_as_env(
        task=sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={"api_key": "LLM_API_KEY"},
    )
```

Exports are saved to: `{export_path}/{flow_id}/{timestamp}/generated.jsonl`

## Environment Variables

For flows with LLM blocks, set these via Kubernetes Secrets:

- `LLM_API_KEY`: API key for the LLM provider
- `LLM_API_BASE`: API base URL (optional, for self-hosted models)

## Local Development

### Prerequisites

```bash
# From the repo root
uv venv && source .venv/bin/activate
uv sync --extra test
```

### Running the Component Locally

KFP's `LocalRunner` does not support `Input[Dataset]` artifacts, so local execution
calls `sdg.python_func()` directly with mock artifact objects.

A ready-to-run script is provided at `shared/run_local.py`:

```bash
cd components/data_processing/sdg/sdg_hub
LLM_API_KEY="<your-api-key>" python shared/run_local.py
```

This runs the LLM test flow against `tests/test_data/sample_input.jsonl` using
`gpt-4o-mini`, prints the generated output, and cleans up the temp directory.

### Running Tests

```bash
# Unit tests (no API key needed)
pytest components/data_processing/sdg/sdg_hub/tests/test_component_unit.py -v

# Integration test with transform-only flow (no API key needed)
pytest components/data_processing/sdg/sdg_hub/tests/test_component_local.py::TestSdgHubLocalRunner -v

# LLM E2E tests (requires API key)
LLM_API_KEY="<your-api-key>" pytest components/data_processing/sdg/sdg_hub/tests/test_component_local.py::TestSdgHubLLMFlow -v
```

## Running on Red Hat OpenShift AI

### OpenShift AI Prerequisites

- OpenShift AI with a pipeline server configured in your data science project
- `oc` CLI logged in to the cluster
- S3-compatible object storage configured for the pipeline server
- KFP SDK installed: `pip install kfp`

### 1. Create Cluster Resources

Create a K8s Secret for your LLM API credentials:

```bash
oc create secret generic llm-credentials \
  --from-literal=api_key="<your-api-key>" \
  -n <namespace>
```

If using a custom flow YAML, create ConfigMaps for the flow and prompt files:

```bash
oc create configmap sdg-flow \
  --from-file=flow.yaml=path/to/your/flow.yaml \
  -n <namespace>

oc create configmap sdg-prompts \
  --from-file=prompt.yaml=path/to/your/prompt.yaml \
  -n <namespace>
```

### 2. Define and Compile the Pipeline

```python
from kfp import compiler, dsl
from kfp_kubernetes import use_config_map_as_volume, use_secret_as_env
from components.data_processing.sdg.sdg_hub.component import sdg

@dsl.pipeline(name="sdg-pipeline")
def sdg_pipeline(model: str = "openai/gpt-4o-mini"):
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_yaml_path="/etc/sdg/flow.yaml",
        model=model,
        max_concurrency=1,
    )

    use_config_map_as_volume(task=sdg_task, config_map_name="sdg-flow", mount_path="/etc/sdg")
    use_config_map_as_volume(task=sdg_task, config_map_name="sdg-prompts", mount_path="/etc/sdg/prompts")
    use_secret_as_env(task=sdg_task, secret_name="llm-credentials",
                      secret_key_to_env={"api_key": "LLM_API_KEY"})

compiler.Compiler().compile(sdg_pipeline, package_path="sdg_pipeline.yaml")
```

### 3. Submit the Pipeline

```python
import kfp
import os

host = os.environ["KFP_ROUTE"]
token = os.environ["KFP_TOKEN"]

client = kfp.Client(host=f"https://{host}", existing_token=token, ssl_ca_cert=False)

run = client.create_run_from_pipeline_package(
    pipeline_file="sdg_pipeline.yaml",
    run_name="sdg-run",
    arguments={"model": "openai/gpt-4o-mini"},
)
print(f"Run: https://{host}/#/runs/details/{run.run_id}")
```

### 4. Monitor

```python
run = client.get_run(run_id=run.run_id)
print(run.state)  # RUNNING → SUCCEEDED / FAILED
```

Or via `oc`:

```bash
oc get pods -n <namespace> | grep sdg-pipeline
oc logs <pod-name> -c main -n <namespace>
```

<details>
<summary><h2>Architecture Design Document</h2></summary>

## SDG Hub KFP Component Architecture Design

### Document Information

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Authors** | SDG Hub Team |
| **Created** | 2025-01-16 |
| **Last Updated** | 2025-01-16 |

---

### Table of Contents

1. [Overview](#1-overview)
2. [Background & Motivation](#2-background--motivation)
3. [Component Scope & Granularity](#3-component-scope--granularity)
4. [Input Data Interface](#4-input-data-interface)
5. [Output Data Interface](#5-output-data-interface)
6. [Flow Selection & Configuration](#6-flow-selection--configuration)
7. [Model/LLM Configuration](#7-modelllm-configuration)
8. [Execution Configuration](#8-execution-configuration)
9. [Error Handling & Observability](#9-error-handling--observability)
10. [Container & Packaging](#10-container--packaging)

---

### 1. Overview

#### 1.1 What We Are Building

A **Kubeflow Pipelines (KFP) component** that wraps the SDG Hub SDK to enable synthetic data generation within Kubernetes-native ML pipelines. This component allows users to:

- Run SDG Hub flows (built-in or custom) as pipeline steps
- Generate synthetic training data at production scale
- Integrate seamlessly with upstream data preparation and downstream model training components

#### 1.2 Component at a Glance

```mermaid
graph TB
    subgraph sdg["sdg Component"]
        direction TB
        subgraph inputs["INPUTS"]
            A1["KFP Artifact"]
            A2["PVC Path"]
        end
        subgraph config["CONFIGURATION"]
            B1["Flow: built-in ID or custom YAML"]
            B2["Model: LiteLLM + K8s Secret"]
            B3["Execution: concurrency, checkpointing"]
            B4["LLM Params: temperature, max_tokens"]
        end
        subgraph outputs["OUTPUTS"]
            C1["KFP Artifact"]
            C2["KFP Metrics"]
            C3["PVC Export (optional)"]
        end
    end
```

#### 1.3 Design Principles

| Principle | Description |
|-----------|-------------|
| **Kubernetes Native** | Use K8s primitives: Secrets for credentials, PVCs for storage, ConfigMaps for configuration |
| **KFP Native** | Use KFP Artifacts for data passing, Metrics for observability, native pipeline composition |
| **Production Scale** | Designed for large datasets with checkpointing, concurrency control, and resumability |
| **Flexible I/O** | Support multiple input sources and output destinations for e2e pipeline integration |
| **Minimal Surface** | Expose only what's needed for production use; no experimentation/discovery features |

---

### 2. Background & Motivation

#### 2.1 What is SDG Hub?

SDG Hub is a Python framework for synthetic data generation using composable blocks and flows:

- **Blocks** are atomic data transformation units (LLM chat, text parsing, filtering)
- **Flows** orchestrate multiple blocks into YAML-defined pipelines
- **Data flows** through blocks sequentially: `dataset -> Block1 -> Block2 -> ... -> enriched_dataset`

```mermaid
flowchart LR
    A[Input Dataset] --> B[Block 1<br/>Prompt]
    B --> C[Block 2<br/>LLM]
    C --> D[Block 3<br/>Parser]
    D --> E[Output Dataset]
```

#### 2.2 Why a KFP Component?

**Problem:** Organizations need to generate synthetic training data as part of their ML pipelines, but:

1. Running SDG manually doesn't integrate with existing pipeline infrastructure
2. Scaling requires Kubernetes orchestration
3. Credential management needs enterprise-grade security
4. Long-running jobs need checkpointing and observability

**Solution:** A KFP component that provides:

| Capability | Benefit |
|------------|---------|
| **Pipeline Integration** | Chain with data prep, training, and evaluation steps |
| **K8s Orchestration** | Automatic scheduling, resource management, scaling |
| **Secret Management** | Secure credential handling via K8s Secrets |
| **Checkpointing** | Resume interrupted jobs, survive pod restarts |
| **Observability** | Native KFP metrics, logging, artifact tracking |

#### 2.3 Target Use Cases

```mermaid
flowchart LR
    subgraph pipeline["ML Pipeline with SDG"]
        A[Data Prep] --> B[SDG]
        B --> C[Model Training]
    end
```

Examples:

- **Knowledge tuning**: document -> QA pairs -> fine-tune LLM
- **Instruction tuning**: seed data -> diverse examples -> train
- **Data augmentation**: small dataset -> expanded dataset -> train

#### 2.4 Non-Goals

The following are explicitly **out of scope** for this component:

- Flow/block discovery and exploration (use SDK directly)
- Interactive experimentation (use notebooks)
- Flow development and debugging (use SDK's dry_run locally)
- Multi-flow orchestration (use multiple component instances)

---

### 3. Component Scope & Granularity

#### 3.1 Decision Summary

| Aspect | Decision |
|--------|----------|
| **Architecture** | Single monolithic component |
| **Flow Selection** | Support both built-in flows and custom YAML |
| **Scope** | Production execution only |

#### 3.2 Selected: Single Monolithic Component

One component handles everything: flow selection, model config, execution.

```mermaid
graph TB
    subgraph component["sdg Component"]
        A["Flow Selection"]
        B["Model Configuration"]
        C["Data Generation"]
        D["Checkpointing"]
        E["Metrics Collection"]
    end
```

**Why Selected:**

- Simple to use - one component does it all
- Fewer artifacts passed between components
- Matches production pattern: "run this flow on this data"
- Validation is built into `flow.generate()`

#### 3.3 Rejected Options

| Option | Why Rejected |
|--------|--------------|
| **Multi-Component** (separate validate, generate, postprocess) | Adds complexity; validation already built into generate() |
| **Core + Utilities** (main component + discovery tools) | Utilities rarely used in production; extra maintenance |

---

### 4. Input Data Interface

#### 4.1 Decision Summary

| Aspect | Decision |
|--------|----------|
| **Primary Interface** | KFP Artifact (native tracking & composition) |
| **Alternative Inputs** | Import from PVC |
| **File Format** | JSONL only |
| **Checkpoint Resume** | Via checkpoint PVC path |

#### 4.2 Input Architecture

The component uses **KFP Artifacts as the primary interface** for pipeline composition and tracking. PVC is an "import" option that gets converted to artifacts internally.

```mermaid
flowchart TB
    subgraph options["Input Options"]
        direction TB
        A["Option A: KFP Artifact<br/>(Native - Preferred)"]
        B["Option B: PVC Import"]
    end

    subgraph component["SDG Component"]
        D["Internal Processing"]
    end

    A -->|"Direct"| D
    B -->|"Import & Wrap"| D

    style A fill:#90EE90
```

**Priority:** Artifact > PVC Path

#### 4.3 Input Flow Details

##### Option A: KFP Artifact (Native - Preferred)

```mermaid
sequenceDiagram
    participant Upstream as Upstream Component
    participant KFP as KFP Orchestrator
    participant SDG as SDG Component

    Upstream->>KFP: Output[Dataset] artifact
    KFP->>SDG: Input[Dataset] artifact
    Note over SDG: Native pipeline composition<br/>Tracked in KFP UI
```

##### Option B: PVC Import

```mermaid
sequenceDiagram
    participant PVC as PVC Volume
    participant SDG as SDG Component
    participant Internal as Internal Artifact

    SDG->>PVC: Read /mnt/data/input.jsonl
    SDG->>Internal: Wrap as artifact
    Note over SDG: Data pre-staged on shared storage<br/>No transfer overhead for large datasets
```

#### 4.4 Why This Design?

| Alternative | Why Rejected |
|-------------|--------------|
| **KFP Artifacts Only** | Doesn't support pre-staged data; transfer overhead for large datasets |
| **Volume Paths Only** | Loses KFP native tracking; harder pipeline composition |

**Selected: Hybrid with Import/Export** because it provides KFP native tracking while supporting external data sources.

#### 4.5 File Format Decision

| Format | Decision | Rationale |
|--------|----------|-----------|
| **JSONL** | Supported | Human-readable, matches SDK checkpoint format, simple |
| **Parquet/CSV** | Not supported | Adds complexity; JSONL sufficient for production |

#### 4.6 Checkpoint Resume

The component supports resuming interrupted jobs via checkpoints stored on PVC.

```mermaid
flowchart TB
    subgraph first["First Run"]
        A1[Input Dataset<br/>1000 rows] --> B1[Process all samples]
        B1 --> C1[Save checkpoints<br/>to PVC]
    end

    subgraph interrupt["Interrupted Run"]
        A2[Processing<br/>row 600...] --> B2[Pod dies]
        B2 --> C2[Checkpoint saved<br/>up to row 500]
    end

    subgraph resume["Resume Run"]
        A3[Load checkpoints<br/>from PVC] --> B3[Find remaining<br/>500 samples]
        B3 --> C3[Process only<br/>remaining 500]
    end

    first --> interrupt
    interrupt --> resume
```

**How It Works:**

1. On start: Check `checkpoint_pvc_path` for existing checkpoints
2. If found: Load completed samples, identify remaining work
3. Processing: Only process samples not yet completed
4. Periodic saves: Save checkpoints every `save_freq` samples
5. Final merge: Combine checkpoint data with newly processed data

**Why PVC for Checkpoints:** PVC persists across pod restarts; KFP temp paths and EmptyDir do not.

#### 4.7 Component Interface (Input Parameters)

```python
@component
def sdg(
    # ==================== INPUT OPTIONS ====================
    # Option A: KFP Artifact (native, preferred)
    input_artifact: Input[Dataset] = None,

    # Option B: Import from PVC
    input_pvc_path: str = "",  # e.g., "/mnt/data/input.jsonl"

    # ==================== CHECKPOINT RESUME ====================
    checkpoint_pvc_path: str = "",  # e.g., "/mnt/checkpoints/"
    # ...
):
```

#### 4.8 Usage Examples

##### Example 1: Input from Upstream Component

```python
@dsl.pipeline
def training_pipeline():
    prep_task = data_preparation(raw_data_path="/data/raw")

    sdg_task = sdg(
        input_artifact=prep_task.outputs["output_dataset"],
        flow_id="extractive-summary-qa",
    )

    train_task = train_model(
        training_data=sdg_task.outputs["output_artifact"],
    )
```

##### Example 2: Input from PVC

```python
sdg_task = sdg(
    input_pvc_path="/mnt/shared-data/seed_documents.jsonl",
    flow_id="extractive-summary-qa",
)
```

##### Example 3: Resume from Checkpoint

```python
sdg_task = sdg(
    input_pvc_path="/mnt/data/large_dataset.jsonl",
    checkpoint_pvc_path="/mnt/checkpoints/job-123/",
    save_freq=100,
    flow_id="extractive-summary-qa",
)
# If pod restarts, checkpoints are automatically loaded and resumed
```

---

### 5. Output Data Interface

#### 5.1 Decision Summary

| Aspect | Decision |
|--------|----------|
| **Primary Output** | KFP Artifact (always produced) |
| **Optional Export** | Export to PVC |
| **Output Structure** | Nested: `{path}/{flow_id}/{timestamp}/generated.jsonl` |
| **Metrics** | KFP Metrics artifact (native) |

#### 5.2 Output Architecture

The component **always produces a KFP Artifact** for native pipeline composition. Users can **optionally export** to PVC for external access.

```mermaid
flowchart TB
    subgraph component["SDG Component"]
        A[Generated DataFrame]
    end

    subgraph outputs["Output Handler"]
        B["KFP Artifact<br/>(Always)"]
        C["PVC Export<br/>(Optional)"]
        D["KFP Metrics<br/>(Always)"]
    end

    A --> B
    A --> C
    A --> D

    B --> E["KFP Artifact Store<br/>(MinIO/S3/GCS)"]
    C --> F["{export_path}/{flow_id}/{timestamp}/generated.jsonl"]
    D --> G["Visible in KFP UI"]

    style B fill:#90EE90
    style D fill:#90EE90
```

#### 5.3 Why Always Produce KFP Artifact?

| Benefit | Description |
|---------|-------------|
| **Pipeline Composition** | Enables `sdg_task.outputs["output_artifact"]` for downstream steps |
| **Tracking** | Visible in KFP UI; linked to pipeline run |
| **Lineage** | KFP tracks artifact provenance automatically |
| **Consistency** | Same interface regardless of input source |

#### 5.4 Optional PVC Export

When `export_to_pvc=True`, output is **also** written to PVC:

```text
{export_path}/{flow_id}/{timestamp}/generated.jsonl

Example:
/mnt/output/extractive-summary-qa/20250116_143052/generated.jsonl
```

**Nested structure rationale:**

- `flow_id`: Identifies which flow produced the output
- `timestamp`: Supports multiple runs without overwriting

#### 5.5 KFP Metrics

The component produces metrics visible in KFP UI:

```python
metrics.log_metric("total_input_rows", 1000)
metrics.log_metric("total_output_rows", 850)
metrics.log_metric("execution_time_seconds", 3456.7)
metrics.log_metric("successful_blocks", 8)
metrics.log_metric("failed_blocks", 0)
```

#### 5.6 Component Interface (Output Parameters)

```python
@component
def sdg(
    # ... input parameters ...

    # ==================== OUTPUT ====================
    output_artifact: Output[Dataset],
    output_metrics: Output[Metrics],
    export_to_pvc: bool = False,
    export_path: str = "",  # e.g., "/mnt/output/"
):
```

#### 5.7 Usage Examples

##### Example 1: Output to Downstream Component Only

```python
@dsl.pipeline
def training_pipeline():
    sdg_task = sdg(
        input_artifact=prep_task.outputs["dataset"],
        flow_id="qa-generation",
    )

    train_task = train_model(
        training_data=sdg_task.outputs["output_artifact"],
    )
```

##### Example 2: Output to Both Artifact and PVC

```python
sdg_task = sdg(
    input_pvc_path="/mnt/data/input.jsonl",
    flow_id="qa-generation",
    export_to_pvc=True,
    export_path="/mnt/output/",
)
# Output at: /mnt/output/qa-generation/20250116_143052/generated.jsonl
# Artifact still available for pipeline composition
```

---

### 6. Flow Selection & Configuration

#### 6.1 Decision Summary

| Aspect | Decision |
|--------|----------|
| **Flow Selection** | Built-in flow ID or custom YAML path |
| **Custom Flow Source** | Path-based (YAML mounted from ConfigMap) |
| **Runtime Params Structure** | Flat dict (matches SDK) |
| **Component-Level LLM Params** | Mirror SDK block-level params |
| **Override Priority** | Flow YAML → Component-level → Block-level |
| **Flow Validation** | No pre-validation; rely on generate() fail-fast |

#### 6.2 Flow Selection Modes

The component supports two mutually exclusive modes for specifying which flow to run:

```mermaid
flowchart TB
    subgraph selection["Flow Selection"]
        A["Option A: Built-in Flow<br/>flow_id parameter"]
        B["Option B: Custom Flow<br/>flow_yaml_path parameter"]
    end

    A --> C["FlowRegistry.get_flow_path(flow_id)"]
    B --> D["Read from mounted path"]

    C --> E["Flow.from_yaml()"]
    D --> E

    style A fill:#90EE90
    style B fill:#87CEEB
```

| Mode | Parameter | Use Case |
|------|-----------|----------|
| **Built-in Flow** | `flow_id` | Use pre-packaged flows from SDG Hub registry |
| **Custom Flow** | `flow_yaml_path` | Use custom flow YAML mounted from ConfigMap |

**Priority:** If both provided, `flow_yaml_path` takes precedence.

#### 6.3 Custom Flow YAML from ConfigMap

Custom flow YAML files are mounted into the container from Kubernetes ConfigMaps. This follows K8s-native configuration patterns.

```mermaid
sequenceDiagram
    participant CM as ConfigMap
    participant K8s as K8s Volume Mount
    participant Pod as SDG Pod
    participant Comp as SDG Component

    CM->>K8s: flow.yaml content
    K8s->>Pod: Mount at /etc/sdg/flow.yaml
    Pod->>Comp: flow_yaml_path="/etc/sdg/flow.yaml"
    Comp->>Comp: Flow.from_yaml(path)
```

**Why ConfigMap over other options:**

| Alternative | Why Not Selected |
|-------------|------------------|
| **Inline YAML as string param** | Unwieldy for complex flows; hard to manage |
| **KFP Artifact** | Flows are config, not data; ConfigMap is more appropriate |
| **PVC only** | ConfigMap is more K8s-native for configuration |

**Note:** PVC paths also work since the component just reads from a file path. ConfigMap is the recommended approach for K8s-native configuration management.

##### ConfigMap Example

```yaml
# K8s ConfigMap definition
apiVersion: v1
kind: ConfigMap
metadata:
  name: custom-qa-flow
  namespace: ml-pipelines
data:
  flow.yaml: |
    metadata:
      name: "Custom QA Generation Flow"
      version: "1.0.0"
      description: "Organization-specific QA generation"

    blocks:
      - block_type: PromptBuilderBlock
        block_config:
          block_name: build_prompt
          input_cols: ["document"]
          output_cols: ["messages"]
          prompt_config_path: prompt.yaml

      - block_type: LLMChatBlock
        block_config:
          block_name: generate_qa
          input_cols: ["messages"]
          output_cols: ["response"]
          max_tokens: 2048
```

##### Pipeline Usage with ConfigMap

```python
from kfp import dsl
from kfp import kubernetes

@dsl.pipeline
def training_pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_yaml_path="/etc/sdg/flow.yaml",  # Mounted from ConfigMap
        model="hosted_vllm/meta-llama/Llama-3.3-70B-Instruct",
    )

    # Mount ConfigMap as volume
    kubernetes.use_config_map_as_volume(
        sdg_task,
        config_map_name="custom-qa-flow",
        mount_path="/etc/sdg",
    )
```

#### 6.4 Parameter Override System

The component implements a three-tier parameter override system that mirrors the SDK's behavior while adding a component-level tier for convenience.

```mermaid
flowchart LR
    A["Flow YAML<br/>Block Defaults<br/>(Lowest Priority)"] --> B["Component-Level<br/>LLM Params<br/>(Medium Priority)"]
    B --> C["runtime_params<br/>Block-Specific<br/>(Highest Priority)"]
    C --> D["Final Block<br/>Configuration"]
```

**Override Priority (lowest to highest):**

1. **Flow YAML Defaults**: Parameters defined in the flow's block configurations
2. **Component-Level Params**: Global LLM parameters passed to the component
3. **Block-Level Overrides**: Per-block settings in `runtime_params` dict

#### 6.5 Component-Level LLM Parameters

The component exposes common LLM parameters at the component level for convenience. These are applied globally to all LLM blocks, then can be overridden per-block via `runtime_params`.

**Parameters (mirroring SDK's LLMChatBlock):**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `temperature` | float | `-1.0` | Generation randomness (0.0-2.0). Use `-1.0` for flow YAML default |
| `max_tokens` | int | `-1` | Maximum response length. Use `-1` for flow YAML default |

**Sentinel values:** The defaults of `-1.0` for temperature and `-1` for max_tokens act as sentinel values indicating "use the value defined in the flow YAML." This allows users to either accept flow defaults or override them at the component level.

**Why expose at component level:**

- **Convenience**: Common parameters don't require `runtime_params` dict
- **Discoverability**: Visible in component interface documentation
- **SDK Consistency**: Matches parameters available on SDK blocks

#### 6.6 Runtime Parameters (Block-Level Overrides)

The `runtime_params` parameter accepts a flat dict matching the SDK's interface. Keys are block names, values are parameter dicts.

```python
runtime_params = {
    # Block-specific overrides (keyed by block_name)
    "gen_detailed_summary": {
        "n": 50,
        "max_tokens": 4096,
        "temperature": 0.5,
    },
    "question_generation": {
        "temperature": 0.9,
        "max_tokens": 256,
    },
    "quality_filter": {
        "filter_value": 0.85,
    },
}
```

**Why flat dict over structured list:**

| Alternative | Why Not Selected |
|-------------|------------------|
| **Structured list** `[{block_name: ..., params: {...}}]` | More verbose; doesn't match SDK interface |

**Selected: Flat dict** for SDK consistency and simplicity.

#### 6.7 Flow Validation

The component does **not** perform pre-validation (dry_run) before execution.

**Rationale:**

- `flow.generate()` already validates inputs and fails fast with clear errors
- Pre-validation adds latency without benefit in production
- Flows used in production are pre-tested during development
- Clear error messages from `generate()` are sufficient for debugging

#### 6.8 Component Interface (Flow & Params)

```python
@component
def sdg(
    # ... input/output params ...

    # ==================== FLOW SELECTION ====================
    flow_id: str = "",           # Built-in flow from registry
    flow_yaml_path: str = "",    # Custom flow (mounted from ConfigMap)

    # ==================== COMPONENT-LEVEL LLM PARAMS ====================
    # Applied globally to all LLM blocks; overridable by runtime_params
    temperature: float = -1.0,  # -1 means use flow YAML default
    max_tokens: int = -1,       # -1 means use flow YAML default

    # ==================== BLOCK-LEVEL OVERRIDES ====================
    runtime_params: dict = {},
    # Example:
    # {
    #     "gen_detailed_summary": {"max_tokens": 4096},
    #     "question_generation": {"temperature": 0.9},
    # }
):
```

#### 6.9 Usage Examples

##### Example 1: Built-in Flow with Component-Level Params

```python
sdg_task = sdg(
    input_pvc_path="/mnt/data/input.jsonl",
    flow_id="extractive-summary-qa",

    # Component-level params (apply to all LLM blocks)
    temperature=0.7,
    max_tokens=2048,
)
```

##### Example 2: Custom Flow from ConfigMap

```python
@dsl.pipeline
def custom_flow_pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_yaml_path="/etc/sdg/flow.yaml",
        temperature=0.7,
    )

    # Mount ConfigMap
    kubernetes.use_config_map_as_volume(
        sdg_task,
        config_map_name="my-custom-flow",
        mount_path="/etc/sdg",
    )
```

##### Example 3: Component-Level + Block-Level Overrides

```python
sdg_task = sdg(
    input_pvc_path="/mnt/data/input.jsonl",
    flow_id="extractive-summary-qa",

    # Component-level defaults
    temperature=0.7,
    max_tokens=2048,

    # Block-specific overrides (highest priority)
    runtime_params={
        "gen_detailed_summary": {
            "n": 50,
            "temperature": 0.5,  # Overrides component-level 0.7
            "max_tokens": 4096,  # Overrides component-level 2048
        },
        "question_generation": {
            "temperature": 0.9,  # Overrides component-level 0.7
        },
    },
)
```

In this example:

- `gen_detailed_summary` uses temperature=0.5, max_tokens=4096
- `question_generation` uses temperature=0.9, max_tokens=2048 (component default)
- Other LLM blocks use temperature=0.7, max_tokens=2048 (component defaults)

---

### 7. Model/LLM Configuration

#### 7.1 Decision Summary

| Aspect | Decision |
|--------|----------|
| **Model Identifier** | Simple string parameter (LiteLLM format) |
| **Credential Storage** | K8s Secret with dedicated keys |
| **Secret Structure** | `api_key` and `api_base` keys |
| **Multiple Models** | Not supported (SDK limitation) |

#### 7.2 Model Identifier

The `model` parameter accepts a LiteLLM format string that specifies both the provider and model.

```python
model = "hosted_vllm/meta-llama/Llama-3.3-70B-Instruct"
#        ^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#        provider     model name
```

**Common LiteLLM provider formats:**

| Provider | Format | Example |
|----------|--------|---------|
| **vLLM** | `hosted_vllm/{model}` | `hosted_vllm/meta-llama/Llama-3.3-70B-Instruct` |
| **OpenAI** | `openai/{model}` | `openai/gpt-4` |
| **Azure OpenAI** | `azure/{deployment}` | `azure/gpt-4-deployment` |
| **Anthropic** | `anthropic/{model}` | `anthropic/claude-3-opus` |

**Why simple string (not structured dict):**

- LiteLLM already encodes provider in the model string
- Matches SDK interface
- Simple and familiar

#### 7.3 Credential Storage with K8s Secrets

Credentials are stored in Kubernetes Secrets and mounted as environment variables using KFP's native `kubernetes.use_secret_as_env()`. The component internally reads these environment variables (`LLM_API_KEY`, `LLM_API_BASE`) without requiring a component parameter.

```mermaid
flowchart TB
    subgraph secret["K8s Secret: llm-credentials"]
        A["api_key: sk-xxx..."]
        B["api_base: https://api.example.com/v1"]
    end

    subgraph kfp["KFP kubernetes Extension"]
        C["kubernetes.use_secret_as_env()"]
    end

    subgraph pod["SDG Pod"]
        D["env: LLM_API_KEY=sk-xxx..."]
        E["env: LLM_API_BASE=https://..."]
    end

    secret --> kfp
    kfp --> pod

    style secret fill:#FFE4B5
    style pod fill:#90EE90
```

**Why K8s Secrets over other options:**

| Alternative | Why Not Selected |
|-------------|------------------|
| **Inline parameters** | Credentials visible in pipeline definition and logs |
| **ConfigMap** | Not designed for sensitive data; no encryption at rest |
| **External vault** | Adds complexity; K8s Secrets sufficient for most cases |

#### 7.4 Secret Structure

Secrets are mounted as environment variables with standardized names (`LLM_API_KEY`, `LLM_API_BASE`). The component reads these via `os.environ.get()` internally.

```yaml
# K8s Secret definition
apiVersion: v1
kind: Secret
metadata:
  name: llm-credentials
  namespace: ml-pipelines
type: Opaque
stringData:
  api_key: "sk-xxxxxxxxxxxxxxxxxxxx"
  api_base: "https://api.example.com/v1"
```

#### 7.5 Secret Mounting in Pipelines

Secrets are mounted as environment variables via the pipeline definition using KFP's native Kubernetes extension. The component reads these environment variables internally.

```python
from kfp import dsl
from kfp import kubernetes

@dsl.pipeline
def training_pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_id="extractive-summary-qa",
        model="hosted_vllm/meta-llama/Llama-3.3-70B-Instruct",
    )

    # Mount secret as environment variables
    kubernetes.use_secret_as_env(
        sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={
            "api_key": "LLM_API_KEY",
            "api_base": "LLM_API_BASE",
        },
    )
```

**Internal component logic:**

```python
# Inside component implementation
import os

# Component reads environment variables directly
api_key = os.environ.get("LLM_API_KEY")
api_base = os.environ.get("LLM_API_BASE")

# Configure LiteLLM with these credentials
```

#### 7.6 Multiple Model Support

The component supports **only a single model configuration** per execution.

**Reason:** The SDK currently configures one LLM client globally for all blocks. Per-block model overrides are not supported in the SDK's `runtime_params`.

**Workaround for multi-model workflows:**

```mermaid
flowchart LR
    A[Input Data] --> B["SDG Task 1<br/>Model A"]
    B --> C["SDG Task 2<br/>Model B"]
    C --> D[Output Data]
```

Use separate SDG component instances in sequence, each with its own model configuration.

#### 7.7 Component Interface (Model Parameters)

```python
@component
def sdg(
    # ... other params ...

    # ==================== MODEL CONFIGURATION ====================
    model: str = "",
    # LiteLLM format: "provider/model-name"
    # Example: "hosted_vllm/meta-llama/Llama-3.3-70B-Instruct"

    # Note: Credentials are provided via environment variables (LLM_API_KEY, LLM_API_BASE)
    # mounted in the pipeline definition using kubernetes.use_secret_as_env()
):
```

#### 7.8 Usage Examples

##### Example 1: vLLM Endpoint

```yaml
# Secret
apiVersion: v1
kind: Secret
metadata:
  name: vllm-credentials
stringData:
  api_key: "token-abc123"
  api_base: "https://vllm.internal.company.com/v1"
```

```python
@dsl.pipeline
def pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_id="extractive-summary-qa",
        model="hosted_vllm/meta-llama/Llama-3.3-70B-Instruct",
    )

    kubernetes.use_secret_as_env(
        sdg_task,
        secret_name="vllm-credentials",
        secret_key_to_env={
            "api_key": "LLM_API_KEY",
            "api_base": "LLM_API_BASE",
        },
    )
```

##### Example 2: OpenAI API

```yaml
# Secret
apiVersion: v1
kind: Secret
metadata:
  name: openai-credentials
stringData:
  api_key: "sk-xxxxxxxxxxxxxxxxxxxx"
  api_base: "https://api.openai.com/v1"
```

```python
@dsl.pipeline
def pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_id="extractive-summary-qa",
        model="openai/gpt-4",
    )

    kubernetes.use_secret_as_env(
        sdg_task,
        secret_name="openai-credentials",
        secret_key_to_env={
            "api_key": "LLM_API_KEY",
            "api_base": "LLM_API_BASE",
        },
    )
```

---

### 8. Execution Configuration

#### 8.1 Decision Summary

| Aspect | Decision |
|--------|----------|
| **Concurrency Default** | `max_concurrency=10` (conservative) |
| **Checkpoint Frequency** | `save_freq=100` samples |
| **Log Level** | Component parameter (`log_level`) |
| **Resource Limits** | Use KFP native methods (no component params) |
| **Timeout** | Use KFP native methods (no component params) |

#### 8.2 Concurrency Control

The `max_concurrency` parameter limits parallel LLM requests to avoid rate limiting.

```python
max_concurrency: int = 10  # Conservative default
```

**Why 10 as default:**

- Safe for most LLM providers without hitting rate limits
- Users can increase for high-throughput endpoints (e.g., self-hosted vLLM)
- Users can decrease for providers with strict rate limits

#### 8.3 Checkpointing Configuration

Checkpointing saves progress to PVC, enabling resume after interruption.

```mermaid
flowchart LR
    subgraph processing["Flow Processing"]
        A["Sample 1-100"] --> B["Checkpoint 1"]
        C["Sample 101-200"] --> D["Checkpoint 2"]
        E["Sample 201-300"] --> F["Checkpoint 3"]
    end

    subgraph resume["On Restart"]
        G["Load checkpoints"] --> H["Skip completed"]
        H --> I["Process remaining"]
    end
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `checkpoint_pvc_path` | str | None | PVC path for checkpoints; None disables checkpointing |
| `save_freq` | int | 100 | Save checkpoint every N completed samples |

**Why `save_freq=100`:**

- Balances data loss risk (max 99 samples) with I/O overhead
- Reasonable for most dataset sizes
- Users can adjust based on sample processing time

**Checkpoint behavior:**

1. If `checkpoint_pvc_path` is None: No checkpointing (simpler, faster)
2. If path provided: Checkpoints saved every `save_freq` samples
3. On start: Automatically loads existing checkpoints and resumes

#### 8.4 Logging Configuration

Log level is controlled via a component parameter for easy pipeline configuration.

```python
log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
```

**Why component parameter (not env var only):**

- Visible in KFP UI and pipeline definition
- Easy to adjust per pipeline run
- More discoverable than environment variables

**Log output:**

- Logs go to stdout/stderr (K8s native)
- KFP captures and displays in task logs
- No separate log aggregation required

#### 8.5 Resource Configuration

Resource requests and limits are configured using **KFP's native methods**, not component parameters.

```python
@dsl.pipeline
def pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_id="extractive-summary-qa",
    )

    # Configure resources via KFP native methods
    sdg_task.set_cpu_request("2")
    sdg_task.set_cpu_limit("4")
    sdg_task.set_memory_request("8Gi")
    sdg_task.set_memory_limit("16Gi")
```

**Why KFP native (not component params):**

| Alternative | Why Not Selected |
|-------------|------------------|
| **Component parameters** | Duplicates KFP functionality; inconsistent with other components |
| **Hardcoded defaults** | Inflexible; different flows have different requirements |

**Selected: KFP native** because it's consistent with KFP patterns and avoids duplication.

#### 8.6 Timeout Configuration

Execution timeout is configured using **KFP's native method**.

```python
@dsl.pipeline
def pipeline():
    sdg_task = sdg(...)

    # Set timeout via KFP native method (seconds)
    sdg_task.set_timeout(7200)  # 2 hours
```

**Why KFP native:** Same rationale as resource configuration - avoids duplication, consistent with KFP patterns.

#### 8.7 Component Interface (Execution Parameters)

```python
@component
def sdg(
    # ... other params ...

    # ==================== EXECUTION ====================
    max_concurrency: int = 10,
    # Maximum concurrent LLM requests (default: 10)

    checkpoint_pvc_path: str = "",
    # PVC path for checkpoints; empty string disables checkpointing

    save_freq: int = 100,
    # Checkpoint save frequency in samples

    log_level: str = "INFO",
    # Logging level: DEBUG, INFO, WARNING, ERROR
):
```

#### 8.8 Usage Examples

##### Example 1: Default Execution Settings

```python
sdg_task = sdg(
    input_pvc_path="/mnt/data/input.jsonl",
    flow_id="extractive-summary-qa",
    model="hosted_vllm/meta-llama/Llama-3.3-70B-Instruct",
    # Uses defaults: max_concurrency=10, no checkpointing, log_level=INFO
)
```

##### Example 2: High-Throughput with Checkpointing

```python
@dsl.pipeline
def high_throughput_pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/large_dataset.jsonl",
        flow_id="extractive-summary-qa",
        model="hosted_vllm/meta-llama/Llama-3.3-70B-Instruct",

        # High concurrency for self-hosted vLLM
        max_concurrency=50,

        # Enable checkpointing for large job
        checkpoint_pvc_path="/mnt/checkpoints/job-001/",
        save_freq=200,  # Less frequent saves for speed

        log_level="DEBUG",  # Verbose logging for monitoring
    )

    # Allocate resources for high throughput
    sdg_task.set_cpu_request("4")
    sdg_task.set_memory_request("16Gi")
    sdg_task.set_timeout(14400)  # 4 hours

    # Mount checkpoint PVC
    kubernetes.mount_pvc(
        sdg_task,
        pvc_name="sdg-checkpoints",
        mount_path="/mnt/checkpoints",
    )
```

##### Example 3: Conservative Settings for Rate-Limited API

```python
sdg_task = sdg(
    input_pvc_path="/mnt/data/input.jsonl",
    flow_id="extractive-summary-qa",
    model="openai/gpt-4",

    # Low concurrency to avoid rate limits
    max_concurrency=5,

    # Frequent checkpoints (expensive API calls)
    checkpoint_pvc_path="/mnt/checkpoints/",
    save_freq=50,
)
```

---

### 9. Error Handling & Observability

#### 9.1 Decision Summary

| Aspect | Decision |
|--------|----------|
| **Failure Behavior** | Fail-fast on unrecoverable errors |
| **Retry Logic** | Use SDK defaults (tenacity-based) |
| **Metrics Scope** | Extended metrics including per-block timing |
| **Log Format** | Human-readable (standard Python logging) |
| **Progress Reporting** | Periodic log messages |

#### 9.2 Failure Behavior

The component uses **fail-fast** semantics: stop on first unrecoverable error and save checkpoint if enabled.

```mermaid
flowchart TB
    A[Processing Sample] --> B{Error?}
    B -->|No| C[Continue]
    B -->|Transient| D[SDK Retry Logic]
    D -->|Success| C
    D -->|Max Retries| E[Save Checkpoint]
    B -->|Unrecoverable| E
    E --> F[Fail Task]
    F --> G[KFP Retry at Task Level]
```

**Why fail-fast:**

- Simple and predictable behavior
- Checkpoints preserve progress before failure
- KFP handles task-level retries natively
- Avoids silently producing incomplete data

**Rejected alternative:**

| Alternative | Why Not Selected |
|-------------|------------------|
| **Best-effort (skip failures)** | May produce incomplete data silently; harder to debug |

#### 9.3 Retry Logic

The component **uses SDK defaults** for retry behavior. The SDK uses `tenacity` for transient error handling (rate limits, timeouts).

**Why not expose retry params:**

- SDK defaults are well-tuned for common providers
- Reduces component surface area
- Users rarely need to customize retry behavior

#### 9.4 KFP Metrics

> **Note:** The current implementation logs three core metrics: `input_rows`, `output_rows`, `execution_time_seconds`. Extended metrics below are planned for future releases.

The component produces extended metrics via `Output[Metrics]`, visible in KFP UI.

##### Metrics Reference

| Metric | Type | Description |
|--------|------|-------------|
| **Core Metrics** | | |
| `input_rows` | int | Total input samples |
| `output_rows` | int | Total output samples |
| `execution_time_seconds` | float | Total wall-clock time |
| **Checkpoint Metrics** | | |
| `checkpoints_saved` | int | Number of checkpoint files written |
| `samples_from_checkpoint` | int | Samples loaded from previous run |
| `samples_newly_processed` | int | Samples processed in this run |
| **Flow Metrics** | | |
| `blocks_total` | int | Total blocks in flow |
| `blocks_succeeded` | int | Blocks that completed successfully |
| **LLM Metrics** *(if SDK exposes)* | | |
| `llm_requests_total` | int | Total LLM API calls made |
| `llm_requests_retried` | int | Requests that required retry |
| `tokens_prompt_total` | int | Total prompt tokens used |
| `tokens_completion_total` | int | Total completion tokens used |
| **Per-Block Timing** | | |
| `block_{name}_duration_seconds` | float | Execution time per block |

**Note:** LLM token metrics depend on SDK exposing this data. If not available, they will be omitted.

##### Metrics Usage Example

```python
# Inside component implementation
from kfp.dsl import Metrics

def log_metrics(metrics: Metrics, stats: dict):
    # Core metrics
    metrics.log_metric("input_rows", stats["input_rows"])
    metrics.log_metric("output_rows", stats["output_rows"])
    metrics.log_metric("execution_time_seconds", stats["duration"])

    # Checkpoint metrics
    metrics.log_metric("checkpoints_saved", stats["checkpoints_saved"])
    metrics.log_metric("samples_from_checkpoint", stats["resumed_samples"])
    metrics.log_metric("samples_newly_processed", stats["new_samples"])

    # Flow metrics
    metrics.log_metric("blocks_total", stats["blocks_total"])
    metrics.log_metric("blocks_succeeded", stats["blocks_succeeded"])

    # Per-block timing
    for block_name, duration in stats["block_timings"].items():
        metrics.log_metric(f"block_{block_name}_duration_seconds", duration)

    # LLM metrics (if available)
    if "tokens_prompt" in stats:
        metrics.log_metric("tokens_prompt_total", stats["tokens_prompt"])
        metrics.log_metric("tokens_completion_total", stats["tokens_completion"])
```

#### 9.5 Logging Configuration

The component uses **human-readable** log format for easy viewing in KFP UI.

```text
# Log output example
2025-01-21 14:30:52 INFO  [sdg] Starting flow: extractive-summary-qa
2025-01-21 14:30:52 INFO  [sdg] Input: 1000 samples
2025-01-21 14:30:52 INFO  [sdg] Loaded 500 samples from checkpoint
2025-01-21 14:31:15 INFO  [sdg] Progress: 100/500 samples (20%)
2025-01-21 14:31:38 INFO  [sdg] Progress: 200/500 samples (40%)
2025-01-21 14:32:01 INFO  [sdg] Progress: 300/500 samples (60%)
2025-01-21 14:32:24 INFO  [sdg] Progress: 400/500 samples (80%)
2025-01-21 14:32:47 INFO  [sdg] Progress: 500/500 samples (100%)
2025-01-21 14:32:48 INFO  [sdg] Flow completed: 1000 output samples
2025-01-21 14:32:48 INFO  [sdg] Execution time: 116.2 seconds
```

**Why human-readable (not JSON):**

- Easier to read in KFP task logs UI
- Standard Python logging is familiar
- JSON structured logs add complexity with minimal benefit for this use case

#### 9.6 Progress Reporting

The component logs progress **periodically** during execution.

**Progress log frequency:**

- Log every `save_freq` samples (aligned with checkpointing)
- Always log start and completion
- Log errors with context

```python
# Progress logging implementation
def log_progress(current: int, total: int, start_time: float):
    elapsed = time.time() - start_time
    percent = (current / total) * 100
    rate = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / rate if rate > 0 else 0

    logger.info(
        f"Progress: {current}/{total} samples ({percent:.0f}%) "
        f"[{rate:.1f} samples/sec, ETA: {eta:.0f}s]"
    )
```

**Example output:**

```text
Progress: 100/1000 samples (10%) [8.3 samples/sec, ETA: 108s]
Progress: 200/1000 samples (20%) [8.5 samples/sec, ETA: 94s]
```

#### 9.7 Error Messages

When failures occur, the component provides actionable error messages:

```text
# Error message examples
ERROR [sdg] LLM API error: Rate limit exceeded (429).
      Retried 3 times, giving up. Checkpoint saved at /mnt/checkpoints/checkpoint_0005.jsonl
      Resume by re-running with same checkpoint_pvc_path.

ERROR [sdg] Flow validation failed: Required column 'document' not found in input dataset.
      Available columns: ['text', 'metadata', 'id']

ERROR [sdg] Block 'generate_qa' failed: Invalid JSON in LLM response.
      Sample ID: 42, Checkpoint saved with 400 completed samples.
```

---

### 10. Container & Packaging

> **Note:** The current implementation uses `packages_to_install` for simplicity. Migration to a pre-baked base image is planned for production deployments.

#### 10.1 Decision Summary

| Aspect | Decision |
|--------|----------|
| **Base Image** | UBI 9 Python 3.11 (`ubi9/python-311`) |
| **Dependencies** | Pre-baked in image (no runtime install) |
| **Versioning** | Match SDK semantic versioning (`sdg-hub>=0.7.0,<1.0`) |
| **Distribution** | Python package + auto-generated YAML |
| **Registry** | Mirror to Quay.io and GHCR |

#### 10.2 Base Image

The component uses Red Hat Universal Base Image (UBI) for enterprise compatibility.

```dockerfile
FROM registry.access.redhat.com/ubi9/python-311:latest

# Install SDG Hub with all dependencies
COPY . /src
RUN pip install --no-cache-dir /src

# Set entrypoint for KFP
ENTRYPOINT ["python", "-m", "sdg_hub.kfp"]
```

**Why UBI:**

| Alternative | Why Not Selected |
|-------------|------------------|
| **Python slim** | No enterprise support, security scanning, or FIPS compliance |
| **Custom base** | Extra maintenance; UBI provides what we need |

**Selected: UBI 9** for:

- Enterprise certification (OpenShift/RHOAI alignment)
- Security scanning and CVE patching
- FIPS compliance capability
- Red Hat support

#### 10.3 Dependency Management

All dependencies are **pre-baked** into the container image at build time.

```mermaid
flowchart LR
    subgraph build["Build Time"]
        A["Dockerfile"] --> B["pip install sdg-hub"]
        B --> C["Image with all deps"]
    end

    subgraph runtime["Runtime"]
        C --> D["Component executes immediately"]
    end
```

**Why pre-baked (not runtime install):**

| Alternative | Why Not Selected |
|-------------|------------------|
| **`packages_to_install`** | 30-60s pip install overhead per run; network dependency; version resolution risk |

**Benefits of pre-baked:**

- Fast startup (no download/install step)
- No network dependency at runtime
- Exact version reproducibility
- Reliable in air-gapped environments

#### 10.4 Image Versioning

Container images follow the **same semantic versioning as the SDK**.

```text
quay.io/redhat-ai-innovation/sdg-hub-kfp:v1.0.0
quay.io/redhat-ai-innovation/sdg-hub-kfp:v1.0.1
quay.io/redhat-ai-innovation/sdg-hub-kfp:v1.1.0
```

**Tag strategy:**

| Tag | Purpose |
|-----|---------|
| `v1.0.0` | Immutable release version |
| `v1.0` | Points to latest patch in minor version |
| `v1` | Points to latest minor in major version |
| `latest` | Points to most recent release |
| `sha-abc1234` | Git SHA for exact build traceability |

**Why match SDK versioning:**

- Clear compatibility: component `v1.2.0` uses SDK `v1.2.0`
- Single version number to communicate
- Aligned release process

#### 10.5 Component Distribution

The component is distributed via **Python package** with **auto-generated YAML** for flexibility.

```mermaid
flowchart TB
    subgraph source["Source of Truth"]
        A["Python @component<br/>src/sdg_hub/kfp/component.py"]
    end

    subgraph distribution["Distribution Formats"]
        B["Python Package<br/>pip install sdg-hub[kfp]"]
        C["component.yaml<br/>Auto-generated"]
    end

    A --> B
    A -->|"CI/CD generates"| C

    style A fill:#90EE90
```

##### Python Package (Primary)

Users install the package and import the component:

```python
# Install
pip install sdg-hub[kfp]

# Use in pipeline
from sdg_hub.kfp import sdg

@dsl.pipeline
def my_pipeline():
    sdg_task = sdg(
        input_pvc_path="/data/input.jsonl",
        flow_id="extractive-summary-qa",
    )
```

**Benefits:**

- IDE autocomplete and type hints
- Docstring documentation
- Version managed via pip
- Modern KFP v2 native pattern

##### Component YAML (Auto-Generated)

YAML is automatically generated from the Python definition—no dual maintenance.

```python
# scripts/generate_component_yaml.py
from kfp import compiler
from sdg_hub.kfp import sdg

compiler.Compiler().compile(
    pipeline_func=sdg,
    package_path="component.yaml"
)
```

Users can load from YAML without installing the package:

```python
from kfp.components import load_component_from_url

sdg = load_component_from_url(
    "https://github.com/Red-Hat-AI-Innovation-Team/sdg_hub/releases/download/v1.0.0/component.yaml"
)

@dsl.pipeline
def my_pipeline():
    sdg_task = sdg(input_pvc_path="/data/input.jsonl", ...)
```

**CI/CD Integration:**

```yaml
# .github/workflows/release.yaml
- name: Generate component YAML
  run: python scripts/generate_component_yaml.py

- name: Publish as release asset
  uses: actions/upload-release-asset@v1
  with:
    asset_path: component.yaml
    asset_name: component.yaml
```

#### 10.6 Container Registry

Images are mirrored to **both** Quay.io and GitHub Container Registry.

| Registry | Image |
|----------|-------|
| **Quay.io** (primary) | `quay.io/redhat-ai-innovation/sdg-hub-kfp:v1.0.0` |
| **GHCR** (mirror) | `ghcr.io/red-hat-ai-innovation-team/sdg-hub-kfp:v1.0.0` |

**Why both:**

- Quay.io: Red Hat ecosystem alignment, enterprise features
- GHCR: GitHub integration, backup availability
- Redundancy: if one registry has issues, users can pull from the other

#### 10.7 Dockerfile Structure

```dockerfile
# Dockerfile.kfp
FROM registry.access.redhat.com/ubi9/python-311:latest

LABEL maintainer="Red Hat AI Innovation Team"
LABEL version="${VERSION}"

# Install system dependencies (if any)
USER root
RUN dnf install -y --nodocs \
    && dnf clean all

# Install Python dependencies
USER 1001
WORKDIR /app

# Copy and install sdg-hub
COPY --chown=1001:0 . /app
RUN pip install --no-cache-dir ".[kfp]"

# Verify installation
RUN python -c "from sdg_hub.kfp import sdg; print('Component loaded successfully')"

# Default entrypoint (overridden by KFP)
ENTRYPOINT ["python"]
```

#### 10.8 Build & Release Process

```mermaid
flowchart TB
    subgraph trigger["Release Trigger"]
        A["Git tag: v1.0.0"]
    end

    subgraph ci["CI/CD Pipeline"]
        B["Run tests"]
        C["Build container image"]
        D["Generate component.yaml"]
        E["Push to Quay.io"]
        F["Push to GHCR"]
        G["Publish to PyPI"]
        H["Create GitHub Release"]
    end

    A --> B
    B --> C
    B --> D
    C --> E
    C --> F
    B --> G
    D --> H
    E --> H
    F --> H
    G --> H
```

**Release artifacts:**

- Container image on Quay.io and GHCR
- Python package on PyPI
- `component.yaml` as GitHub Release asset
- Release notes

---

### Appendix A: Complete Component Interface (Draft)

```python
from kfp.dsl import component, Input, Output, Dataset, Metrics

@component(
    packages_to_install=["sdg-hub>=0.7.0,<1.0"],
)
def sdg(
    # ==================== INPUT OPTIONS ====================
    input_artifact: Input[Dataset] = None,
    input_pvc_path: str = "",

    # ==================== OUTPUT ====================
    output_artifact: Output[Dataset],
    output_metrics: Output[Metrics],
    export_to_pvc: bool = False,
    export_path: str = "",

    # ==================== FLOW SELECTION ====================
    flow_id: str = "",
    flow_yaml_path: str = "",

    # ==================== MODEL CONFIGURATION ====================
    model: str = "",

    # ==================== EXECUTION ====================
    max_concurrency: int = 10,
    checkpoint_pvc_path: str = "",
    save_freq: int = 100,
    log_level: str = "INFO",

    # ==================== COMPONENT-LEVEL LLM PARAMETERS ====================
    # Applied globally to all LLM blocks; overridable by runtime_params
    temperature: float = -1.0,  # -1 means use flow YAML default
    max_tokens: int = -1,       # -1 means use flow YAML default

    # ==================== BLOCK-LEVEL OVERRIDES ====================
    runtime_params: dict = {},
):
    """
    SDG Hub data generation component for Kubeflow Pipelines.

    Runs a synthetic data generation flow on input data, producing
    enriched output suitable for model training.

    Args:
        input_artifact: KFP Dataset artifact from upstream component
        input_pvc_path: Path to JSONL file on mounted PVC
        output_artifact: KFP Dataset artifact for downstream components
        output_metrics: KFP Metrics artifact with execution stats
        export_to_pvc: Whether to also write output to PVC
        export_path: Base path for PVC export
        flow_id: Built-in flow ID from SDG Hub registry
        flow_yaml_path: Path to custom flow YAML (mounted from ConfigMap)
        model: LiteLLM model identifier
        max_concurrency: Maximum concurrent LLM requests
        checkpoint_pvc_path: PVC path for checkpoints (enables resume)
        save_freq: Checkpoint save frequency (samples)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        temperature: LLM temperature (0.0-2.0). Use -1 for flow default
        max_tokens: Maximum response tokens. Use -1 for flow default
        runtime_params: Block-specific parameter overrides
    """
    pass
```

---

### Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Block** | Atomic data transformation unit in SDG Hub |
| **Flow** | YAML-defined pipeline of blocks |
| **KFP** | Kubeflow Pipelines |
| **Artifact** | Data object passed between KFP components |
| **PVC** | Persistent Volume Claim (K8s storage) |
| **LiteLLM** | Library supporting 100+ LLM providers with unified API |

---

### Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-01-16 | SDG Hub Team | Initial draft with Phases 1-6 |
| 0.2 | 2025-01-16 | SDG Hub Team | Added Phase 7: Model/LLM Configuration |
| 0.3 | 2025-01-21 | SDG Hub Team | Added Phase 8: Execution Configuration |
| 0.4 | 2025-01-21 | SDG Hub Team | Added Phase 9: Error Handling & Observability |
| 0.5 | 2025-01-21 | SDG Hub Team | Added Phase 10: Container & Packaging |

</details>
