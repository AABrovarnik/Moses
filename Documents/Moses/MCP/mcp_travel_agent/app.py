"""Точка входа Streamlit: левая колонка — чат, правая — логи MCP."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from agent.openai_agent import TravelAgent
from mcp_clients.base import LogQueue
from ui.chat import render_chat
from ui.logs import render_logs


load_dotenv()


st.set_page_config(
    page_title="MCP Travel Agent",
    page_icon="✈️",
    layout="wide",
)


def _get_agent() -> TravelAgent:
    """Создаём агента один раз на сессию Streamlit.

    Сессия у Streamlit переживает rerun, поэтому держим агента
    в session_state — иначе mcp-session-id Kiwi сбрасывался бы
    при каждом rerun.
    """
    if "agent" not in st.session_state:
        log_queue = LogQueue()
        agent = TravelAgent(log_queue=log_queue)
        # Подтянем существующие логи (если были) в session_state.
        st.session_state["logs"] = [ev.as_dict() for ev in log_queue.all()]
        log_queue.clear()
        st.session_state["agent"] = agent
    return st.session_state["agent"]


def main() -> None:
    st.title("✈️ Туристический ассистент")
    st.caption(
        "AI-агент через OpenAI-совместимый API (по умолчанию — локальный Ollama "
        "с Qwen 2.5 7B). Ищет авиабилеты через Kiwi MCP и отели через Trivago MCP. "
        "Отвечает на русском."
    )

    # Достаточно наличия ЛЮБОГО из признаков: реальный ключ (OpenAI cloud)
    # или base_url (Ollama/OpenRouter и т.п.).
    has_llm = bool(
        os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_BASE_URL")
    )
    if not has_llm:
        st.error(
            "Не настроен провайдер LLM. Скопируй `.env.example` в `.env` "
            "и подставь OPENAI_BASE_URL/OPENAI_API_KEY/OPENAI_MODEL. "
            "По умолчанию — локальный Ollama (см. README)."
        )
        return

    # Предупреждение о холодном старте локальной модели.
    if os.environ.get("OPENAI_BASE_URL"):
        st.info(
            "ℹ️ Первый запрос к локальной модели может занять 10–30 секунд "
            "(cold start). Дальнейшие ответы — обычно 2–5 секунд."
        )

    agent = _get_agent()

    chat_col, logs_col = st.columns([2, 1])
    with chat_col:
        render_chat(agent)
    with logs_col:
        render_logs()


if __name__ == "__main__":
    main()
