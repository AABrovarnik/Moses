"""Полу-реальный e2e: реальные Kiwi/Trivago + мок LLM.

Нужен, потому что OpenAI блокирует запросы с территории RU (403).
Этот тест:
1. Подключается к НАСТОЯЩИМ Kiwi и Trivago MCP.
2. Прогоняет сценарии через реальный TravelAgent.run, но с моком OpenAI.
3. Мок имитирует: модель вызывает tool_call с правильными аргументами,
   а на втором шаге возвращает финальный текст.
4. В логе видно, что MCP-вызовы прошли, ответы пришли.

Запускать:
    MCP_LIVE=1 python -m pytest tests/test_semi_e2e.py -v -s
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import pytest

from agent.openai_agent import AgentRunResult, TravelAgent
from mcp_clients.base import LogQueue


pytestmark = pytest.mark.skipif(
    os.environ.get("MCP_LIVE") != "1",
    reason="MCP_LIVE!=1",
)


# --- мок OpenAI ---------------------------------------------------------


class _MockFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class _MockToolCall:
    def __init__(self, id_: str, name: str, arguments: str):
        self.id = id_
        self.function = _MockFunction(name, arguments)


class _MockChoiceMsg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none=True):
        out: dict[str, Any] = {"role": "assistant"}
        if self.content is not None:
            out["content"] = self.content
        if self.tool_calls:
            out["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in self.tool_calls
            ]
        return out


class _MockChoice:
    def __init__(self, m):
        self.message = m


class _MockResponse:
    def __init__(self, m):
        self.choices = [_MockChoice(m)]


class _MockCompletions:
    def __init__(self, scripts):
        self._scripts = list(scripts)
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw)
        if not self._scripts:
            # Дальнейшие шаги — финальный текст «от агента» без tool_calls.
            return _MockResponse(_MockChoiceMsg(content="(продолжаю)"))
        kind = self._scripts.pop(0)
        return _MockResponse(_MockChoiceMsg(**kind))


class _MockChat:
    def __init__(self, scripts):
        self.completions = _MockCompletions(scripts)


class _MockOpenAI:
    def __init__(self, scripts):
        self.chat = _MockChat(scripts)


# --- сценарии -----------------------------------------------------------


def _next_friday() -> date:
    d = date.today()
    delta = (4 - d.weekday()) % 7
    if delta == 0:
        delta = 7
    return d + timedelta(days=delta)


def _next_weekend() -> tuple[date, date]:
    d = date.today()
    wd = d.weekday()
    if wd == 5:
        sat = d
    elif wd == 6:
        sat = d
    else:
        sat = d + timedelta(days=(5 - wd) or 7)
    return sat, sat + timedelta(days=2)


def test_scenario_berlin_to_rome():
    dep = _next_friday().strftime("%d/%m/%Y")
    scripts = [
        {
            "content": None,
            "tool_calls": [
                _MockToolCall("c1", "search_flight",
                              f'{{"flyFrom":"BER","flyTo":"FCO","departureDate":"{dep}"}}'),
            ],
        },
        {"content": f"Нашёл билеты BER-FCO на {dep}. Подробности в результатах Kiwi."},
    ]
    agent = TravelAgent(
        log_queue=LogQueue(),
        openai_client=_MockOpenAI(scripts),
    )
    result = agent.run([{"role": "user", "content": "Билет Берлин-Рим на пятницу"}])
    print("\n>>> FINAL:", result.final_message)
    assert "Берлин" in result.final_message or "Нашёл" in result.final_message
    assert result.steps == 2


def test_scenario_prague_hotel():
    arr, dep = _next_weekend()
    scripts = [
        {
            "content": None,
            "tool_calls": [
                _MockToolCall("c1", "search_hotel",
                              f'{{"city":"Prague","check_in":"{arr}","check_out":"{dep}"}}'),
            ],
        },
        {"content": f"Нашёл отели в Праге на {arr}-{dep}."},
    ]
    agent = TravelAgent(
        log_queue=LogQueue(),
        openai_client=_MockOpenAI(scripts),
    )
    result = agent.run([{"role": "user", "content": "Отель в Праге на выходные"}])
    print("\n>>> FINAL:", result.final_message)
    assert "Праг" in result.final_message or "отел" in result.final_message


def test_scenario_full_trip_to_vienna():
    arr = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
    dep = (date.today() + timedelta(days=16)).strftime("%Y-%m-%d")
    dep_flight = (date.today() + timedelta(days=14)).strftime("%d/%m/%Y")
    scripts = [
        {
            "content": None,
            "tool_calls": [
                _MockToolCall("c1", "search_flight",
                              f'{{"flyFrom":"SVO","flyTo":"VIE","departureDate":"{dep_flight}"}}'),
            ],
        },
        {
            "content": None,
            "tool_calls": [
                _MockToolCall("c2", "search_hotel",
                              f'{{"city":"Vienna","check_in":"{arr}","check_out":"{dep}"}}'),
            ],
        },
        {"content": "Из Москвы Kiwi не ищет, но отели в Вене нашёл."},
    ]
    agent = TravelAgent(
        log_queue=LogQueue(),
        openai_client=_MockOpenAI(scripts),
    )
    result = agent.run([{"role": "user", "content": "Поездка в Вену через 2 недели"}])
    print("\n>>> FINAL:", result.final_message)
    # В этом сценарии ожидаем 3 шага: flight, hotel, summary.
    assert result.steps == 3
