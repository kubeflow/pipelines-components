# Test Data Loader ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Download test data json file from S3 into a KFP artifact.

The component reads S3-compatible credentials from environment variables (injected by the pipeline from a Kubernetes secret) and downloads a JSON test data file from the provided bucket and path to the output artifact.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `test_data_bucket_name` | `str` | `None` | S3 (or compatible) bucket that contains the test data file. |
| `test_data_path` | `str` | `None` | S3 object key to the JSON test data file. |
| `test_data` | `dsl.Output[dsl.Artifact]` | `None` | Output artifact that receives the downloaded file. |

## Metadata 🗂️

- **Name**: test_data_loader
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: pandas, Version: >=2.0.0
- **Tags**:
  - data-processing
  - autorag
  - test-data
- **Last Verified**: 2026-01-23 10:29:45+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - filip-komarzyniec
    - witold-nowogorski
