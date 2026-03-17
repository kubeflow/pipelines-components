# Documents Indexing ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Index extracted text into a vector store with optional batch processing.

Reads markdown files from extracted_text, chunks them, embeds via Llama Stack, and adds them to the vector store. When batch_size > 0, processes documents in batches to limit memory use and allow progress on large inputs.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `embedding_model_id` | `str` | `None` | Embedding model ID used for the vector store. |
| `extracted_text` | `dsl.Input[dsl.Artifact]` | `None` | Input artifact (folder) containing .md files from text extraction. |
| `llama_stack_vector_database_id` | `str` | `None` | Llama Stack provider ID for the vector database. |
| `embedding_params` | `Optional[dict]` | `None` | Optional embedding parameters. |
| `distance_metric` | `str` | `cosine` | Vector distance metric (e.g. "cosine"). |
| `chunking_method` | `str` | `recursive` | Chunking method. |
| `chunk_size` | `int` | `1024` | Chunk size in characters. |
| `chunk_overlap` | `int` | `0` | Chunk overlap in characters. |
| `batch_size` | `int` | `20` | Number of documents per batch; 0 means process all in one batch. |
| `collection_name` | `Optional[str]` | `None` | Optional name of the collection to reuse; omit to create a new one. |

## Metadata 🗂️

- **Name**: documents_indexing
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: RHOAI Connections API, Version: >=1.0.0
    - Name: ai4rag, Version: >=1.0.0
- **Tags**:
  - data-indexing
  - autorag
- **Last Verified**: 2026-01-23 10:29:35+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - filip-komarzyniec
    - witold-nowogorski
