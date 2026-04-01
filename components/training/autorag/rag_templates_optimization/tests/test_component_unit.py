"""Tests for the rag_templates_optimization component."""

import os
import ssl
import sys
import types
from unittest import mock

import pytest

from ..component import rag_templates_optimization


class _SentinelAbort(Exception):
    """Raised by mocks to abort the component after client creation."""


def _make_httpx_module():
    """Return a minimal fake httpx module with a trackable Client class."""
    mod = types.ModuleType("httpx")

    class ConnectError(Exception):
        pass

    class Client:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    mod.ConnectError = ConnectError
    mod.Client = Client
    return mod


def _make_minimal_httpx_module():
    """Return a minimal httpx stub for validation-only test paths."""
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
        pass

    mod.APIConnectionError = APIConnectionError
    mod.LlamaStackClient = mock.MagicMock()
    return mod


def _make_openai_module():
    """Stub openai with a real APIConnectionError (MagicMock breaks except clauses)."""
    mod = types.ModuleType("openai")

    class APIConnectionError(Exception):
        pass

    mod.APIConnectionError = APIConnectionError
    mod.OpenAI = mock.MagicMock()
    return mod


def _make_all_mocks():
    """Build sys.modules patch dict for all heavy dependencies."""
    mocks = {}
    for name in [
        "pysqlite3",
        "ai4rag",
        "ai4rag.core",
        "ai4rag.core.experiment",
        "ai4rag.core.experiment.experiment",
        "ai4rag.core.experiment.results",
        "ai4rag.core.hpo",
        "ai4rag.core.hpo.gam_opt",
        "ai4rag.rag",
        "ai4rag.rag.embedding",
        "ai4rag.rag.embedding.base_model",
        "ai4rag.rag.embedding.llama_stack",
        "ai4rag.rag.embedding.openai_model",
        "ai4rag.rag.foundation_models",
        "ai4rag.rag.foundation_models.base_model",
        "ai4rag.rag.foundation_models.llama_stack",
        "ai4rag.rag.foundation_models.openai_model",
        "ai4rag.search_space",
        "ai4rag.search_space.src",
        "ai4rag.search_space.src.parameter",
        "ai4rag.search_space.src.search_space",
        "ai4rag.utils",
        "ai4rag.utils.event_handler",
        "ai4rag.utils.event_handler.event_handler",
        "langchain_core",
        "langchain_core.documents",
        "pandas",
    ]:
        mocks[name] = mock.MagicMock()

    httpx_mod = _make_httpx_module()
    mocks["httpx"] = httpx_mod

    # yaml needs safe_load to return a dict with .items()
    mock_yaml = mock.MagicMock()
    mock_yaml.safe_load.return_value = {}
    mocks["yaml"] = mock_yaml

    return mocks


def _minimal_dependency_modules():
    """Mock imported heavy third-party modules for validation-path tests."""
    return {
        "pandas": mock.MagicMock(),
        "yaml": mock.MagicMock(),
        "ai4rag": mock.MagicMock(),
        "ai4rag.core": mock.MagicMock(),
        "ai4rag.core.experiment": mock.MagicMock(),
        "ai4rag.core.experiment.experiment": mock.MagicMock(AI4RAGExperiment=mock.MagicMock()),
        "ai4rag.core.experiment.results": mock.MagicMock(ExperimentResults=mock.MagicMock()),
        "ai4rag.core.hpo": mock.MagicMock(),
        "ai4rag.core.hpo.gam_opt": mock.MagicMock(GAMOptSettings=mock.MagicMock()),
        "ai4rag.rag": mock.MagicMock(),
        "ai4rag.rag.embedding": mock.MagicMock(),
        "ai4rag.rag.embedding.base_model": mock.MagicMock(BaseEmbeddingModel=mock.MagicMock()),
        "ai4rag.rag.embedding.llama_stack": mock.MagicMock(LSEmbeddingModel=mock.MagicMock()),
        "ai4rag.rag.embedding.openai_model": mock.MagicMock(OpenAIEmbeddingModel=mock.MagicMock()),
        "ai4rag.rag.foundation_models": mock.MagicMock(),
        "ai4rag.rag.foundation_models.base_model": mock.MagicMock(BaseFoundationModel=mock.MagicMock()),
        "ai4rag.rag.foundation_models.llama_stack": mock.MagicMock(LSFoundationModel=mock.MagicMock()),
        "ai4rag.rag.foundation_models.openai_model": mock.MagicMock(OpenAIFoundationModel=mock.MagicMock()),
        "ai4rag.search_space": mock.MagicMock(),
        "ai4rag.search_space.src": mock.MagicMock(),
        "ai4rag.search_space.src.parameter": mock.MagicMock(Parameter=mock.MagicMock()),
        "ai4rag.search_space.src.search_space": mock.MagicMock(AI4RAGSearchSpace=mock.MagicMock()),
        "ai4rag.utils": mock.MagicMock(),
        "ai4rag.utils.event_handler": mock.MagicMock(),
        "ai4rag.utils.event_handler.event_handler": mock.MagicMock(
            BaseEventHandler=type("BaseEventHandler", (), {}),
            LogLevel=mock.MagicMock(),
        ),
        "langchain_core": mock.MagicMock(),
        "langchain_core.documents": mock.MagicMock(Document=mock.MagicMock()),
        "llama_stack_client": mock.MagicMock(LlamaStackClient=mock.MagicMock()),
        "openai": mock.MagicMock(OpenAI=mock.MagicMock()),
        "httpx": _make_minimal_httpx_module(),
    }


