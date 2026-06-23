"""Клиент Trivago MCP для поиска отелей.

Особенности (по факту проверки реального API):
- Endpoint: https://mcp.trivago.com/mcp
- Инструмент: trivago-accommodation-search
  (в ранних версиях требовался двухшаговый suggestions → search,
  сейчас API принимает query напрямую).
- Параметры: query (город на английском), arrival, departure (YYYY-MM-DD),
  adults, country (ISO-2), currency и т.д.
- Названия городов — только на английском (агент конвертирует).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .base import MCPClient


class TrivagoClient(MCPClient):
    name = "trivago"
    endpoint = "https://mcp.trivago.com/mcp"

    def search_hotels(
        self,
        city: str,
        check_in: date | str,
        check_out: date | str,
        *,
        adults: int = 1,
        country: str = "DE",
        currency: str = "EUR",
    ) -> dict[str, Any]:
        """Ищет отели в городе на заданные даты.

        :param city: название города на английском (например "Prague")
        :param check_in: дата заезда (date или YYYY-MM-DD)
        :param check_out: дата выезда
        :param adults: количество взрослых
        :param country: ISO-2 код страны рынка (DE, US, ...). Дефолт DE.
        :param currency: ISO-4217 код валюты. Дефолт EUR.
        """
        city_en = city.strip()
        if not city_en:
            raise ValueError("Название города пустое")
        if any(ord(ch) > 127 for ch in city_en):
            raise ValueError(
                f"Trivago принимает названия городов только на английском, "
                f"получено: {city_en!r}"
            )

        arrival = self._normalize_date(check_in)
        departure = self._normalize_date(check_out)

        if departure <= arrival:
            raise ValueError(
                f"Дата выезда ({departure}) должна быть позже даты заезда ({arrival})"
            )

        arguments = {
            "query": city_en,
            "arrival": arrival,
            "departure": departure,
            "adults": adults,
            "country": country,
            "currency": currency,
        }
        result = self.call_tool("trivago-accommodation-search", arguments)
        return result if isinstance(result, dict) else {"raw": result}

    @staticmethod
    def _normalize_date(value: date | str) -> str:
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        s = value.strip()
        from datetime import datetime as _dt
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return _dt.strptime(s, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(
            f"Не удалось распознать дату: {value!r} "
            f"(ожидаю YYYY-MM-DD или dd/mm/yyyy)"
        )
