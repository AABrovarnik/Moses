"""OpenAI-агент с function calling и интеграцией MCP-клиентов.

Основной цикл:
1. История чата + system prompt → chat.completions.create(..., tools=...).
2. Если модель вернула tool_calls — выполняем через MCP-клиенты.
3. Результаты кладём в messages с role='tool'.
4. Повторяем, пока модель не вернёт финальный текст.
5. Каждый шаг пишем в LogQueue (для UI).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from mcp_clients.base import LogQueue
from mcp_clients.kiwi import KiwiClient
from mcp_clients.trivago import TrivagoClient

from .prompts import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS


# Загружаем .env один раз на старте модуля.
load_dotenv()


@dataclass
class AgentRunResult:
    """Что вернёт один запуск агента."""

    final_message: str
    history: list[dict[str, Any]] = field(default_factory=list)
    steps: int = 0  # сколько раз дёрнули модель


class TravelAgent:
    """Агент-туристический ассистент.

    Использование:
        agent = TravelAgent(log_queue=my_logs)
        result = agent.run([{"role": "user", "content": "..."}])
    """

    def __init__(
        self,
        log_queue: LogQueue | None = None,
        *,
        model: str | None = None,
        mcp_timeout: float | None = None,
        openai_client: OpenAI | None = None,
    ) -> None:
        self.logs = log_queue or LogQueue()
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY не задан. Проверь .env в корне проекта."
            )
        self.client = openai_client or OpenAI(api_key=api_key)
        self.mcp_timeout = mcp_timeout or float(os.environ.get("MCP_TIMEOUT", "30"))

        # Один экземпляр клиента на сессию — у Kiwi нужно сохранять
        # mcp-session-id между вызовами.
        self.kiwi = KiwiClient(log_queue=self.logs, timeout=self.mcp_timeout)
        self.trivago = TrivagoClient(log_queue=self.logs, timeout=self.mcp_timeout)
        # TODO: foursquare — добавить self.foursquare = FoursquareClient(...) когда включим.

    # --- публичный API --------------------------------------------------

    def run(self, history: list[dict[str, Any]]) -> AgentRunResult:
        """Один проход: берёт историю, возвращает финальный ответ + историю.

        Под «историей» — список сообщений OpenAI. Текущая реализация
        синхронная и не стримит промежуточные токены (для MVP
        Streamlit-чат это оптимально).
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
        ]

        steps = 0
        max_steps = 8  # защита от зацикливания
        while steps < max_steps:
            steps += 1
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            # Финальный ответ — нет tool_calls.
            if not msg.tool_calls:
                return AgentRunResult(
                    final_message=msg.content or "",
                    history=_append(messages, msg.model_dump(exclude_none=True)),
                    steps=steps,
                )

            # Иначе выполняем все tool_calls и кладём результаты в messages.
            messages = _append(messages, msg.model_dump(exclude_none=True))
            for call in msg.tool_calls:
                tool_result = self._dispatch_tool(call)
                messages = _append(
                    messages,
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": _safe_json(tool_result),
                    },
                )

        # Если вышли по лимиту шагов — попросим модель резюмировать.
        tail = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="none",
        )
        final = tail.choices[0].message.content or ""
        return AgentRunResult(
            final_message=final,
            history=_append(
                messages,
                {"role": "assistant", "content": final},
            ),
            steps=steps,
        )

    # --- маршрутизация инструментов -------------------------------------

    def _dispatch_tool(self, call: Any) -> dict[str, Any]:
        """Выполняет один tool_call и возвращает dict с результатом.

        Возвращаем dict, чтобы OpenAI смог сериализовать в JSON.
        При исключениях — возвращаем структуру с полем error,
        чтобы агент мог корректно отреагировать в ответе.
        """
        name = call.function.name
        try:
            arguments = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError:
            return {"error": f"Не удалось разобрать аргументы: {call.function.arguments}"}

        try:
            if name == "search_flight":
                from datetime import datetime as _dt
                origin = arguments.get("flyFrom", "").upper()
                destination = arguments.get("flyTo", "").upper()
                date_raw = arguments.get("departureDate", "")
                # Модель передаёт dd/mm/yyyy; принимаем и ISO на всякий случай.
                try:
                    flight_date = _dt.strptime(date_raw, "%d/%m/%Y").date()
                except ValueError:
                    flight_date = _dt.strptime(date_raw, "%Y-%m-%d").date()
                result = self.kiwi.search_flight(origin, destination, flight_date)
                return {"status": "ok", "data": result}

            if name == "search_hotel":
                from datetime import datetime as _dt
                city = arguments.get("city", "")
                check_in = _dt.strptime(arguments["check_in"], "%Y-%m-%d").date()
                check_out = _dt.strptime(arguments["check_out"], "%Y-%m-%d").date()
                result = self.trivago.search_hotels(city, check_in, check_out)
                return {"status": "ok", "data": result}

            # TODO: foursquare
            # if name == "search_places": ...

            return {"error": f"Неизвестный инструмент: {name}"}

        except ValueError as exc:
            # Наша валидация (российские аэропорты, плохие даты и т.п.)
            return {"status": "validation_error", "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


# --- helpers -------------------------------------------------------------


def _append(messages: list[dict[str, Any]], msg: dict[str, Any]) -> list[dict[str, Any]]:
    out = list(messages)
    out.append(msg)
    return out


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return json.dumps({"raw": repr(value)}, ensure_ascii=False)
