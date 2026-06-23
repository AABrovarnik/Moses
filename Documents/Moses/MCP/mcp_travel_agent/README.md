# MCP Travel Agent

AI-агент-туристический ассистент: ищет авиабилеты через **Kiwi MCP**
и отели через **Trivago MCP**. Интерфейс — Streamlit, две колонки
(чат слева, логи MCP справа), ответы на русском.

## Запуск

```bash
cd mcp_travel_agent
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Впиши свой OPENAI_API_KEY в .env

streamlit run app.py
```

Откроется вкладка `http://localhost:8501`.

## Переменные окружения

| Имя | Назначение |
|---|---|
| `OPENAI_API_KEY` | ключ OpenAI |
| `OPENAI_MODEL` | модель (по умолчанию `gpt-4o-mini`) |
| `MCP_TIMEOUT` | таймаут HTTP, сек (по умолчанию `30`) |
| `FOURSQUARE_API_KEY` | опционально, для Foursquare MCP (выключено в MVP) |

## Структура

```
app.py                 # точка входа Streamlit
agent/                 # OpenAI агент: цикл tool-use, схемы, промпты
mcp_clients/           # JSON-RPC клиенты к MCP-серверам
ui/                    # компоненты Streamlit (чат + логи)
tests/                 # сценарии из задания + sanity-проверки
```

## Как включить Foursquare

1. Получи API Key на https://foursquare.com/developers.
2. Положи его в `.env`: `FOURSQUARE_API_KEY=...`.
3. Реализуй функцию `search_places` в `mcp_clients/foursquare.py`
   (заготовка с TODO уже есть).
4. Добавь инструмент в `agent/tools.py` и подключи в
   `agent/openai_agent.py` (там комментарий `TODO: foursquare`).

## Зачем `Posts/`

В корне репозитория рядом с этим проектом лежит папка `Posts/` —
там хранятся ТЗ, отчёты и промпты по проекту.
