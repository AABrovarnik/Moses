"""Левая колонка — чат с агентом."""

from __future__ import annotations

from typing import Iterable

import streamlit as st

from agent.openai_agent import AgentRunResult, TravelAgent


def render_chat(agent: TravelAgent) -> None:
    """Рисует историю чата и поле ввода, возвращает выбранное действие."""
    st.subheader("Чат с турагентом")

    history = st.session_state.setdefault("chat_history", [])
    logs = st.session_state.setdefault("logs", [])

    # Кнопки сверху
    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("Очистить чат", use_container_width=True):
            st.session_state["chat_history"] = []
            st.session_state["logs"] = []
            st.rerun()

    # История
    _render_history(history)

    # Поле ввода
    prompt = st.chat_input("Например: Найди билет из Берлина в Рим на следующую пятницу")
    if prompt:
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("_Думаю..._")
            try:
                result: AgentRunResult = agent.run(_strip_system(history))
            except Exception as exc:  # noqa: BLE001
                placeholder.error(f"Ошибка агента: {exc}")
                return

            placeholder.markdown(result.final_message or "_пустой ответ_")
            history.append({"role": "assistant", "content": result.final_message})

        # Подтянуть логи из общего LogQueue агента в session_state.
        _sync_logs(agent, logs)
        st.rerun()


def _render_history(history: Iterable[dict]) -> None:
    """Рисует сообщения сверху вниз. Последнее сообщение пользователя
    рисуется отдельно — его мы перерисуем после ввода."""
    msgs = list(history)
    for m in msgs[:-1]:
        with st.chat_message(m["role"]):
            st.markdown(m.get("content") or "")


def _strip_system(history: list[dict]) -> list[dict]:
    """Отдаём агенту только user/assistant/tool сообщения."""
    return [m for m in history if m.get("role") in {"user", "assistant", "tool"}]


def _sync_logs(agent: TravelAgent, target: list[dict]) -> None:
    """Копирует события из LogQueue агента в session_state для UI."""
    events = agent.logs.all()
    if not events:
        return
    for ev in events:
        target.append(ev.as_dict())
    # Чтобы не дублировать — после копирования чистим LogQueue агента.
    agent.logs.clear()
