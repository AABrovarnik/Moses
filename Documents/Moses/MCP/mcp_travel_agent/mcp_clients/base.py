"""Базовый JSON-RPC клиент для MCP-серверов + общая очередь логов.

Используется Kiwi, Trivago и (в будущем) Foursquare-клиентами.
Сделан как тонкая обёртка над httpx — без зависимости от
официального mcp SDK, чтобы легче было логировать и тестировать.

Протокол MCP (упрощённо):
    POST <endpoint>
    Headers:
        Content-Type: application/json
        Accept: application/json, text/event-stream
        mcp-session-id: <id из ответа initialize> (после handshake)
        (опц.) Authorization: Bearer <token>

    Body (JSON-RPC 2.0):
        {"jsonrpc": "2.0", "id": <int|str>, "method": "...", "params": {...}}

    Server возвращает либо JSON, либо SSE-стрим. Для наших вызовов
    достаточно одного JSON-ответа на каждый запрос.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import httpx


# --- Логгер --------------------------------------------------------------


@dataclass
class MCPLogEvent:
    """Одно событие MCP для UI и тестов."""

    timestamp: float
    server: str              # например "kiwi" / "trivago"
    kind: str                # "init" | "request" | "response" | "error"
    method: str | None       # JSON-RPC method, для request/response
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "server": self.server,
            "kind": self.kind,
            "method": self.method,
            "details": self.details,
        }


class LogQueue:
    """Потокобезопасная очередь событий для UI Streamlit.

    Streamlit сам по себе однопоточный в рамках сессии, но мы
    страхуемся на случай, если логгер будут дёргать из тестов.
    """

    def __init__(self) -> None:
        self._events: list[MCPLogEvent] = []

    def push(self, event: MCPLogEvent) -> None:
        self._events.append(event)

    def all(self) -> list[MCPLogEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()


# --- Базовый клиент ------------------------------------------------------


# Хедеры по умолчанию для MCP. mcp-session-id добавляется динамически.
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


class MCPError(RuntimeError):
    """Ошибка вызова MCP (сетевая или JSON-RPC error)."""

    def __init__(self, message: str, *, server: str, payload: dict | None = None) -> None:
        super().__init__(message)
        self.server = server
        self.payload = payload or {}


class MCPClient:
    """База для MCP-клиентов.

    Подкласс задаёт `name` и `endpoint`, опционально переопределяет
    `extra_headers`. Перед вызовом инструментов нужно вызвать
    `initialize()` — это handshake и сохранение mcp-session-id.
    """

    name: str = "mcp"
    endpoint: str = ""

    def __init__(
        self,
        log_queue: LogQueue | None = None,
        timeout: float = 30.0,
        extra_headers: dict[str, str] | None = None,
        client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self.logs = log_queue or LogQueue()
        self.timeout = timeout
        self.extra_headers = dict(extra_headers or {})
        self._session_id: str | None = None
        self._initialized: bool = False
        self._id_counter: int = 0
        # Фабрика httpx-клиента вынесена отдельно, чтобы тесты могли
        # подсунуть свой транспорт (например, MockTransport).
        self._client_factory = client_factory or self._default_client_factory

    # --- фабрика httpx ----------------------------------------------------

    def _default_client_factory(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout)

    def _client(self) -> httpx.Client:
        return self._client_factory()

    # --- утилиты JSON-RPC -------------------------------------------------

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def _build_headers(self) -> dict[str, str]:
        h = dict(DEFAULT_HEADERS)
        h.update(self.extra_headers)
        if self._session_id:
            h["mcp-session-id"] = self._session_id
        return h

    def _log(self, kind: str, method: str | None, details: dict[str, Any]) -> None:
        self.logs.push(
            MCPLogEvent(
                timestamp=time.time(),
                server=self.name,
                kind=kind,
                method=method,
                details=details,
            )
        )

    # Ключи dict-ов, чьи значения маскируем как чувствительные.
    _SENSITIVE_KEYS = {
        "apikey", "api_key", "_apikey", "token", "secret", "password",
        "authorization", "auth", "access_token", "refresh_token",
    }

    @classmethod
    def _mask(cls, value: Any, *, _key: str | None = None) -> Any:
        """Маскирует чувствительные данные в логах.

        Правила:
        - dict: маскируем значение, если имя ключа чувствительное
          (регистр неважен); иначе рекурсивно обходим.
        - list/tuple: рекурсивно по элементам.
        - str: маскируем, если строка похожа на OpenAI-ключ (sk-...).
        """
        if _key is not None and _key.lower() in cls._SENSITIVE_KEYS:
            return "<masked>"
        if isinstance(value, dict):
            return {k: cls._mask(v, _key=k) for k, v in value.items()}
        if isinstance(value, list):
            return [cls._mask(v) for v in value]
        if isinstance(value, tuple):
            return tuple(cls._mask(v) for v in value)
        if isinstance(value, str):
            if value.startswith("sk-") and len(value) > 12:
                return value[:7] + "***" + value[-4:]
        return value

    # --- handshake и вызовы ----------------------------------------------

    def initialize(self) -> dict[str, Any]:
        """Шаг 1: handshake. Сохраняет mcp-session-id."""
        method = "initialize"
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mcp-travel-agent", "version": "0.1.0"},
        }
        try:
            response = self._call_raw(method, params, require_session=False)
        except MCPError:
            self._log("error", method, {"stage": "initialize"})
            raise

        # Сохраняем session-id из заголовка ответа.
        sid = response.get("_headers", {}).get("mcp-session-id")
        if sid:
            self._session_id = sid

        # Уведомление notifications/initialized — отдельным запросом
        # без ожидания ответа (но MCP ожидает именно POST с JSON-RPC).
        self._notify("notifications/initialized", {})

        self._initialized = True
        self._log("init", method, {"sessionId": self._session_id})
        return response.get("result", {})

    def list_tools(self) -> list[dict[str, Any]]:
        """tools/list — полезно для отладки и валидации схем."""
        if not self._initialized:
            self.initialize()
        response = self._call_raw("tools/list", {})
        result = response.get("result", {}) or {}
        tools = result.get("tools", []) if isinstance(result, dict) else []
        self._log("response", "tools/list", {"tools_count": len(tools)})
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """tools/call — основной вызов инструмента MCP."""
        if not self._initialized:
            self.initialize()
        self._log(
            "request",
            "tools/call",
            {"name": name, "arguments": self._mask(arguments)},
        )
        response = self._call_raw(
            "tools/call", {"name": name, "arguments": arguments}
        )
        result = response.get("result", {})
        self._log(
            "response",
            "tools/call",
            {"name": name, "result_preview": _preview(result)},
        )
        return result

    # --- низкоуровневый обмен -------------------------------------------

    def _call_raw(
        self,
        method: str,
        params: dict[str, Any],
        *,
        require_session: bool = True,
    ) -> dict[str, Any]:
        if not self.endpoint:
            raise MCPError(f"{self.name}: endpoint не задан", server=self.name)

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }
        headers = self._build_headers()
        if require_session and not self._session_id:
            # На этапе initialize session-id ещё нет — это норма.
            # Для всех последующих вызовов ожидаем, что он есть.
            pass

        with self._client() as client:
            try:
                resp = client.post(
                    self.endpoint,
                    headers=headers,
                    content=json.dumps(payload),
                )
            except httpx.HTTPError as exc:
                self._log("error", method, {"stage": "http", "error": str(exc)})
                raise MCPError(
                    f"{self.name}: HTTP ошибка — {exc}", server=self.name
                ) from exc

        if resp.status_code >= 400:
            self._log(
                "error",
                method,
                {"stage": "http", "status": resp.status_code, "body": resp.text[:500]},
            )
            raise MCPError(
                f"{self.name}: HTTP {resp.status_code}: {resp.text[:200]}",
                server=self.name,
            )

        # Kiwi отдаёт ответ как text/event-stream, обычные JSON-RPC серверы —
        # как application/json. Парсим оба варианта.
        data = self._parse_response_body(resp.text)
        if data is None:
            self._log("error", method, {"stage": "json", "body": resp.text[:500]})
            raise MCPError(
                f"{self.name}: невалидный JSON в ответе", server=self.name
            )

        if "error" in data and data["error"]:
            self._log("error", method, {"stage": "rpc", "error": data["error"]})
            raise MCPError(
                f"{self.name}: JSON-RPC error — {data['error']}",
                server=self.name,
                payload=data["error"],
            )

        # Прокидываем заголовки ответа дальше — нужно для handshake.
        data["_headers"] = {
            k.lower(): v for k, v in resp.headers.items()
        }
        return data

    @staticmethod
    def _parse_response_body(text: str) -> dict[str, Any] | None:
        """Парсит либо application/json, либо SSE-стрим с JSON-RPC.

        SSE-формат:
            event: message
            data: {"jsonrpc": "2.0", ...}

        Берём последний data-блок, в котором есть JSON.
        """
        text = text.strip()
        if not text:
            return None

        # Обычный JSON — Kiwi/Trivago в SSE-режиме присылают именно так.
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None

        # SSE: разделяем по двойному переводу строки.
        last_json: dict[str, Any] | None = None
        for event_block in text.split("\n\n"):
            data_line = None
            for line in event_block.splitlines():
                if line.startswith("data:"):
                    data_line = line[5:].strip()
                    break
            if not data_line:
                continue
            try:
                obj = json.loads(data_line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                last_json = obj
        return last_json

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        """Уведомление (без поля id, без ожидания ответа)."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        with self._client() as client:
            try:
                client.post(
                    self.endpoint,
                    headers=self._build_headers(),
                    content=json.dumps(payload),
                )
            except httpx.HTTPError as exc:
                # Уведомления не критичны — лог и идём дальше.
                self._log("error", method, {"stage": "notify", "error": str(exc)})


# --- helpers -------------------------------------------------------------


def _preview(value: Any, limit: int = 400) -> Any:
    """Сокращает большие ответы для логов."""
    try:
        s = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = repr(value)
    if len(s) > limit:
        return s[:limit] + f"... (+{len(s) - limit} chars)"
    return value


def as_iterable(x: Any) -> Iterable[Any]:
    """Удобный flatten для списков словарей в ответах MCP."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]
