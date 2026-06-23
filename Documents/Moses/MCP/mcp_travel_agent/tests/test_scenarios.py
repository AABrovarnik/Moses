"""Smoke-тесты базового клиента.

Проверяем, что MCPClient умеет:
- инкрементить id,
- строить правильные заголовки с mcp-session-id,
- маскировать чувствительные данные в логах,
- парсить JSON-RPC ответ и поднимать MCPError при error.

Без сетевых вызовов — используем httpx.MockTransport.
"""

from __future__ import annotations

import json

import httpx
import pytest

from mcp_clients.base import MCPClient, MCPError, LogQueue


def _client_with_mock(handler) -> MCPClient:
    """Собираем MCPClient с подменённым транспортом."""
    transport = httpx.MockTransport(handler)
    client = MCPClient(
        log_queue=LogQueue(),
        timeout=5.0,
        client_factory=lambda: httpx.Client(transport=transport),
    )
    # Базовый класс используется только в smoke-тестах — задаём имя
    # и endpoint, чтобы валидация в _call_raw не падала.
    client.name = "test"
    client.endpoint = "https://test.invalid/mcp"
    return client


def test_id_increments_and_jsonrpc_envelope():
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured.append(body)
        # Уведомления (без id) тоже надо принять — отвечать не нужно,
        # но MockTransport требует вернуть Response.
        if "id" not in body:
            return httpx.Response(200, json={"jsonrpc": "2.0", "result": {}})
        return httpx.Response(
            200,
            headers={"mcp-session-id": "abc-123"},
            json={"jsonrpc": "2.0", "id": body["id"], "result": {"ok": True}},
        )

    client = _client_with_mock(handler)
    # initialize
    client.initialize()
    # tools/list
    client.list_tools()

    assert captured[0]["method"] == "initialize"
    assert captured[0]["id"] == 1
    assert captured[1]["method"] == "notifications/initialized"
    assert "id" not in captured[1]
    assert captured[2]["method"] == "tools/list"
    assert captured[2]["id"] == 2


def test_session_id_propagated_after_initialize():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "id" not in body:
            return httpx.Response(200, json={"jsonrpc": "2.0", "result": {}})
        return httpx.Response(
            200,
            headers={"mcp-session-id": "sess-xyz"},
            json={"jsonrpc": "2.0", "id": body["id"], "result": {"echo": True}},
        )

    client = _client_with_mock(handler)
    client.initialize()
    assert client._session_id == "sess-xyz"  # noqa: SLF001 — внутренняя проверка


def test_call_tool_returns_result():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "id" not in body:
            return httpx.Response(200, json={"jsonrpc": "2.0", "result": {}})
        if body["method"] == "initialize":
            return httpx.Response(
                200,
                headers={"mcp-session-id": "s1"},
                json={"jsonrpc": "2.0", "id": body["id"], "result": {"serverInfo": {}}},
            )
        if body["method"] == "tools/call":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {"items": [{"a": 1}]},
                },
            )
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": body["id"], "result": {}},
        )

    client = _client_with_mock(handler)
    result = client.call_tool("search-flight", {"origin": "BER", "destination": "FCO"})
    assert result["items"][0]["a"] == 1


def test_jsonrpc_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "id" not in body:
            return httpx.Response(200, json={"jsonrpc": "2.0", "result": {}})
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "error": {"code": -32601, "message": "method not found"},
            },
        )

    client = _client_with_mock(handler)
    with pytest.raises(MCPError) as exc_info:
        client._call_raw("tools/call", {"name": "nope", "arguments": {}})
    assert exc_info.value.server == "test"


def test_mask_secrets():
    payload = {
        "name": "search_places",
        "arguments": {
            "query": "museum",
            "_apiKey": "fsq-secret-12345",
            "nested": {"token": "abc"},
        },
    }
    masked = MCPClient._mask(payload)
    assert masked["arguments"]["_apiKey"] == "<masked>"
    assert masked["arguments"]["nested"]["token"] == "<masked>"
    # OpenAI-ключ в строке
    masked_sk = MCPClient._mask("sk-proj-abcdefghijklmnopqrstuvwxyz")
    assert masked_sk.startswith("sk-proj") and "***" in masked_sk
