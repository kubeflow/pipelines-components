"""Tests for the documents_indexing component."""

import ssl
import sys
import types
from unittest import mock

import pytest

from ..component import documents_indexing


def _make_httpx_module():
    """Return a minimal fake httpx module with a trackable Client class."""
    mod = types.ModuleType("httpx")

    class ConnectError(Exception):
        pass

    class Client:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    mod.ConnectError = ConnectError
    mod.Client = Client
    return mod


def _make_llama_stack_client_module():
    """Stub llama_stack_client with a real APIConnectionError (MagicMock breaks except clauses)."""
    mod = types.ModuleType("llama_stack_client")

    class APIConnectionError(Exception):
        """Stand-in for llama_stack_client.APIConnectionError."""

    mod.APIConnectionError = APIConnectionError
    mod.LlamaStackClient = mock.MagicMock()
    return mod


def _make_all_mocks():
    """Build sys.modules patch dict for all heavy dependencies."""
    mocks = {}
    for name in [
        "ai4rag",
        "ai4rag.rag",
        "ai4rag.rag.chunking",
        "ai4rag.rag.embedding",
        "ai4rag.rag.embedding.llama_stack",
        "ai4rag.rag.vector_store",
        "ai4rag.rag.vector_store.llama_stack",
        "langchain_core",
        "langchain_core.documents",
        "langchain_text_splitters",
    ]:
        mocks[name] = mock.MagicMock()

    mocks["httpx"] = _make_httpx_module()
    mocks["llama_stack_client"] = _make_llama_stack_client_module()
    return mocks


def _patch_indexing_dependencies():
    """Return modules dict to mock ai4rag/langchain/llama-stack imports."""
    mock_chunker_cls = mock.MagicMock()
    mock_chunker = mock.MagicMock()
    mock_chunker.split_documents.return_value = ["chunk-1", "chunk-2"]
    mock_chunker_cls.return_value = mock_chunker

    mock_ls_embedding_params = mock.MagicMock()
    mock_ls_embedding_model = mock.MagicMock()
    mock_ls_vector_store = mock.MagicMock()
    mock_ls_vector_store.add_documents = mock.MagicMock()
    mock_llama_client = mock.MagicMock()
    mock_document = mock.MagicMock(side_effect=lambda **kwargs: kwargs)

    mods = {
        "ai4rag": mock.MagicMock(),
        "ai4rag.rag": mock.MagicMock(),
        "ai4rag.rag.chunking": mock.MagicMock(LangChainChunker=mock_chunker_cls),
        "ai4rag.rag.embedding": mock.MagicMock(),
        "ai4rag.rag.embedding.llama_stack": mock.MagicMock(
            LSEmbeddingModel=mock_ls_embedding_model,
            LSEmbeddingParams=mock_ls_embedding_params,
        ),
        "ai4rag.rag.vector_store": mock.MagicMock(),
        "ai4rag.rag.vector_store.llama_stack": mock.MagicMock(
            LSVectorStore=mock.MagicMock(return_value=mock_ls_vector_store),
        ),
        "langchain_core": mock.MagicMock(),
        "langchain_core.documents": mock.MagicMock(Document=mock_document),
        "httpx": _make_httpx_module(),
        "llama_stack_client": _make_llama_stack_client_module(),
    }
    mods["llama_stack_client"].LlamaStackClient.return_value = mock_llama_client
    return mods, mock_ls_vector_store


class TestDocumentsIndexingUnitTests:
    """Unit tests for component logic."""

    def test_component_function_exists(self):
        """Test that the component function is properly imported."""
        assert callable(documents_indexing)
        assert hasattr(documents_indexing, "python_func")

    def test_component_has_expected_interface(self):
        """Test component has expected interface (required args)."""
        import inspect

        sig = inspect.signature(documents_indexing.python_func)
        params = list(sig.parameters)
        assert "embedding_model_id" in params
        assert "extracted_text" in params
        assert "llama_stack_vector_database_id" in params

    def test_invalid_vector_store_type_raises_value_error(self, tmp_path):
        """Unsupported llama_stack_vector_database_id raises ValueError."""
        mods, _ = _patch_indexing_dependencies()
        extracted = mock.MagicMock(path=str(tmp_path))
        with mock.patch.dict(sys.modules, mods):
            with pytest.raises(ValueError, match="is not supported"):
                documents_indexing.python_func(
                    embedding_model_id="embed-model",
                    extracted_text=extracted,
                    llama_stack_vector_database_id="unsupported",
                )

    def test_empty_embedding_model_id_raises_value_error(self, tmp_path):
        """Empty embedding_model_id is rejected."""
        mods, _ = _patch_indexing_dependencies()
        extracted = mock.MagicMock(path=str(tmp_path))
        with mock.patch.dict(sys.modules, mods):
            with pytest.raises(ValueError, match="embedding_model_id must be a non-empty string"):
                documents_indexing.python_func(
                    embedding_model_id="",
                    extracted_text=extracted,
                    llama_stack_vector_database_id="ls_milvus",
                )

    def test_invalid_chunk_size_type_raises_type_error(self, tmp_path):
        """Non-int chunk_size is rejected."""
        mods, _ = _patch_indexing_dependencies()
        extracted = mock.MagicMock(path=str(tmp_path))
        with mock.patch.dict(sys.modules, mods):
            with pytest.raises(TypeError, match="chunk_size must be an integer"):
                documents_indexing.python_func(
                    embedding_model_id="embed-model",
                    extracted_text=extracted,
                    llama_stack_vector_database_id="ls_milvus",
                    chunk_size="1024",
                )


