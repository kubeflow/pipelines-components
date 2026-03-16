# Autorag Documents Indexing ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Defines a pipeline to load, sample, extract text, and index documents for AutoRAG.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `input_data_secret_name` | `str` | `None` | Name of the secret with S3 credentials for input data ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT", "AWS_DEFAULT_REGION"). |
| `input_data_bucket_name` | `str` | `None` | Name of the S3 bucket containing input data. |
| `input_data_key` | `str` | `None` | Path to folder with input documents within bucket. |
| `llama_stack_secret_name` | `str` | `None` | Name of the secret with LLAMA stack credentials ("LLAMA_STACK_CLIENT_BASE_URL", "LLAMA_STACK_CLIENT_API_KEY"). |
| `embedding_model_id` | `str` | `None` | Embedding model ID for the vector store. |
| `llama_stack_vector_database_id` | `str` | `None` | Optional Llama Stack provider ID. |
| `collection_name` | `str` | `None` | Optional name of the collection to reuse; omit to create a new one. |
| `embedding_params` | `Optional[dict]` | `None` | Dict passed to LSEmbeddingParams (default: {}). |
| `distance_metric` | `str` | `cosine` | Vector distance metric (e.g. "cosine"). |
| `chunking_method` | `str` | `recursive` | Chunking method (e.g. "recursive"). |
| `chunk_size` | `int` | `1024` | Chunk size in characters. |
| `chunk_overlap` | `int` | `0` | Chunk overlap in characters. |
| `batch_size` | `int` | `20` | Number of documents per batch (0 = process all at once). |

## Metadata 🗂️

- **Name**: autorag-documents-indexing
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: docling, Version: >=2.72.0
    - Name: boto3, Version: >=1.42.34
    - Name: ai4rag, Version: >=1.0.0
    - Name: RHOAI Connections API, Version: >=1.0.0
- **Tags**:
  - data_processing
  - text_extraction
  - documents_discovery
  - data_indexing
  - autorag
- **Last Verified**: 2026-03-05 00:00:00+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - LukaszCmielowski
