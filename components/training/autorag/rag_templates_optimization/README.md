# Rag Templates Optimization ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

RAG Templates Optimization component.

Carries out the iterative RAG optimization process.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `extracted_text` | `dsl.InputPath(dsl.Artifact)` | `None` | A path pointing to a folder containg extracted texts from input documents. |
| `test_data` | `dsl.InputPath(dsl.Artifact)` | `None` | A path pointing to test data used for evaluating RAG pattern quality. |
| `search_space_prep_report` | `dsl.InputPath(dsl.Artifact)` | `None` | A path pointing to a .yml file containig short report on the experiment's first phase (search space preparation). |
| `rag_patterns` | `dsl.Output[dsl.Artifact]` | `None` | kfp-enforced argument specifying an output artifact. Provided by kfp backend automatically. |
| `autorag_run_artifact` | `dsl.Output[dsl.Artifact]` | `None` | kfp-enforced argument specifying an output artifact. Provided by kfp backend atomatically. |
| `embedded_artifact` | `dsl.EmbeddedInput[dsl.Dataset]` | `None` | kfp-enforced argument to allow access of base64 encoded dir with notebook templates. |
| `chat_model_url` | `Optional[str]` | `None` | Inference endpoint URL for the chat/generation model (OpenAI-compatible). Required for in-memory scenario. |
| `chat_model_token` | `Optional[str]` | `None` | Optional API token for the chat model endpoint. Omit if deployment has no auth. |
| `embedding_model_url` | `Optional[str]` | `None` | Inference endpoint URL for the embedding model. Required for in-memory scenario. |
| `embedding_model_token` | `Optional[str]` | `None` | Optional API token for the embedding model endpoint. Omit if no auth. |
| `llama_stack_vector_database_id` | `Optional[str]` | `None` | Vector database identifier as registered in llama-stack. |
| `optimization_settings` | `Optional[dict]` | `None` | Additional settings customising the experiment. |
| `input_data_key` | `Optional[str]` | `None` | A path to documents dir within a bucket used as an input to AI4RAG experiment. |
| `test_data_key` | `Optional[str]` | `None` | A path to test data file within a bucket used as an input to AI4RAG experiment. |

## Metadata 🗂️

- **Name**: rag_templates_optimization
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: ai4rag, Version: >=1.0.0
    - Name: llama-stack API, Version: >=1.0.0
    - Name: Milvus, Version: >=2.0.0
    - Name: Milvus Lite, Version: >=2.0.0
- **Tags**:
  - training
  - autorag
  - optimization
  - rag-patterns
- **Last Verified**: 2026-01-23 14:23:12+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
  - Reviewers:
    - filip-komarzyniec
    - witold-nowogorski
