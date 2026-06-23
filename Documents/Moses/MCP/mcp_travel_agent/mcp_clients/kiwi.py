"""Клиент Kiwi MCP для поиска авиабилетов.

Особенности (по факту проверки реального API):
- Endpoint: https://mcp.kiwi.com
- handshake через initialize → сохраняем mcp-session-id
- основной инструмент: search-flight
- параметры: flyFrom, flyTo, departureDate (формат YYYY-MM-DD)
- российские аэропорты не поддерживаются
- ответ приходит как SSE (text/event-stream)
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .base import MCPClient, MCPError


# IATA-коды российских аэропортов, которые Kiwi не поддерживает.
# Это не исчерпывающий список, но покрывает крупнейшие хабы, чтобы
# агент мог дать осмысленный отказ пользователю.
RU_AIRPORTS: set[str] = {
    "SVO",  # Москва Шереметьево
    "DME",  # Москва Домодедово
    "VKO",  # Москва Внуково
    "LED",  # Санкт-Петербург Пулково
    "AER",  # Адлер
    "OVB",  # Новосибирск Толмачёво
    "KZN",  # Казань
    "ROV",  # Ростов-на-Дону
    "SVX",  # Екатеринбург Кольцово
    "UFA",  # Уфа
    "KRR",  # Краснодар
    "VOG",  # Волгоград
    "CEK",  # Челябинск
    "OMS",  # Омск
    "MRV",  # Минеральные Воды
    "TJM",  # Тюмень
    "KJA",  # Красноярск
    "IKT",  # Иркутск
    "KHV",  # Хабаровск
    "VVO",  # Владивосток
    "YKS",  # Якутск
    "MMK",  # Мурманск
    "ARH",  # Архангельск
    "PKC",  # Петропавловск-Камчатский
    "GOJ",  # Нижний Новгород
    "EGO",  # Белгород
    "BQS",  # Благовещенск
}


class KiwiClient(MCPClient):
    name = "kiwi"
    endpoint = "https://mcp.kiwi.com"

    def search_flight(
        self,
        origin: str,
        destination: str,
        departure_date: date | str,
    ) -> dict[str, Any]:
        """Ищет рейсы origin → destination на указанную дату.

        :param origin: IATA-код аэропорта вылета (3 буквы, например BER)
        :param destination: IATA-код аэропорта прилёта
        :param departure_date: дата вылета (date или YYYY-MM-DD)
        :raises ValueError: если российский аэропорт
        :raises MCPError: при сетевых/JSON-RPC проблемах
        """
        origin = origin.strip().upper()
        destination = destination.strip().upper()

        if len(origin) != 3 or not origin.isalpha():
            raise ValueError(
                f"Нужен IATA-код аэропорта вылета, получено: {origin!r}"
            )
        if len(destination) != 3 or not destination.isalpha():
            raise ValueError(
                f"Нужен IATA-код аэропорта прилёта, получено: {destination!r}"
            )

        if origin in RU_AIRPORTS or destination in RU_AIRPORTS:
            blocked = origin if origin in RU_AIRPORTS else destination
            raise ValueError(
                f"Российские аэропорты Kiwi не поддерживает: {blocked}"
            )

        dep_str = self._normalize_date(departure_date)

        arguments = {
            "flyFrom": origin,
            "flyTo": destination,
            "departureDate": dep_str,
        }
        result = self.call_tool("search-flight", arguments)
        return result if isinstance(result, dict) else {"raw": result}

    @staticmethod
    def _normalize_date(value: date | str) -> str:
        # Kiwi ждёт dd/mm/yyyy (валидация на стороне сервера).
        if isinstance(value, date):
            return value.strftime("%d/%m/%Y")
        s = value.strip()
        from datetime import datetime as _dt
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return _dt.strptime(s, fmt).strftime("%d/%m/%Y")
            except ValueError:
                continue
        raise ValueError(
            f"Не удалось распознать дату: {value!r} "
            f"(ожидаю dd/mm/yyyy или YYYY-MM-DD)"
        )

    @staticmethod
    def is_russian_airport(iata: str) -> bool:
        return iata.strip().upper() in RU_AIRPORTS