class TestRagTemplatesOptimizationUnitTests:
    """Unit tests for component logic."""

    def test_component_function_exists(self):
        """Test that the component function is properly imported."""
        assert callable(rag_templates_optimization)
        assert hasattr(rag_templates_optimization, "python_func")

    def test_component_with_default_parameters(self):
        """Test component has expected interface (required args)."""
        import inspect

        sig = inspect.signature(rag_templates_optimization.python_func)
        params = list(sig.parameters)
        assert "extracted_text" in params
        assert "test_data" in params
        assert "search_space_prep_report" in params
        assert "rag_patterns" in params

    def test_missing_chat_model_url_raises_type_error(self):
        """Missing required model endpoint args raises TypeError early."""
        with mock.patch.dict(sys.modules, _minimal_dependency_modules()):
            with pytest.raises(TypeError, match="chat_model_url must be a non-empty string"):
                rag_templates_optimization.python_func(
                    extracted_text="/tmp/extracted",
                    test_data="/tmp/test_data.json",
                    search_space_prep_report="/tmp/report.yml",
                    rag_patterns=mock.MagicMock(path="/tmp/rag_patterns", metadata={}, uri=""),
                    embedded_artifact=mock.MagicMock(path="/tmp/embedded"),
                    test_data_key="small-dataset/benchmark.json",
                    chat_model_url="",
                    chat_model_token="token",
                    embedding_model_url="https://emb",
                    embedding_model_token="token",
                    optimization_settings={"metric": "faithfulness", "max_number_of_rag_patterns": 8},
                )

    def test_invalid_vector_store_id_raises_value_error(self):
        """Unsupported llama_stack_vector_database_id raises ValueError."""
        with mock.patch.dict(sys.modules, _minimal_dependency_modules()):
            with pytest.raises(ValueError, match="is not supported"):
                rag_templates_optimization.python_func(
                    extracted_text="/tmp/extracted",
                    test_data="/tmp/test_data.json",
                    search_space_prep_report="/tmp/report.yml",
                    rag_patterns=mock.MagicMock(path="/tmp/rag_patterns", metadata={}, uri=""),
                    embedded_artifact=mock.MagicMock(path="/tmp/embedded"),
                    test_data_key="small-dataset/benchmark.json",
                    chat_model_url="https://chat",
                    chat_model_token="token",
                    embedding_model_url="https://emb",
                    embedding_model_token="token",
                    llama_stack_vector_database_id="unsupported_vs",
                    optimization_settings={"metric": "faithfulness", "max_number_of_rag_patterns": 8},
                )

    def test_max_number_of_rag_patterns_non_numeric_string_raises_value_error(self):
        """UI may pass string parameters; non-numeric strings are rejected with a clear error."""
        with mock.patch.dict(sys.modules, _minimal_dependency_modules()):
            with pytest.raises(ValueError, match="max_number_of_rag_patterns must be a valid integer"):
                rag_templates_optimization.python_func(
                    extracted_text="/tmp/extracted",
                    test_data="/tmp/test_data.json",
                    search_space_prep_report="/tmp/report.yml",
                    rag_patterns=mock.MagicMock(path="/tmp/rag_patterns", metadata={}, uri=""),
                    embedded_artifact=mock.MagicMock(path="/tmp/embedded"),
                    test_data_key="small-dataset/benchmark.json",
                    chat_model_url="https://chat",
                    chat_model_token="token",
                    embedding_model_url="https://emb",
                    embedding_model_token="token",
                    optimization_settings={
                        "metric": "faithfulness",
                        "max_number_of_rag_patterns": "not-a-number",
                    },
                )

    @mock.patch.dict(
        os.environ,
        {
            "LLAMA_STACK_CLIENT_BASE_URL": "https://llama-stack.example.com",
            "LLAMA_STACK_CLIENT_API_KEY": "test-api-key",
        },
    )
    def test_max_number_of_rag_patterns_numeric_string_coerced_for_gam_opt(self, tmp_path):
        """Pipeline UI often sends numbers as strings; they must coerce to int for GAMOptSettings."""
        mocks = _make_all_mocks()
        llama_mod = _make_llama_stack_client_module()
        mock_ls = mock.MagicMock()
        mock_ls.models.list.return_value = []
        llama_mod.LlamaStackClient.return_value = mock_ls
        mocks["llama_stack_client"] = llama_mod
        mocks["openai"] = _make_openai_module()
        mocks["ai4rag.core.experiment.experiment"].AI4RAGExperiment.side_effect = _SentinelAbort

        search_space_report = tmp_path / "report.yml"
        search_space_report.write_text("{}")
        extracted_text = str(tmp_path / "extracted_text")
        test_data_path = tmp_path / "test_data.json"
        test_data_path.write_text("[]")
        test_data = str(test_data_path)
        rag_patterns = mock.MagicMock()
        embedded_artifact = mock.MagicMock()

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(_SentinelAbort):
                rag_templates_optimization.python_func(
                    extracted_text=extracted_text,
                    test_data=test_data,
                    search_space_prep_report=str(search_space_report),
                    rag_patterns=rag_patterns,
                    embedded_artifact=embedded_artifact,
                    test_data_key="small-dataset/benchmark.json",
                    optimization_settings={"metric": "faithfulness", "max_number_of_rag_patterns": "8"},
                )

        mocks["ai4rag.core.hpo.gam_opt"].GAMOptSettings.assert_called_once_with(max_evals=8)


