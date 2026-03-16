# Documents Rag Optimization Pipeline ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Automated system for building and optimizing Retrieval-Augmented Generation (RAG) applications.

The Documents Lite RAG Optimization Pipeline is an automated system for building and optimizing Retrieval-Augmented Generation (RAG) applications within Red Hat OpenShift AI. It leverages Kubeflow Pipelines to orchestrate the optimization workflow, using the ai4rag optimization engine to
systematically explore RAG configurations and identify the best performing parameter settings based on an upfront-specified quality metric.

The system integrates with OpenAI API for inference and in-memory ChromaDB vector database operations, producing optimized RAG patterns as artifacts that can be deployed and used for production RAG applications.

## Inputs 📥

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `test_data_secret_name` | `str` | `None` | Name of the Kubernetes secret holding S3-compatible credentials for test data access. The following environment variables are required: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, AWS_DEFAULT_REGION. |
| `test_data_bucket_name` | `str` | `None` | S3 (or compatible) bucket name for the test data file. |
| `test_data_key` | `str` | `None` | Object key (path) of the test data JSON file in the test data bucket. |
| `input_data_secret_name` | `str` | `None` | Name of the Kubernetes secret holding S3-compatible credentials for input document data access. The following environment variables are required: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, AWS_DEFAULT_REGION. |
| `input_data_bucket_name` | `str` | `None` | S3 (or compatible) bucket name for the input documents. |
| `input_data_key` | `str` | `None` | Object key (path) of the input documents in the input data bucket. |
| `chat_model_url` | `str` | `None` | Inference endpoint URL for the chat/generation model (OpenAI-compatible endpoint). |
| `chat_model_token` | `str` | `None` | API token or key for authenticating with the chat model endpoint. |
| `embedding_model_url` | `str` | `None` | Inference endpoint URL for the embedding model. |
| `embedding_model_token` | `str` | `None` | API token or key for authenticating with the embedding model endpoint. |
| `optimization_metric` | `str` | `faithfulness` | Quality metric used to optimize RAG patterns. Supported values: "faithfulness", "answer_correctness", "context_correctness". Defaults to "faithfulness". |
| `optimization_max_rag_patterns` | `int` | `8` | Maximum number of RAG patterns to generate. Passed to ai4rag (max_number_of_rag_patterns). Defaults to 8. |

## Usage Examples 🧪

```python
"""Example usage of the documents_lite_rag_optimization_pipeline."""

from kfp_components.pipelines.training.autorag.documents_lite_rag_optimization_pipeline import (
    documents_lite_rag_optimization_pipeline,
)


def example_minimal_usage():
    """Minimal example with only required parameters."""
    return documents_lite_rag_optimization_pipeline(
        test_data_secret_name="s3-test-data-secret",
        test_data_bucket_name="autorag-benchmarks",
        test_data_key="test_data.json",
        input_data_secret_name="s3-input-secret",
        input_data_bucket_name="my-documents-bucket",
        input_data_key="rh_documents/",
        chat_model_url="https://api.openai.com/v1",
        chat_model_token="your-chat-model-token",
        embedding_model_url="https://api.openai.com/v1",
        embedding_model_token="your-embedding-model-token",
    )


def example_full_usage():
    """Full example with optional parameters."""
    return documents_lite_rag_optimization_pipeline(
        test_data_secret_name="s3-test-data-secret",
        test_data_bucket_name="autorag-benchmarks",
        test_data_key="my-folder/test_data.json",
        input_data_secret_name="s3-input-secret",
        input_data_bucket_name="my-documents-bucket",
        input_data_key="rh_documents/",
        chat_model_url="https://api.openai.com/v1",
        chat_model_token="your-chat-model-token",
        embedding_model_url="https://api.openai.com/v1",
        embedding_model_token="your-embedding-model-token",
        optimization_metric="answer_correctness",
    )

```

## Metadata 🗂️

- **Name**: documents_rag_optimization_pipeline
- **Stability**: alpha
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: ai4rag, Version: >=1.0.0
    - Name: llama-stack API, Version: >=1.0.0
    - Name: RHOAI Connections API, Version: >=1.0.0
    - Name: Milvus, Version: >=2.0.0
    - Name: Milvus Lite, Version: >=2.0.0
    - Name: MLFlow, Version: >=2.0.0
    - Name: docling, Version: >=1.0.0
- **Tags**:
  - training
  - pipeline
  - autorag
  - rag-optimization
- **Last Verified**: 2026-01-23 14:57:32+00:00
- **Owners**:
  - Approvers:
    - LukaszCmielowski
    - filip-komarzyniec
    - witold-nowogorski
  - Reviewers:
    - LukaszCmielowski

<!-- custom-content -->

## Optimization Engine: ai4rag 🚀

The pipeline uses [ai4rag](https://github.com/IBM/ai4rag), a RAG Templates Optimization Engine that
provides an automated approach to optimizing Retrieval-Augmented Generation (RAG) systems. The
engine is designed to be LLM and Vector Database provider agnostic, making it flexible and
adaptable to various RAG implementations.

ai4rag accepts a variety of RAG templates and search space definitions, then systematically
explores different parameter configurations to find optimal settings. The engine returns initialized
RAG templates with optimal parameter values, which are referred to as RAG Patterns.

## Supported Features ✨

**Status**: Tech Preview - MVP (May 2026)

### RAG Configuration

- **RAG Type**: Documents (documents provided as input)
- **Supported Languages**: English
- **Supported Document Types**: PDF, DOCX, PPTX, Markdown, HTML, Plain text
- **Document Data Sources**: S3 (Amazon S3), Local filesystem (FS)

### Infrastructure Components

- **Vector store**: ChromaDB (in-memory), used during optimization
- **Chat and embedding**: OpenAI-compatible API; endpoints and tokens provided via pipeline
  parameters (`chat_model_url`, `chat_model_token`, `embedding_model_url`, `embedding_model_token`)

### Processing Methods

- **Chunking Method**: Recursive
- **Retrieval Methods**: Simple, Simple with hybrid ranker

### Interfaces

- **API**: Programmatic access to AutoRAG functionality
- **UI**: User interface for interacting with AutoRAG

## Glossary 📚

### RAG Configuration Definition

A **RAG Configuration** is a specific set of parameter values that define how a
Retrieval-Augmented Generation system operates. It includes settings for:

- **Chunking**: Method and parameters for splitting documents (e.g., recursive method with
  chunk_size=2048, chunk_overlap=256)
- **Embeddings**: The embedding model used (e.g., `intfloat/multilingual-e5-large`)
- **Generation**: The language model used (e.g., `ibm/granite-13b-instruct-v2`) along with its
  parameters
- **Retrieval**: The method for retrieving relevant document chunks (e.g., simple retrieval or
  hybrid ranker)

### RAG Pattern

A **RAG Pattern** is an optimized RAG configuration that has been evaluated and ranked by
AutoRAG. It represents a complete, deployable RAG system with:

- Validated parameter settings that have been tested and evaluated
- Performance metrics (e.g., answer_correctness, faithfulness, context_correctness)
- Executable notebooks for indexing and inference operations
- A position in the leaderboard based on performance

### RAG Template

A **RAG Template** is a reusable blueprint that defines the structure and workflow of a RAG
system. Templates are parameterized and AutoRAG uses templates as the foundation, optimizing the
parameter values to create RAG Patterns.

## Additional Resources 📚

- **ai4rag Documentation**: [ai4rag GitHub](https://github.com/IBM/ai4rag)
- **Issue Tracker**: [GitHub Issues](https://github.com/kubeflow/pipelines-components/issues)
