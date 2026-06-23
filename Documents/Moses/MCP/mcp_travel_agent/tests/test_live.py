"""Smoke-тесты против реальных MCP-серверов.

Эти тесты НЕ мокают ничего — они ходят в сеть. По умолчанию пропускаются,
если переменная окружения MCP_LIVE=1 не выставлена. Запускать так:

    MCP_LIVE=1 python -m pytest tests/test_live.py -v -s

Проверяют:
- Kiwi MCP доступен и возвращает билеты
- Trivago MCP доступен и возвращает отели
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest

from mcp_clients.kiwi import KiwiClient
from mcp_clients.trivago import TrivagoClient


pytestmark = pytest.mark.skipif(
    os.environ.get("MCP_LIVE") != "1",
    reason="живые MCP-вызовы отключены (MCP_LIVE!=1)",
)


def test_kiwi_real_search_flight():
    client = KiwiClient(timeout=45.0)
    # Берём дату через 30 дней, чтобы попасть в доступное окно.
    target = date.today() + timedelta(days=30)
    result = client.search_flight("BER", "FCO", target)
    assert isinstance(result, dict)
    # Структура ответа у Kiwi нестабильна между версиями, проверяем
    # только что что-то вернулось без ошибки.
    assert result, "Kiwi вернул пустой результат"


def test_trivago_real_search_hotels():
    client = TrivagoClient(timeout=45.0)
    check_in = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
    check_out = (date.today() + timedelta(days=16)).strftime("%Y-%m-%d")
    result = client.search_hotels("Prague", check_in, check_out)
    assert isinstance(result, dict)
    assert result, "Trivago вернул пустой результат"
