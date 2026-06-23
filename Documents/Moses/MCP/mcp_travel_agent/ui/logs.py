"""Правая колонка — лента логов MCP."""

from __future__ import annotations

import datetime as _dt
import json

import streamlit as st


_KIND_BADGE = {
    "init": "🟢 init",
    "request": "➡️ request",
    "response": "⬅️ response",
    "error": "🔴 error",
}


def render_logs() -> None:
    st.subheader("Логи MCP")

    logs = st.session_state.get("logs", [])

    if not logs:
        st.caption("Логи появятся здесь после первого вызова агента.")
        return

    # Контейнер с фиксированной высотой и прокруткой.
    container = st.container(height=600)
    with container:
        for entry in logs:
            ts = _dt.datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S")
            server = entry.get("server", "?")
            kind = entry.get("kind", "?")
            method = entry.get("method")
            badge = _KIND_BADGE.get(kind, kind)

            header = f"`{ts}` **{server}** {badge}"
            if method:
                header += f" — `{method}`"

            with st.expander(header, expanded=False):
                details = entry.get("details") or {}
                st.code(
                    json.dumps(details, ensure_ascii=False, indent=2, default=str),
                    language="json",
                )
