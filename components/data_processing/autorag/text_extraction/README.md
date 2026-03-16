# Text Extraction ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Text Extraction component.

Reads the documents_descriptor JSON (from documents_discovery), fetches the listed documents from S3, and extracts text using the docling library.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `documents_descriptor` | `dsl.Input[dsl.Artifact]` | `None` | Input artifact containing documents_descriptor.json with bucket, prefix, and documents list. |
| `extracted_text` | `dsl.Output[dsl.Artifact]` | `None` | Output artifact where the extracted text content will be stored. |

## Metadata 🗂️

- **Name**: text_extraction
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: docling, Version: >=1.0.0
- **Tags**:
  - data-processing
  - autorag
  - text-extraction
- **Last Verified**: 2026-01-23 10:29:57+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - filip-komarzyniec
    - witold-nowogorski
