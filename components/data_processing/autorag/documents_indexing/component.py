from typing import Optional

from kfp import dsl


@dsl.component(
    base_image="registry.redhat.io/rhoai/odh-pipeline-runtime-datascience-cpu-py312-rhel9@sha256:f9844dc150592a9f196283b3645dda92bd80dfdb3d467fa8725b10267ea5bdbc",
    packages_to_install=["langchain-text-splitters", "ai4rag@git+https://github.com/IBM/ai4rag.git"],
)
def documents_indexing(
    embedding_model_id: str,
    extracted_text: dsl.Input[dsl.Artifact],
    llama_stack_vector_database_id: str,
    embedding_params: Optional[dict] = None,
    distance_metric: str = "cosine",
    chunking_method: str = "recursive",
    chunk_size: int = 1024,
    chunk_overlap: int = 0,
    batch_size: int = 20,
    collection_name: Optional[str] = None,
):
    """Index extracted text into a vector store with optional batch processing.

    Reads markdown files from extracted_text, chunks them, embeds via Llama Stack,
    and adds them to the vector store. When batch_size > 0, processes documents
    in batches to limit memory use and allow progress on large inputs.

    Args:
        embedding_model_id: Embedding model ID used for the vector store.
        extracted_text: Input artifact (folder) containing .md files from text extraction.
        llama_stack_vector_database_id: Llama Stack provider ID for the vector database.
        embedding_params: Optional embedding parameters.
        distance_metric: Vector distance metric (e.g. "cosine").
        chunking_method: Chunking method.
        chunk_size: Chunk size in characters.
        chunk_overlap: Chunk overlap in characters.
        batch_size: Number of documents per batch; 0 means process all in one batch.
        collection_name: Optional name of the collection to reuse; omit to create a new one.
    """
    import logging
    import os
    import sys
    from pathlib import Path

    from ai4rag.rag.chunking import LangChainChunker
    from ai4rag.rag.embedding.llama_stack import LSEmbeddingModel, LSEmbeddingParams
    from ai4rag.rag.vector_store.llama_stack import LSVectorStore
    from langchain_core.documents import Document
    from llama_stack_client import LlamaStackClient

    logger = logging.getLogger("Document Loader component logger")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)

    if embedding_params is None:
        embedding_params = {}

    params = LSEmbeddingParams(**embedding_params)

    client = LlamaStackClient(
        base_url=os.getenv("LLAMA_STACK_CLIENT_BASE_URL"),
        api_key=os.getenv("LLAMA_STACK_CLIENT_API_KEY"),
    )

    paths = sorted(Path(extracted_text.path).glob("*.md"))
    total_documents = len(paths)
    logger.info("Found %s documents to index", total_documents)

    if total_documents == 0:
        logger.warning("No documents found in %s", extracted_text.path)
        return

    chunker = LangChainChunker(method=chunking_method, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    embedding_model = LSEmbeddingModel(client=client, model_id=embedding_model_id, params=params)

    collection_name_param = {"reuse_collection_name": collection_name if collection_name is not None else {}}
    ls_vectorstore = LSVectorStore(
        embedding_model=embedding_model,
        client=client,
        provider_id=llama_stack_vector_database_id,
        distance_metric=distance_metric,
        **collection_name_param,
    )

    effective_batch_size = batch_size if batch_size > 0 else total_documents
    total_chunks = 0

    for start in range(0, total_documents, effective_batch_size):
        batch_paths = paths[start : start + effective_batch_size]
        batch_documents = [
            Document(
                page_content=p.read_text(encoding="utf-8", errors="replace"),
                metadata={"document_id": p.stem},
            )
            for p in batch_paths
        ]
        batch_chunks = chunker.split_documents(batch_documents)
        ls_vectorstore.add_documents(batch_chunks)
        total_chunks += len(batch_chunks)
        batch_num = start // effective_batch_size + 1
        num_batches = (total_documents + effective_batch_size - 1) // effective_batch_size
        logger.info(
            "Batch %s/%s: indexed %s documents (%s chunks), total chunks so far: %s",
            batch_num,
            num_batches,
            len(batch_documents),
            len(batch_chunks),
            total_chunks,
        )

    logger.info(
        "Documents indexing finished: %s documents, %s chunks",
        total_documents,
        total_chunks,
    )
