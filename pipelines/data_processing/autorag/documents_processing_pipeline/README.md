# Autorag ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Defines a pipeline to load and sample input data for AutoRAG.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `test_data_secret_name` | `str` | `None` | Name of the secret containing environment variables with S3 credentials used to access the test data. |
| `input_data_secret_name` | `str` | `None` | Name of the secret containing environment variables with S3 credentials used to access the input data. |
| `input_data_bucket_name` | `str` | `None` | Name of the S3 bucket containing input data. |
| `input_data_key` | `str` | `None` | Path to folder with input documents within bucket. |
| `sampling_enabled` | `bool` | `False` | Whether to enable sampling or not. |
| `sampling_max_size` | `Optional[float]` | `None` | Maximum size of sampled documents (in gigabytes). |
| `test_data_bucket_name` | `Optional[str]` | `None` | S3 bucket that contains the test data file. |
| `test_data_key` | `Optional[str]` | `None` | S3 object key to the JSON test data file. |

## Metadata 🗂️

- **Name**: autorag
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: docling, Version: >=2.72.0
    - Name: boto3, Version: >=1.42.34
- **Tags**:
  - data_processing
  - text_extraction
  - documents_discovery
- **Last Verified**: 2026-02-04 11:46:16+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - LukaszCmielowski

<!-- custom-content -->

## Pipeline Workflow 🔄

The data processing pipeline runs three stages:

1. **Test Data Loading**: Loads the test data JSON file from S3 into a KFP artifact (used for evaluation and for document sampling).
2. **Document Sampling**: Lists documents in the input S3 bucket/prefix, applies sampling (e.g. test-data–driven with optional size limit), and writes a YAML descriptor of the sampled set. Does not download document contents.
3. **Text Extraction**: Reads the descriptor, fetches the listed documents from S3, and extracts text using docling. Outputs markdown files suitable for downstream chunking and embedding.

## Required Parameters ✅

The following parameters are required to run the pipeline:

- `test_data_secret_name` - Kubernetes secret for S3 credentials (test data)
- `input_data_secret_name` - Kubernetes secret for S3 credentials (input documents)
- `test_data_bucket_name` - Bucket containing the test data JSON file
- `test_data_key` - Object key to the test data JSON file
- `input_data_bucket_name` - Bucket containing the input documents
- `input_data_key` - Path to folder with input documents in the bucket
- `sampling_config` - Sampling configuration dict (use `{}` for defaults)

## Components Used 🔧

This pipeline orchestrates the following AutoRAG components:

1. **[Test Data Loader](../../components/data_processing/autorag/test_data_loader/README.md)** -
   Loads test data from a JSON file in S3

2. **[Documents sampling](../../components/data_processing/autorag/documents_sampling/README.md)** -
   Lists documents from S3 and performs sampling; produces a YAML descriptor

3. **[Text Extraction](../../components/data_processing/autorag/text_extraction/README.md)** -
   Fetches documents from S3 and extracts text using docling

## Artifacts 📦

For each pipeline run, the pipeline produces:

- **Test Data Artifact**: JSON file containing the benchmark/test data (e.g. questions and correct answer document IDs).
- **Sampled Documents Artifact**: YAML manifest (`sampled_documents_descriptor.yaml`) with bucket, prefix, and list of sampled document keys for downstream components.
- **Extracted Text Artifact**: Folder of markdown files (one per document) with extracted text, ready for chunking and embedding in RAG optimization pipelines.
