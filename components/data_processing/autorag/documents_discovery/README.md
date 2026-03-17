# Documents Discovery ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Documents discovery component.

Lists available documents from S3, performs sampling if applied and writes a JSON manifest (documents_descriptor.json) with metadata. Does not download document contents.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `input_data_bucket_name` | `str` | `None` | S3 (or compatible) bucket containing input data. |
| `input_data_path` | `str` | `None` | Path to folder with input documents within the bucket. |
| `test_data` | `dsl.Input[dsl.Artifact]` | `None` | Optional input artifact containing test data for sampling. |
| `sampling_enabled` | `bool` | `True` | Whether to enable sampling or not. |
| `sampling_max_size` | `float` | `1` | Maximum size of sampled documents (in gigabytes). |
| `discovered_documents` | `dsl.Output[dsl.Artifact]` | `None` | Output artifact containing the documents descriptor JSON file. |

## Metadata 🗂️

- **Name**: documents_discovery
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: RHOAI Connections API, Version: >=1.0.0
    - Name: ai4rag, Version: >=1.0.0
- **Tags**:
  - data-processing
  - autorag
  - documents-sampling
- **Last Verified**: 2026-01-23 10:29:35+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - filip-komarzyniec
    - witold-nowogorski
