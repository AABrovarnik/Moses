"""Sanity-проверки Kiwi-клиента без сетевых вызовов."""

from __future__ import annotations

from datetime import date

import pytest

from mcp_clients.kiwi import KiwiClient


def test_normalize_date_from_date():
    assert KiwiClient._normalize_date(date(2026, 6, 28)) == "28/06/2026"


def test_normalize_date_from_iso_string():
    assert KiwiClient._normalize_date("2026-06-28") == "28/06/2026"


def test_normalize_date_from_dd_mm_yyyy():
    assert KiwiClient._normalize_date("28/06/2026") == "28/06/2026"


def test_normalize_date_invalid():
    with pytest.raises(ValueError):
        KiwiClient._normalize_date("не дата")


def test_is_russian_airport_true():
    assert KiwiClient.is_russian_airport("SVO")
    assert KiwiClient.is_russian_airport("dme")  # case-insensitive


def test_is_russian_airport_false():
    assert not KiwiClient.is_russian_airport("BER")
    assert not KiwiClient.is_russian_airport("FCO")


def test_search_flight_rejects_cyrillic_origin():
    client = KiwiClient()
    with pytest.raises(ValueError):
        client.search_flight("Берлин", "FCO", date(2026, 6, 28))


def test_search_flight_rejects_russian_airport():
    client = KiwiClient()
    with pytest.raises(ValueError) as exc:
        client.search_flight("SVO", "FCO", date(2026, 6, 28))
    assert "Kiwi не поддерживает" in str(exc.value)


def test_search_flight_rejects_short_iata():
    client = KiwiClient()
    with pytest.raises(ValueError):
        client.search_flight("BERLIN", "FCO", date(2026, 6, 28))
