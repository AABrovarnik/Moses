"""End-to-end сценарий: реальный LLM (Ollama/OpenAI) + реальные Kiwi/Trivago MCP.

Запускать вручную (по умолчанию skip):
    LLM_E2E=1 MCP_LIVE=1 python -m pytest tests/test_full_e2e.py -v -s

Гоняет 4 сценария из задания и пишет ответы в stdout/логи.
"""

from __future__ import annotations

import os

import pytest

from agent.openai_agent import TravelAgent
from mcp_clients.base import LogQueue


pytestmark = pytest.mark.skipif(
    os.environ.get("LLM_E2E") != "1" or os.environ.get("MCP_LIVE") != "1",
    reason="end-to-end требует LLM_E2E=1 и MCP_LIVE=1",
)


SCENARIOS = [
    "Найди билет из Berlin в Rome на следующую пятницу.",
    "Найди недорогой отель в Prague на ближайшие выходные.",
    "Найди билет и отель для поездки в Vienna через две недели.",
    "Подбери поездку в Barcelona на 3 дня.",
    "Хочу слетать из Москвы в Стамбул на следующей неделе.",  # отказ по RU
]


@pytest.mark.parametrize("query", SCENARIOS)
def test_scenario(query: str) -> None:
    agent = TravelAgent(log_queue=LogQueue())
    result = agent.run([{"role": "user", "content": query}])
    print(f"\n>>> USER: {query}")
    print(f">>> ASSISTANT:\n{result.final_message}\n")
    assert result.final_message, "агент вернул пустой ответ"
    assert result.steps >= 1
