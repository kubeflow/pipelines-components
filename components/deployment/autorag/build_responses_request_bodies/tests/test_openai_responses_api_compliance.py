"""Structural compliance with OpenAI Responses ``POST /v1/responses`` request JSON."""

import json

import pytest

from .openai_responses_request_validate import validate_responses_api_request_body
from .test_component_unit import OUTPUT_FILENAME, _minimal_pattern, _run_python_func

# Shape taken from a real pipeline artifact (Llama Stack / OpenAI-compatible Responses).
_USER_PIPELINE_SAMPLE = {
    "model": "vllm-inference-qwen/qwen25-7b-instruct",
    "stream": False,
    "store": True,
    "input": [
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "\n\nContext:\n[Retrieved context will be injected by the file_search "
                        "tool when configured.]:\n\nQuestion: What information is available in the "
                        "indexed knowledge base?. \nAgain, please answer the question based on "
                        "the context provided only."
                    ),
                }
            ],
        }
    ],
    "metadata": {
        "rag_pattern_name": "Pattern2",
        "rag_pattern_iteration": "1",
        "vector_datasource_type": "ls_milvus",
        "embedding_model_id": "vllm-embedding/bge-m3",
    },
    "instructions": (
        "Please answer the question I provide in the Question section below, based solely on "
        "the information I provide in the Context section."
    ),
    "tools": [
        {
            "type": "file_search",
            "vector_store_ids": ["vs_e06c7601-7975-4966-bca3-f0d6079417ed"],
            "max_num_results": 10,
        }
    ],
    "tool_choice": {"type": "file_search"},
    "include": ["file_search_call.results"],
}


def test_pipeline_sample_json_is_compliant() -> None:
    """Realistic generated body matches the structural rules we enforce."""
    errors = validate_responses_api_request_body(_USER_PIPELINE_SAMPLE)
    assert errors == [], errors


def test_round_trip_json_stays_compliant() -> None:
    """JSON serialization preserves types OpenAI-style clients expect."""
    raw = json.dumps(_USER_PIPELINE_SAMPLE)
    errors = validate_responses_api_request_body(json.loads(raw))
    assert errors == [], errors


def test_component_output_passes_openai_responses_validation(tmp_path) -> None:
    """Bodies from ``prepare_responses_api_requests`` validate the same way."""
    out, _ = _run_python_func(tmp_path, [("p1", _minimal_pattern())])
    body = json.loads((out / "p1" / OUTPUT_FILENAME).read_text(encoding="utf-8"))
    errors = validate_responses_api_request_body(body)
    assert errors == [], errors


@pytest.mark.parametrize(
    "bad_body,fragment",
    [
        ({}, "missing required"),
        ({"model": "x"}, "missing required field: input"),
        ({"model": "x", "input": "ok", "stream": "no"}, "stream must be a boolean"),
        ({"model": "x", "input": "ok", "metadata": {"a": 1}}, "must be a string"),
        (
            {
                "model": "x",
                "input": [
                    {"type": "message", "role": "invalid_role", "content": [{"type": "input_text", "text": "t"}]}
                ],
            },
            "role must be one of",
        ),
    ],
)
def test_validator_catches_common_mistakes(bad_body: dict, fragment: str) -> None:
    """Negative cases: validator returns messages containing ``fragment``."""
    errors = validate_responses_api_request_body(bad_body)
    assert errors, f"expected errors for {bad_body!r}"
    assert any(fragment in e for e in errors), errors
