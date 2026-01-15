# Dataset Download ✨

> ⚠️ **Stability: experimental** — This asset is not yet stable and may change.

## Overview 🧾

Download and prepare datasets from multiple sources.

Validates that datasets follow chat template format (messages/conversations with role/content).

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `train_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output artifact for training dataset (JSONL format) |
| `eval_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output artifact for evaluation dataset (JSONL format) |
| `dataset_uri` | `str` | `None` | Dataset URI (hf://, s3://, https://, pvc:// or absolute path) |
| `pvc_mount_path` | `str` | `None` | Path where the shared PVC is mounted |
| `train_split_ratio` | `float` | `0.9` | Ratio for train split (e.g., 0.9 for 90/10) |
| `subset_count` | `int` | `0` | Number of examples to use (0 = use all) |
| `hf_token` | `str` | `` | HuggingFace token for gated/private datasets |
| `shared_log_file` | `str` | `pipeline_log.txt` | Name of the shared log file |

## Metadata 🗂️

- **Name**: dataset_download
- **Stability**: experimental
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: HuggingFace Datasets, Version: >=2.14.0
    - Name: AWS S3, Version: >=1.0.0
- **Tags**:
  - data_processing
  - dataset
  - download
  - huggingface
  - s3
- **Last Verified**: 2026-01-14 00:00:00+00:00
- **Owners**:
  - Approvers:
    - briangallagher
    - Fiona-Waters
    - kramaranya
    - MStokluska
    - szaher

## Additional Resources 📚

- **Documentation**: [https://github.com/kubeflow/pipelines-components](https://github.com/kubeflow/pipelines-components)
