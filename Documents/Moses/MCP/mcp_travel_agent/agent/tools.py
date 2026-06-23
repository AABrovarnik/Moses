"""Схемы инструментов (function calling) для OpenAI.

Формат — OpenAI tools/function calling. Имена и описания
специально говорят модели, что:
- в city для отеля — ТОЛЬКО английское название,
- даты для билета — dd/mm/yyyy,
- аэропорты — IATA-коды.

Это дублирует часть system prompt, но function-calling схема
надёжнее: модель видит её каждый раз при вызове инструмента.
"""

from __future__ import annotations


TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_flight",
            "description": (
                "Поиск авиабилетов через Kiwi MCP. "
                "Возвращает список рейсов с ценами. "
                "Российские аэропорты Kiwi не поддерживает — "
                "если пользователь хочет вылететь из RU, не вызывай, "
                "а сообщи ему об ограничении."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "flyFrom": {
                        "type": "string",
                        "description": (
                            "IATA-код аэропорта вылета, 3 латинские буквы. "
                            "Примеры: BER (Berlin), FCO (Rome Fiumicino), "
                            "PRG (Prague). НЕ передавай название города."
                        ),
                    },
                    "flyTo": {
                        "type": "string",
                        "description": (
                            "IATA-код аэропорта прилёта, 3 латинские буквы."
                        ),
                    },
                    "departureDate": {
                        "type": "string",
                        "description": (
                            "Дата вылета СТРОГО в формате dd/mm/yyyy. "
                            "Пример: 28/07/2026."
                        ),
                    },
                },
                "required": ["flyFrom", "flyTo", "departureDate"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotel",
            "description": (
                "Поиск отелей через Trivago MCP. "
                "Возвращает список отелей с ценами."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": (
                            "Название города ТОЛЬКО на английском языке, "
                            "на латинице. Примеры: Berlin, Prague, Rome, "
                            "Barcelona, Vienna. Кириллицу НЕ передавай."
                        ),
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Дата заезда в формате YYYY-MM-DD.",
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Дата выезда в формате YYYY-MM-DD.",
                    },
                },
                "required": ["city", "check_in", "check_out"],
                "additionalProperties": False,
            },
        },
    },
    # TODO: foursquare — раскомментировать, когда будет готов клиент.
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "search_places",
    #         "description": "Поиск мест/достопримечательностей через Foursquare.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "query": {"type": "string", "description": "Что ищем"},
    #                 "near": {"type": "string", "description": "Город/точка на английском"},
    #                 "limit": {"type": "integer", "description": "Сколько результатов"},
    #             },
    #             "required": ["query", "near"],
    #         },
    #     },
    # },
]
