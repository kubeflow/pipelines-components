"""Validate request bodies for OpenAI-compatible ``POST /v1/responses``.

The OpenAI Responses API accepts ``model``, ``input`` (string or structured items),
optional ``instructions``, ``tools``, ``stream``, ``store``, and ``metadata``. See
https://developers.openai.com/api/docs/guides/migrate-to-responses

Llama Stack exposes the same OpenAI-compatible surface at ``/v1/responses``; this
module checks shapes that both stacks typically accept for non-streaming RAG calls.
"""

from __future__ import annotations

from typing import Any

_MESSAGE_ROLES = frozenset({"system", "developer", "user", "assistant"})


def validate_responses_api_request_body(body: Any) -> list[str]:
    """Return validation issue messages; empty list means the body looks compliant.

    This is a **structural** check (types and nesting), not a guarantee the server
    accepts every optional field (e.g. ``ranking_options`` may be stack-specific).
    """
    errors: list[str] = []
    if not isinstance(body, dict):
        return ["root must be a JSON object"]

    if "model" not in body:
        errors.append("missing required field: model")
    elif not isinstance(body["model"], str):
        errors.append("model must be a string")
    elif not body["model"].strip():
        errors.append("model must be a non-empty string")

    if "input" not in body:
        errors.append("missing required field: input")
    else:
        errors.extend(_validate_input(body["input"]))

    if "stream" in body and not isinstance(body["stream"], bool):
        errors.append("stream must be a boolean when present")

    if "store" in body and not isinstance(body["store"], bool):
        errors.append("store must be a boolean when present")

    if "instructions" in body and body["instructions"] is not None:
        if not isinstance(body["instructions"], str):
            errors.append("instructions must be a string when present")

    if "metadata" in body:
        errors.extend(_validate_metadata(body["metadata"]))

    if "tools" in body:
        errors.extend(_validate_tools(body["tools"]))
    if "tool_choice" in body:
        errors.extend(_validate_tool_choice(body["tool_choice"]))
    if "include" in body:
        errors.extend(_validate_include(body["include"]))

    return errors


def _validate_input(inp: Any) -> list[str]:
    if isinstance(inp, str):
        return []
    if not isinstance(inp, list):
        return ["input must be a string or a JSON array"]
    for i, item in enumerate(inp):
        if not isinstance(item, dict):
            return [f"input[{i}] must be an object"]
        err = _validate_input_item(i, item)
        if err:
            return err
    return []


def _validate_input_item(i: int, item: dict[str, Any]) -> list[str]:
    """Accept Responses ``message`` items or Chat Completions-style ``role``/``content`` rows."""
    itype = item.get("type")
    if itype == "message":
        role = item.get("role")
        if role not in _MESSAGE_ROLES:
            return [f"input[{i}].role must be one of {_MESSAGE_ROLES}, got {role!r}"]
        content = item.get("content")
        if not isinstance(content, list):
            return [f"input[{i}].content must be an array for type message"]
        for j, part in enumerate(content):
            if not isinstance(part, dict):
                return [f"input[{i}].content[{j}] must be an object"]
            ptype = part.get("type")
            if ptype == "input_text":
                if "text" not in part or not isinstance(part["text"], str):
                    return [f"input[{i}].content[{j}] input_text requires string text"]
        return []

    # Chat Completions-compatible rows: ``{ "role": "...", "content": "..." }`` (see migration guide).
    if "role" in item:
        role = item.get("role")
        if role not in _MESSAGE_ROLES:
            return [f"input[{i}].role must be one of {_MESSAGE_ROLES}, got {role!r}"]
        content = item.get("content")
        if isinstance(content, str):
            return []
        if isinstance(content, list):
            for j, part in enumerate(content):
                if not isinstance(part, dict):
                    return [f"input[{i}].content[{j}] must be an object"]
                if part.get("type") == "input_text" and ("text" not in part or not isinstance(part["text"], str)):
                    return [f"input[{i}].content[{j}] input_text requires string text"]
            return []
        return [f"input[{i}].content must be a string or array"]

    return []


def _validate_metadata(meta: Any) -> list[str]:
    if meta is None:
        return []
    if not isinstance(meta, dict):
        return ["metadata must be a JSON object"]
    for k, v in meta.items():
        if not isinstance(k, str):
            return ["metadata keys must be strings"]
        if not isinstance(v, str):
            return [f"metadata[{k!r}] must be a string (OpenAI/Llama Stack custom metadata)"]
    return []


def _validate_tools(tools: Any) -> list[str]:
    if not isinstance(tools, list):
        return ["tools must be a JSON array"]
    for i, tool in enumerate(tools):
        if not isinstance(tool, dict):
            return [f"tools[{i}] must be an object"]
        ttype = tool.get("type")
        if ttype == "file_search":
            vs = tool.get("vector_store_ids")
            if not isinstance(vs, list) or not all(isinstance(x, str) for x in vs):
                return [f"tools[{i}] file_search.vector_store_ids must be an array of strings"]
            if "max_num_results" in tool and not isinstance(tool["max_num_results"], int):
                return [f"tools[{i}] max_num_results must be an integer when present"]
            if "ranking_options" in tool and tool["ranking_options"] is not None:
                ro = tool["ranking_options"]
                if not isinstance(ro, dict):
                    return [f"tools[{i}] ranking_options must be an object when present"]
        elif ttype is None:
            return [f"tools[{i}] missing type"]
    return []


def _validate_tool_choice(tool_choice: Any) -> list[str]:
    if tool_choice is None:
        return []
    if not isinstance(tool_choice, dict):
        return ["tool_choice must be an object when present"]
    if "type" not in tool_choice or not isinstance(tool_choice["type"], str):
        return ["tool_choice.type must be a string when present"]
    return []


def _validate_include(include: Any) -> list[str]:
    if not isinstance(include, list):
        return ["include must be an array when present"]
    if not all(isinstance(v, str) for v in include):
        return ["include entries must be strings"]
    return []
