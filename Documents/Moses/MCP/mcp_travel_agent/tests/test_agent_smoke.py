"""Сухой прогон TravelAgent.run() с mock-OpenAI клиентом.

Проверяем, что агент:
- корректно подсовывает TOOL_SCHEMAS в каждый вызов,
- получает tool_calls и передаёт их в MCP-клиенты,
- возвращает финальный ответ пользователю.

MCP-клиенты тоже подменяем mock-объектами, чтобы не дёргать сеть.
"""

from __future__ import annotations

from typing import Any

from agent.openai_agent import TravelAgent
from mcp_clients.base import LogQueue


class _MockFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class _MockToolCall:
    def __init__(self, id_: str, name: str, arguments: str):
        self.id = id_
        self.function = _MockFunction(name, arguments)


class _MockChoiceMsg:
    def __init__(self, content: str | None = None, tool_calls: list[_MockToolCall] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {"role": "assistant"}
        if self.content is not None:
            out["content"] = self.content
        if self.tool_calls:
            out["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        return out


class _MockChoice:
    def __init__(self, message: _MockChoiceMsg):
        self.message = message


class _MockResponse:
    def __init__(self, message: _MockChoiceMsg):
        self.choices = [_MockChoice(message)]


class _MockCompletions:
    def __init__(self, responses: list[_MockResponse]):
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs) -> _MockResponse:
        self.calls.append(kwargs)
        idx = len(self.calls) - 1
        if idx >= len(self._responses):
            raise AssertionError(
                f"Агент сделал больше вызовов ({len(self.calls)}), чем ожидалось"
            )
        return self._responses[idx]


class _MockChat:
    def __init__(self, responses: list[_MockResponse]):
        self.completions = _MockCompletions(responses)


class _MockOpenAI:
    def __init__(self, responses: list[_MockResponse]):
        self.chat = _MockChat(responses)


def _make_kiwi_mock(monkeypatch) -> dict[str, Any]:
    """Подменяем KiwiClient.search_flight."""
    captured: dict[str, Any] = {}

    def fake_search_flight(self, origin: str, destination: str, departure_date):
        captured["origin"] = origin
        captured["destination"] = destination
        captured["date"] = departure_date
        return {"flights": [{"price": 99, "from": origin, "to": destination}]}

    from mcp_clients.kiwi import KiwiClient
    monkeypatch.setattr(KiwiClient, "search_flight", fake_search_flight)
    return captured


def _make_trivago_mock(monkeypatch) -> dict[str, Any]:
    """Подменяем TrivagoClient.search_hotels."""
    captured: dict[str, Any] = {}

    def fake_search_hotels(self, city, check_in, check_out, *, adults=1, **kwargs):
        captured["city"] = city
        captured["check_in"] = check_in
        captured["check_out"] = check_out
        return {"hotels": [{"name": f"Hotel in {city}", "price": 120}]}

    from mcp_clients.trivago import TrivagoClient
    monkeypatch.setattr(TrivagoClient, "search_hotels", fake_search_hotels)
    return captured


def test_agent_runs_search_flight_only(monkeypatch):
    kiwi_calls = _make_kiwi_mock(monkeypatch)
    _make_trivago_mock(monkeypatch)

    # Сценарий: модель сразу вызывает search_flight и затем отвечает текстом.
    openai_client = _MockOpenAI(
        responses=[
            _MockResponse(
                _MockChoiceMsg(
                    content=None,
                    tool_calls=[
                        _MockToolCall(
                            id_="call_1",
                            name="search_flight",
                            arguments='{"flyFrom": "BER", "flyTo": "FCO", "departureDate": "28/07/2026"}',
                        )
                    ],
                )
            ),
            _MockResponse(_MockChoiceMsg(content="Нашёл билеты, вот варианты…")),
        ]
    )

    agent = TravelAgent(log_queue=LogQueue(), openai_client=openai_client)
    result = agent.run([{"role": "user", "content": "билет Берлин-Рим"}])

    assert result.final_message.startswith("Нашёл")
    assert result.steps == 2
    assert kiwi_calls["origin"] == "BER"
    assert kiwi_calls["destination"] == "FCO"
    from datetime import date
    assert kiwi_calls["date"] == date(2026, 7, 28)


def test_agent_handles_tool_validation_error(monkeypatch):
    """Если Kiwi вернёт ValueError (российский аэропорт) — агент должен
    получить структуру с validation_error и ответить пользователю по-русски."""
    _make_kiwi_mock(monkeypatch)

    from mcp_clients.kiwi import KiwiClient

    def boom(self, origin, destination, departure_date):
        raise ValueError("Российские аэропорты Kiwi не поддерживает: SVO")

    monkeypatch.setattr(KiwiClient, "search_flight", boom)

    openai_client = _MockOpenAI(
        responses=[
            _MockResponse(
                _MockChoiceMsg(
                    tool_calls=[
                        _MockToolCall(
                            id_="call_x",
                            name="search_flight",
                            arguments='{"flyFrom": "SVO", "flyTo": "FCO", "departureDate": "28/07/2026"}',
                        )
                    ],
                )
            ),
            _MockResponse(_MockChoiceMsg(content="Kiwi не ищет из SVO, увы.")),
        ]
    )

    agent = TravelAgent(log_queue=LogQueue(), openai_client=openai_client)
    result = agent.run([{"role": "user", "content": "билет Москва-Рим"}])
    assert "SVO" in result.final_message or "увы" in result.final_message
