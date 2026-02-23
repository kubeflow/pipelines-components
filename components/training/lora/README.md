# LoRA Training Component

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview

Train model using LoRA (Low-Rank Adaptation) via TrainingHub. This component is purpose-built for LoRA training and uses the unsloth backend. For SFT training, use the `components.training.sft` component instead. For OSFT training, use the `components.training.osft` component instead.

## Description

This component provides a streamlined interface for LoRA training with:

- Hardcoded unsloth backend (no configuration needed)
- LoRA-specific parameters only
- QLoRA support (4-bit and 8-bit quantization)
- Automatic dataset resolution from HuggingFace, S3, or PVC
- Kubernetes-native execution via TrainingHub
- Metrics logging and loss visualization
- Model artifact export to PVC and KFP artifacts

## Installation & Usage

This component uses shared utilities from the parent `kfp-components` package. The component automatically installs the package at runtime via:

```python
packages_to_install=[
    "kfp-components@git+https://github.com/red-hat-data-services/pipelines-components.git@main"
]
```

**Note:** When the package is published to PyPI, this will change to a standard PyPI installation.

### Example Usage

```python
from kfp import dsl
from components.training.lora import train_model

@dsl.pipeline(name="my-lora-pipeline")
def my_pipeline():
    training_task = train_model(
        pvc_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
        training_base_model="Qwen/Qwen2.5-1.5B-Instruct",
        training_num_epochs=3,
        training_effective_batch_size=128,
        training_max_seq_len=8192,
        training_lora_r=16,
        training_lora_alpha=32,
    )
```

## Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pvc_path` | `str` | Required | Workspace PVC root path (use dsl.WORKSPACE_PATH_PLACEHOLDER). |
| `output_model` | `dsl.Output[dsl.Model]` | Required | Output model artifact. |
| `output_metrics` | `dsl.Output[dsl.Metrics]` | Required | Output training metrics artifact. |
| `output_loss_chart` | `dsl.Output[dsl.HTML]` | Required | Output HTML artifact with training loss chart. |
| `dataset` | `dsl.Input[dsl.Dataset]` | `None` | Input training dataset artifact. |
| `training_base_model` | `str` | `Qwen/Qwen2.5-1.5B-Instruct` | Base model (HuggingFace ID or local path). |
| `training_effective_batch_size` | `int` | `128` | Effective batch size per optimizer step. |
| `training_max_tokens_per_gpu` | `int` | `32000` | Max tokens per GPU (memory cap). |
| `training_max_seq_len` | `int` | `8192` | Max sequence length in tokens. |
| `training_learning_rate` | `Optional[float]` | `None` | Learning rate (default: 2e-4). |
| `training_lr_warmup_steps` | `Optional[int]` | `None` | Learning rate warmup steps (default: 10). |
| `training_checkpoint_at_epoch` | `Optional[bool]` | `None` | Save checkpoint at each epoch. |
| `training_num_epochs` | `Optional[int]` | `None` | Number of training epochs (default: 3). |
| `training_data_output_dir` | `Optional[str]` | `None` | Directory for processed training data. |
| `training_envs` | `str` | `""` | Environment overrides as KEY=VAL,KEY=VAL. |
| `training_resource_cpu_per_worker` | `str` | `"4"` | CPU cores per worker. |
| `training_resource_gpu_per_worker` | `int` | `1` | GPUs per worker. |
| `training_resource_memory_per_worker` | `str` | `"32Gi"` | Memory per worker (e.g., 32Gi). |
| `training_resource_num_procs_per_worker` | `str` | `"auto"` | Processes per worker (auto or int). |
| `training_resource_num_workers` | `int` | `1` | Number of training pods. |
| `training_metadata_labels` | `str` | `""` | Pod labels as key=value,key=value. |
| `training_metadata_annotations` | `str` | `""` | Pod annotations as key=value,key=value. |
| `training_lora_r` | `int` | `16` | LoRA rank (controls model capacity). |
| `training_lora_alpha` | `int` | `32` | LoRA scaling factor. |
| `training_lora_dropout` | `float` | `0.0` | Dropout rate for LoRA layers. |
| `training_lora_target_modules` | `str` | `""` | Comma-separated list of modules to apply LoRA (empty = auto-detect). |
| `training_lora_use_rslora` | `Optional[bool]` | `None` | Use Rank-Stabilized LoRA variant. |
| `training_lora_use_dora` | `Optional[bool]` | `None` | Use Weight-Decomposed LoRA (DoRA). |
| `training_lora_load_in_4bit` | `Optional[bool]` | `None` | Enable 4-bit quantization (QLoRA). |
| `training_lora_load_in_8bit` | `Optional[bool]` | `None` | Enable 8-bit quantization. |
| `training_lora_bnb_4bit_quant_type` | `Optional[str]` | `None` | Quantization type (e.g., "nf4"). |
| `training_lora_bnb_4bit_compute_dtype` | `Optional[str]` | `None` | Compute dtype (e.g., "bfloat16"). |
| `training_lora_bnb_4bit_use_double_quant` | `Optional[bool]` | `None` | Enable double quantization. |
| `training_lora_sample_packing` | `Optional[bool]` | `None` | Pack multiple samples for efficiency. |
| `training_seed` | `Optional[int]` | `None` | Random seed for reproducibility. |
| `training_use_liger` | `Optional[bool]` | `None` | Enable Liger kernel optimizations. |
| `training_lr_scheduler` | `Optional[str]` | `None` | LR scheduler type (cosine, linear, etc.). |
| `training_fsdp_sharding_strategy` | `Optional[str]` | `None` | FSDP sharding strategy (FULL_SHARD, HYBRID_SHARD, NO_SHARD). |
| `kubernetes_config` | `dsl.TaskConfig` | `None` | KFP TaskConfig for volumes/env/resources passthrough. |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| Output | `str` | Status message ("training completed"). |

## Environment Variables

- `HF_TOKEN`: HuggingFace token for gated models (read from environment)
- `OCI_PULL_SECRET_MODEL_DOWNLOAD`: Docker config.json content for pulling OCI model images
- `KUBERNETES_SERVER_URL`: Kubernetes API server URL for remote training
- `KUBERNETES_AUTH_TOKEN`: Kubernetes authentication token for remote training

## Metadata

- **Name**: lora
- **Stability**: alpha
- **Backend**: unsloth (hardcoded)
- **Algorithm**: LoRA (hardcoded)
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
    - Name: Trainer, Version: >=0.1.0
  - External Services:
    - Name: HuggingFace Datasets, Version: >=2.14.0
    - Name: Kubernetes, Version: >=1.28.0
    - Name: Unsloth, Version: >=2024.11
- **Tags**:
  - training
  - fine_tuning
  - lora
  - peft
  - llm
  - parameter_efficient
- **Last Verified**: 2026-02-23
- **Owners**:
  - Approvers:
    - briangallagher
    - Fiona-Waters
    - kramaranya
    - MStokluska
    - szaher

## Additional Resources

- **Documentation**: [https://github.com/kubeflow/trainer](https://github.com/kubeflow/trainer)
