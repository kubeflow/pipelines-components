# Download Model From Hf ✨

## Overview 🧾

Downloads a model from HuggingFace Hub to a local directory

(use mounted PVC path with sufficient storage for larger models).

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_identifier` | `str` | `None` | HuggingFace model identifier (e.g., "Qwen/Qwen3-VL-2B-Instruct") |
| `local_model_dir` | `str` | `/models` | Local directory to save the model files to (default: "/models") |
| `if_exists` | `str` | `skip` | Behavior if files already exist in local_model_dir. Options: ["skip" (default), "overwrite", "error"] |

## Metadata 🗂️

- **Name**: download_model_from_hf
- **Tier**: core
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.5
  - External Services: None
- **Tags**:
  - deployment
- **Last Verified**: 2025-01-08 00:00:00+00:00
- **Owners**:
  - Approvers:
    - dandawg
  - Reviewers:
    - dandawg

## Additional Resources 📚

- **Documentation**: [https://huggingface.co/docs/huggingface_hub/guides/download](https://huggingface.co/docs/huggingface_hub/guides/download)
- **Issue Tracker**: [https://github.com/kubeflow/pipelines-components/issues](https://github.com/kubeflow/pipelines-components/issues)
