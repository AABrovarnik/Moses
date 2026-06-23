"""Sanity-проверки Trivago-клиента без сетевых вызовов."""

from __future__ import annotations

from datetime import date

import pytest

from mcp_clients.trivago import TrivagoClient


def test_normalize_date_from_date():
    assert TrivagoClient._normalize_date(date(2026, 6, 28)) == "2026-06-28"


def test_normalize_date_from_iso():
    assert TrivagoClient._normalize_date("2026-06-28") == "2026-06-28"


def test_normalize_date_from_dd_mm_yyyy():
    assert TrivagoClient._normalize_date("28/06/2026") == "2026-06-28"


def test_normalize_date_invalid():
    with pytest.raises(ValueError):
        TrivagoClient._normalize_date("завтра")


def test_search_hotels_rejects_cyrillic():
    client = TrivagoClient()
    with pytest.raises(ValueError) as exc:
        client.search_hotels("Прага", "2026-07-10", "2026-07-12")
    assert "только на английском" in str(exc.value)


def test_search_hotels_rejects_departure_before_arrival():
    client = TrivagoClient()
    with pytest.raises(ValueError):
        client.search_hotels("Prague", "2026-07-12", "2026-07-10")


def test_search_hotels_rejects_empty_city():
    client = TrivagoClient()
    with pytest.raises(ValueError):
        client.search_hotels("   ", "2026-07-10", "2026-07-12")
