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
# .env уже сконфигурирован под локальный Ollama — см. раздел "Провайдер LLM".

streamlit run app.py
```

Откроется вкладка `http://localhost:8501`.

## Провайдер LLM

Агент работает с **любым OpenAI-совместимым endpoint'ом** — выбор
через `.env`. По умолчанию — локальный Ollama, у которого нет
региональных ограничений (в отличие от OpenAI cloud, который
блокирует запросы с территории РФ кодом `403 unsupported_country_region_territory`).

### Вариант 1: локальный Ollama (рекомендуется для РФ) — по умолчанию

1. Установи [Ollama](https://ollama.com/download).
2. Скачай модель:
   ```bash
   ollama pull qwen2.5:14b
   ```
   Это 9.0 GB; первая загрузка занимает несколько минут.
3. Убедись, что сервис запущен: `ollama serve` (или просто открой
   приложение Ollama — оно стартует сервис автоматически).
4. В `.env` оставь строки как в `.env.example`:
   ```dotenv
   OPENAI_BASE_URL=http://127.0.0.1:11434/v1
   OPENAI_MODEL=qwen2.5:14b
   OPENAI_API_KEY=ollama
   ```
   Ollama не валидирует ключ — `ollama` это просто заглушка
   для openai-sdk.
5. Запускай `streamlit run app.py`.

> **Первый запрос** к локальной модели занимает 10–30 секунд
> (cold start: модель грузится в RAM). Дальнейшие ответы —
> обычно 2–5 секунд.

### Вариант 2: OpenAI cloud (если есть VPN в разрешённый регион)

Закомментируй `OPENAI_BASE_URL` в `.env`, подставь свой ключ и модель:

```dotenv
# OPENAI_BASE_URL=
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### Вариант 3: OpenRouter (облачные LLM с оплатой по токенам)

```dotenv
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-...
OPENAI_MODEL=qwen/qwen-2.5-72b-instruct
```

## Переменные окружения

| Имя | Назначение |
|---|---|
| `OPENAI_BASE_URL` | базовый URL OpenAI-совместимого API (например, Ollama или OpenRouter). Пусто = OpenAI cloud. |
| `OPENAI_API_KEY` | ключ API. Для Ollama — любая непустая строка (например, `ollama`). |
| `OPENAI_MODEL` | модель (по умолчанию `qwen2.5:14b` для Ollama, `gpt-4o-mini` для OpenAI) |
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