class TestSSLFallbackDocumentsIndexing:
    """Tests for SSL retry logic in _create_llama_stack_client."""

    @mock.patch.dict(
        "os.environ",
        {
            "LLAMA_STACK_CLIENT_BASE_URL": "https://llama-stack.example.com",
            "LLAMA_STACK_CLIENT_API_KEY": "test-api-key",
        },
    )
    def test_llama_stack_client_ssl_retry_with_verify_false(self, tmp_path):
        """SSL error on models.list() retries LlamaStackClient with verify=False."""
        mocks = _make_all_mocks()

        mock_ls_client_fail = mock.MagicMock()
        mock_ls_client_fail.models.list.side_effect = ssl.SSLCertVerificationError(
            "CERTIFICATE_VERIFY_FAILED: self-signed certificate"
        )
        mock_ls_client_ok = mock.MagicMock()
        mock_ls_client_ok.models.list.return_value = []

        ls_call_count = 0
        ls_kwargs_history = []

        def fake_ls_client(**kwargs):
            nonlocal ls_call_count
            ls_call_count += 1
            ls_kwargs_history.append(kwargs)
            if ls_call_count == 1:
                return mock_ls_client_fail
            return mock_ls_client_ok

        mocks["llama_stack_client"].LlamaStackClient.side_effect = fake_ls_client

        # Provide an empty directory — component returns early when no .md files found
        extracted_text_dir = tmp_path / "extracted"
        extracted_text_dir.mkdir()
        extracted_text = mock.MagicMock()
        extracted_text.path = str(extracted_text_dir)

        with mock.patch.dict(sys.modules, mocks):
            documents_indexing.python_func(
                embedding_model_id="granite-embedding",
                extracted_text=extracted_text,
                llama_stack_vector_database_id="ls_milvus",
            )

        assert ls_call_count == 2, "LlamaStackClient should be instantiated twice (initial + SSL retry)"
        assert ls_kwargs_history[0].get("http_client") is None, "First call should not disable SSL"
        assert isinstance(ls_kwargs_history[1].get("http_client"), mocks["httpx"].Client), (
            "Retry call should pass httpx.Client"
        )
        assert ls_kwargs_history[1]["http_client"].kwargs.get("verify") is False

    @mock.patch.dict(
        "os.environ",
        {
            "LLAMA_STACK_CLIENT_BASE_URL": "https://llama-stack.example.com",
            "LLAMA_STACK_CLIENT_API_KEY": "test-api-key",
        },
    )
    def test_llama_stack_client_api_connection_error_wrapping_ssl_retries(self, tmp_path):
        """LSAPIConnectionError wrapping an SSL cause triggers the verify=False retry (production case)."""
        mocks = _make_all_mocks()

        LSAPIConnectionError = mocks["llama_stack_client"].APIConnectionError
        ssl_err = ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED: self-signed certificate")
        api_err = LSAPIConnectionError("Connection error.")
        api_err.__cause__ = ssl_err

        mock_ls_client_fail = mock.MagicMock()
        mock_ls_client_fail.models.list.side_effect = api_err
        mock_ls_client_ok = mock.MagicMock()
        mock_ls_client_ok.models.list.return_value = []

        ls_call_count = 0
        ls_kwargs_history = []

        def fake_ls_client(**kwargs):
            nonlocal ls_call_count
            ls_call_count += 1
            ls_kwargs_history.append(kwargs)
            if ls_call_count == 1:
                return mock_ls_client_fail
            return mock_ls_client_ok

        mocks["llama_stack_client"].LlamaStackClient.side_effect = fake_ls_client

        extracted_text_dir = tmp_path / "extracted"
        extracted_text_dir.mkdir()
        extracted_text = mock.MagicMock()
        extracted_text.path = str(extracted_text_dir)

        with mock.patch.dict(sys.modules, mocks):
            documents_indexing.python_func(
                embedding_model_id="granite-embedding",
                extracted_text=extracted_text,
                llama_stack_vector_database_id="ls_milvus",
            )

        assert ls_call_count == 2, "LlamaStackClient should be instantiated twice (initial + SSL retry)"
        assert ls_kwargs_history[0].get("http_client") is None
        assert isinstance(ls_kwargs_history[1].get("http_client"), mocks["httpx"].Client)
        assert ls_kwargs_history[1]["http_client"].kwargs.get("verify") is False

    @mock.patch.dict(
        "os.environ",
        {
            "LLAMA_STACK_CLIENT_BASE_URL": "https://llama-stack.example.com",
            "LLAMA_STACK_CLIENT_API_KEY": "test-api-key",
        },
    )
    def test_llama_stack_client_non_ssl_error_is_reraised(self, tmp_path):
        """Non-SSL error from models.list() propagates without retry."""
        mocks = _make_all_mocks()

        mock_ls_client = mock.MagicMock()
        mock_ls_client.models.list.side_effect = ConnectionRefusedError("Connection refused")
        mocks["llama_stack_client"].LlamaStackClient.return_value = mock_ls_client

        extracted_text = mock.MagicMock()
        extracted_text.path = str(tmp_path)

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(ConnectionRefusedError):
                documents_indexing.python_func(
                    embedding_model_id="granite-embedding",
                    extracted_text=extracted_text,
                    llama_stack_vector_database_id="ls_milvus",
                )

    @mock.patch.dict(
        "os.environ",
        {
            "LLAMA_STACK_CLIENT_BASE_URL": "https://llama-stack.example.com",
            "LLAMA_STACK_CLIENT_API_KEY": "test-api-key",
        },
    )
    def test_llama_stack_client_api_connection_error_non_ssl_cause_is_reraised(self, tmp_path):
        """LSAPIConnectionError whose cause is NOT SSL propagates without retry."""
        mocks = _make_all_mocks()

        LSAPIConnectionError = mocks["llama_stack_client"].APIConnectionError
        err = LSAPIConnectionError("Connection timeout")
        err.__cause__ = TimeoutError("timed out")

        mock_ls_client = mock.MagicMock()
        mock_ls_client.models.list.side_effect = err
        mocks["llama_stack_client"].LlamaStackClient.return_value = mock_ls_client

        extracted_text = mock.MagicMock()
        extracted_text.path = str(tmp_path)

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(LSAPIConnectionError):
                documents_indexing.python_func(
                    embedding_model_id="granite-embedding",
                    extracted_text=extracted_text,
                    llama_stack_vector_database_id="ls_milvus",
                )

    @mock.patch.dict(
        "os.environ",
        {
            "LLAMA_STACK_CLIENT_BASE_URL": "https://llama-stack.example.com",
            "LLAMA_STACK_CLIENT_API_KEY": "test-api-key",
        },
    )
    def test_no_documents_returns_early(self, tmp_path):
        """Component returns early and skips indexing when no .md files are found."""
        mocks = _make_all_mocks()

        mock_ls_client = mock.MagicMock()
        mock_ls_client.models.list.return_value = []
        mocks["llama_stack_client"].LlamaStackClient.return_value = mock_ls_client

        extracted_text_dir = tmp_path / "extracted"
        extracted_text_dir.mkdir()
        extracted_text = mock.MagicMock()
        extracted_text.path = str(extracted_text_dir)

        with mock.patch.dict(sys.modules, mocks):
            documents_indexing.python_func(
                embedding_model_id="granite-embedding",
                extracted_text=extracted_text,
                llama_stack_vector_database_id="ls_milvus",
            )

        # LSVectorStore.add_documents should never be called if no documents found
        mocks["ai4rag.rag.vector_store.llama_stack"].LSVectorStore.return_value.add_documents.assert_not_called()

    @mock.patch.dict(
        "os.environ",
        {
            "LLAMA_STACK_CLIENT_BASE_URL": "https://llama-stack.example.com",
            "LLAMA_STACK_CLIENT_API_KEY": "test-api-key",
        },
    )
    def test_documents_are_indexed_in_batches(self, tmp_path):
        """Documents are chunked and indexed; add_documents called once per batch."""
        mocks = _make_all_mocks()

        mock_ls_client = mock.MagicMock()
        mock_ls_client.models.list.return_value = []
        mocks["llama_stack_client"].LlamaStackClient.return_value = mock_ls_client

        # Stub chunker to return one chunk per document
        mock_chunker = mock.MagicMock()
        mock_chunker.split_documents.side_effect = lambda docs: docs
        mocks["ai4rag.rag.chunking"].LangChainChunker.return_value = mock_chunker

        mock_vectorstore = mock.MagicMock()
        mocks["ai4rag.rag.vector_store.llama_stack"].LSVectorStore.return_value = mock_vectorstore

        # Write 3 .md files; use batch_size=2 → 2 batches
        extracted_text_dir = tmp_path / "extracted"
        extracted_text_dir.mkdir()
        for i in range(3):
            (extracted_text_dir / f"doc{i}.md").write_text(f"content {i}", encoding="utf-8")

        extracted_text = mock.MagicMock()
        extracted_text.path = str(extracted_text_dir)

        with mock.patch.dict(sys.modules, mocks):
            documents_indexing.python_func(
                embedding_model_id="granite-embedding",
                extracted_text=extracted_text,
                llama_stack_vector_database_id="ls_milvus",
                batch_size=2,
            )

        assert mock_vectorstore.add_documents.call_count == 2, "Expected 2 batches for 3 docs with batch_size=2"