class TestSSLFallbackRagTemplatesOptimization:
    """Tests for SSL retry logic in _create_llama_stack_client and _create_openai_client."""

    def _make_paths(self, tmp_path):
        """Create minimal real files needed by the component."""
        search_space_report = tmp_path / "report.yml"
        search_space_report.write_text("{}")
        return (
            str(tmp_path / "extracted_text"),  # non-existent dir → load_as_langchain_doc returns []
            str(tmp_path / "test_data.json"),
            str(search_space_report),
        )

    def _make_output_artifacts(self):
        rag_patterns = mock.MagicMock()
        embedded_artifact = mock.MagicMock()
        return rag_patterns, embedded_artifact

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

        llama_mod = _make_llama_stack_client_module()
        llama_mod.LlamaStackClient.side_effect = fake_ls_client
        mocks["llama_stack_client"] = llama_mod
        mocks["openai"] = _make_openai_module()

        # Abort after client creation via AI4RAGSearchSpace
        mocks["ai4rag.search_space.src.search_space"].AI4RAGSearchSpace.side_effect = _SentinelAbort

        extracted_text, test_data, search_space_report = self._make_paths(tmp_path)
        rag_patterns, embedded_artifact = self._make_output_artifacts()

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(_SentinelAbort):
                rag_templates_optimization.python_func(
                    extracted_text=extracted_text,
                    test_data=test_data,
                    search_space_prep_report=search_space_report,
                    rag_patterns=rag_patterns,
                    embedded_artifact=embedded_artifact,
                    test_data_key="small-dataset/benchmark.json",
                )

        assert ls_call_count == 2, "LlamaStackClient should be instantiated twice (initial + SSL retry)"
        assert ls_kwargs_history[0].get("http_client") is None, "First call should not disable SSL"
        assert isinstance(ls_kwargs_history[1].get("http_client"), mocks["httpx"].Client), (
            "Second call should pass httpx.Client"
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

        llama_mod = _make_llama_stack_client_module()
        LSAPIConnectionError = llama_mod.APIConnectionError
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

        llama_mod.LlamaStackClient.side_effect = fake_ls_client
        mocks["llama_stack_client"] = llama_mod
        mocks["openai"] = _make_openai_module()

        mocks["ai4rag.search_space.src.search_space"].AI4RAGSearchSpace.side_effect = _SentinelAbort

        extracted_text, test_data, search_space_report = self._make_paths(tmp_path)
        rag_patterns, embedded_artifact = self._make_output_artifacts()

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(_SentinelAbort):
                rag_templates_optimization.python_func(
                    extracted_text=extracted_text,
                    test_data=test_data,
                    search_space_prep_report=search_space_report,
                    rag_patterns=rag_patterns,
                    embedded_artifact=embedded_artifact,
                    test_data_key="small-dataset/benchmark.json",
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

        llama_mod = _make_llama_stack_client_module()
        llama_mod.LlamaStackClient.return_value = mock_ls_client
        mocks["llama_stack_client"] = llama_mod
        mocks["openai"] = _make_openai_module()

        extracted_text, test_data, search_space_report = self._make_paths(tmp_path)
        rag_patterns, embedded_artifact = self._make_output_artifacts()

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(ConnectionRefusedError):
                rag_templates_optimization.python_func(
                    extracted_text=extracted_text,
                    test_data=test_data,
                    search_space_prep_report=search_space_report,
                    rag_patterns=rag_patterns,
                    embedded_artifact=embedded_artifact,
                    test_data_key="small-dataset/benchmark.json",
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

        llama_mod = _make_llama_stack_client_module()
        LSAPIConnectionError = llama_mod.APIConnectionError
        err = LSAPIConnectionError("Connection timeout")
        err.__cause__ = TimeoutError("timed out")

        mock_ls_client = mock.MagicMock()
        mock_ls_client.models.list.side_effect = err
        llama_mod.LlamaStackClient.return_value = mock_ls_client
        mocks["llama_stack_client"] = llama_mod
        mocks["openai"] = _make_openai_module()

        extracted_text, test_data, search_space_report = self._make_paths(tmp_path)
        rag_patterns, embedded_artifact = self._make_output_artifacts()

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(LSAPIConnectionError):
                rag_templates_optimization.python_func(
                    extracted_text=extracted_text,
                    test_data=test_data,
                    search_space_prep_report=search_space_report,
                    rag_patterns=rag_patterns,
                    embedded_artifact=embedded_artifact,
                    test_data_key="small-dataset/benchmark.json",
                )

    def test_openai_client_ssl_retry_with_verify_false(self, tmp_path):
        """SSL error on OpenAI models.list() retries with httpx.Client(verify=False)."""
        mocks = _make_all_mocks()

        openai_call_count = 0
        openai_kwargs_history = []

        mock_openai_client_fail = mock.MagicMock()
        mock_openai_client_fail.models.list.side_effect = ssl.SSLCertVerificationError(
            "CERTIFICATE_VERIFY_FAILED: self-signed certificate"
        )
        mock_openai_client_ok = mock.MagicMock()
        _models_list_ok = mock.MagicMock()
        _models_list_ok.data = [mock.MagicMock(id="test-model", max_model_len=8192)]
        mock_openai_client_ok.models.list.return_value = _models_list_ok

        def fake_openai(**kwargs):
            nonlocal openai_call_count
            openai_call_count += 1
            openai_kwargs_history.append(kwargs)
            if openai_call_count % 2 == 1:  # first call per endpoint fails
                return mock_openai_client_fail
            return mock_openai_client_ok

        openai_mod = _make_openai_module()
        openai_mod.OpenAI.side_effect = fake_openai
        mocks["openai"] = openai_mod
        mocks["llama_stack_client"] = _make_llama_stack_client_module()

        # Abort after client creation
        mocks["ai4rag.search_space.src.search_space"].AI4RAGSearchSpace.side_effect = _SentinelAbort

        extracted_text, test_data, search_space_report = self._make_paths(tmp_path)
        rag_patterns, embedded_artifact = self._make_output_artifacts()

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(_SentinelAbort):
                rag_templates_optimization.python_func(
                    extracted_text=extracted_text,
                    test_data=test_data,
                    search_space_prep_report=search_space_report,
                    rag_patterns=rag_patterns,
                    embedded_artifact=embedded_artifact,
                    test_data_key="small-dataset/benchmark.json",
                    chat_model_url="http://chat.example.com",
                    chat_model_token="chat-token",
                    embedding_model_url="http://embed.example.com",
                    embedding_model_token="embed-token",
                )

        # Each endpoint: initial call fails (SSL), retry succeeds → 2 calls per endpoint = 4 total
        assert openai_call_count == 4
        for retry_idx in [1, 3]:
            assert isinstance(openai_kwargs_history[retry_idx].get("http_client"), mocks["httpx"].Client)
            assert openai_kwargs_history[retry_idx]["http_client"].kwargs.get("verify") is False

    def test_openai_client_api_connection_error_wrapping_ssl_retries(self, tmp_path):
        """OAIAPIConnectionError wrapping an SSL cause triggers the verify=False retry (production case)."""
        mocks = _make_all_mocks()

        openai_mod = _make_openai_module()
        OAIAPIConnectionError = openai_mod.APIConnectionError
        ssl_err = ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED: self-signed certificate")
        api_err = OAIAPIConnectionError("Connection error.")
        api_err.__cause__ = ssl_err

        openai_call_count = 0
        openai_kwargs_history = []

        mock_openai_client_fail = mock.MagicMock()
        mock_openai_client_fail.models.list.side_effect = api_err
        mock_openai_client_ok = mock.MagicMock()
        mock_openai_client_ok.models.list.return_value = []

        def fake_openai(**kwargs):
            nonlocal openai_call_count
            openai_call_count += 1
            openai_kwargs_history.append(kwargs)
            if openai_call_count % 2 == 1:
                return mock_openai_client_fail
            return mock_openai_client_ok

        openai_mod.OpenAI.side_effect = fake_openai
        mocks["openai"] = openai_mod
        mocks["llama_stack_client"] = _make_llama_stack_client_module()

        mocks["ai4rag.search_space.src.search_space"].AI4RAGSearchSpace.side_effect = _SentinelAbort

        extracted_text, test_data, search_space_report = self._make_paths(tmp_path)
        rag_patterns, embedded_artifact = self._make_output_artifacts()

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(_SentinelAbort):
                rag_templates_optimization.python_func(
                    extracted_text=extracted_text,
                    test_data=test_data,
                    search_space_prep_report=search_space_report,
                    rag_patterns=rag_patterns,
                    embedded_artifact=embedded_artifact,
                    test_data_key="small-dataset/benchmark.json",
                    chat_model_url="http://chat.example.com",
                    chat_model_token="chat-token",
                    embedding_model_url="http://embed.example.com",
                    embedding_model_token="embed-token",
                )

        # Each endpoint: initial call fails (SSL), retry succeeds → 2 calls per endpoint = 4 total
        assert openai_call_count == 4
        for retry_idx in [1, 3]:
            assert isinstance(openai_kwargs_history[retry_idx].get("http_client"), mocks["httpx"].Client)
            assert openai_kwargs_history[retry_idx]["http_client"].kwargs.get("verify") is False

    def test_openai_client_api_connection_error_non_ssl_cause_is_reraised(self, tmp_path):
        """OAIAPIConnectionError whose cause is NOT SSL propagates without retry."""
        mocks = _make_all_mocks()

        openai_mod = _make_openai_module()
        OAIAPIConnectionError = openai_mod.APIConnectionError
        err = OAIAPIConnectionError("Connection timeout")
        err.__cause__ = TimeoutError("timed out")

        mock_openai_client = mock.MagicMock()
        mock_openai_client.models.list.side_effect = err
        openai_mod.OpenAI.return_value = mock_openai_client
        mocks["openai"] = openai_mod
        mocks["llama_stack_client"] = _make_llama_stack_client_module()

        extracted_text, test_data, search_space_report = self._make_paths(tmp_path)
        rag_patterns, embedded_artifact = self._make_output_artifacts()

        with mock.patch.dict(sys.modules, mocks):
            with pytest.raises(OAIAPIConnectionError):
                rag_templates_optimization.python_func(
                    extracted_text=extracted_text,
                    test_data=test_data,
                    search_space_prep_report=search_space_report,
                    rag_patterns=rag_patterns,
                    embedded_artifact=embedded_artifact,
                    test_data_key="small-dataset/benchmark.json",
                    chat_model_url="http://chat.example.com",
                    chat_model_token="chat-token",
                    embedding_model_url="http://embed.example.com",
                    embedding_model_token="embed-token",
                )
