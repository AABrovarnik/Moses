"""Заготовка клиента Foursquare MCP.

В MVP отключён. Чтобы включить:
1. Получи API Key на https://foursquare.com/developers (Create App).
2. Положи ключ в .env: FOURSQUARE_API_KEY=...
3. Реализуй метод search_places(...) ниже по контракту из задания.
4. Добавь описание инструмента в agent/tools.py и подключи
   в agent/openai_agent.py (там есть TODO: foursquare).

Контракт вызова (из задания):
    POST https://gateway.pipeworx.io/foursquare/mcp
    {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_places",
            "arguments": {
                "query": "museum",
                "near": "Shanghai",
                "limit": 5,
                "_apiKey": "<token>"
            }
        },
        "id": 1
    }

Токен передаётся ВНУТРИ аргументов, не в заголовке Authorization.
"""

from __future__ import annotations

import os
from typing import Any

from .base import MCPClient


class FoursquareClient(MCPClient):
    name = "foursquare"
    endpoint = "https://gateway.pipeworx.io/foursquare/mcp"

    def __init__(self, *args, api_key: str | None = None, **kwargs) -> None:
        # В extra_headers намеренно НЕ кладём ключ — токен уходит
        # внутри arguments._apiKey по контракту.
        super().__init__(*args, **kwargs)
        self.api_key = api_key or os.environ.get("FOURSQUARE_API_KEY", "")

    def search_places(
        self,
        query: str,
        near: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Поиск мест рядом с городом/точкой.

        :param query: что ищем ("museum", "cafe", "park"...)
        :param near: город или координаты (на английском)
        :param limit: сколько результатов вернуть
        """
        if not self.api_key:
            raise RuntimeError(
                "FOURSQUARE_API_KEY не задан. См. README.md, раздел "
                "'Как включить Foursquare'."
            )

        arguments = {
            "query": query,
            "near": near,
            "limit": limit,
            "_apiKey": self.api_key,
        }
        # TODO: реализовать. Когда будет готово — раскомментировать:
        # return self.call_tool("search_places", arguments)
        raise NotImplementedError(
            "Foursquare-клиент в MVP отключён. Реализация — TODO."
        )
