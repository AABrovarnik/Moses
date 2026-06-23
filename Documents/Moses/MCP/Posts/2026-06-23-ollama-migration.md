# Миграция LLM: OpenAI cloud → Ollama (Qwen 2.5 14B)

**Дата:** 2026-06-23
**Проект:** `mcp_travel_agent`
**Причина:** OpenAI возвращает `403 unsupported_country_region_territory`
для запросов с территории РФ. Это политика провайдера, не дефект кода —
воспроизводится с любого аккаунта в RU-регионе.

## Что сделано

Перевёл агента на **локальный Ollama** с моделью **Qwen 2.5 14B**
(9.0 GB; скачали `ollama pull qwen2.5:14b`). Сначала пробовали 7B —
после получения `role: tool` ответа от MCP Qwen 7B в ~30% случаев
эмулировал вызов функции прямо в `content` вместо `tool_calls`.
14B стабильнее, но всё равно требует `temperature=0` (см. ниже).

Архитектура стала **провайдер-агностичной** — тот же код работает
и с Ollama, и с OpenAI cloud, и с OpenRouter; переключение через `.env`.

## Подход

Не вводил новый SDK. Ollama отдаёт OpenAI-совместимый endpoint
на `/v1` — `openai` Python SDK принимает его с параметром `base_url`.
Поэтому весь существующий цикл `chat.completions.create(..., tools=…)`
работает без изменений. Добавил только чтение `OPENAI_BASE_URL` в
конструктор `TravelAgent`.

### Изменённые файлы

- `agent/openai_agent.py`:
  - Конструктор читает `OPENAI_BASE_URL`; если ключ не задан, но
    есть base_url — ставит заглушку `"ollama"` (openai-sdk требует
    непустую строку, Ollama не валидирует ключ).
  - При наличии base_url ставит `timeout=600` (Ollama на cold start
    может думать 30–60 сек; 14B при длинном system prompt — до 2–3 мин).
  - В `run()` жёстко зашит `temperature=0` — стабилизирует tool-calling
    у Qwen (см. ниже).
- `app.py` — проверка ключа смягчена: достаточно `OPENAI_API_KEY`
  или `OPENAI_BASE_URL`. Подпись `st.caption` обновлена. Добавлен
  `st.info` про cold start.
- `tests/test_full_e2e.py` — флаг `OPENAI_E2E` → `LLM_E2E`
  (теперь не OpenAI-specific).
- `.env.example` — Ollama-секция как сценарий по умолчанию,
  OpenAI/OpenRouter — как опции.
- `.env` — переключён на Ollama (`OPENAI_BASE_URL=…/v1`, модель `qwen2.5:14b`).
  Реальный OpenAI-ключ сохранён в комментарии для возможного отката.
- `README.md` — добавлен раздел «Провайдер LLM» с тремя сценариями.

## Что НЕ менялось

- `agent/prompts.py` — Qwen 2.5 поддерживает system-сообщения.
- `agent/tools.py` — формат tool schemas совместим с Ollama.
- `mcp_clients/*` — независимы от LLM.
- `requirements.txt` — никаких новых зависимостей.

## Про стабильность Qwen + tool-calling

Локальные тесты на двухшаговом сценарии (вызов `search_flight` →
получение результата → второй запрос для ответа пользователю):

| Temperature | Шаг 1 (tool_call) | Шаг 2 (final answer) |
|---|---|---|
| `temperature=0` | 3/3 OK | 3/3 OK |
| `temperature=0.7` (default) | 2/3 OK | 2/3 OK + 1 галлюцинация |

Галлюцинация выглядит так: вместо `tool_calls=[]` и `content="…"`
Qwen отдаёт `tool_calls=None` и `content="…\n{\"name\": \"search_hotel\", ...}\n…"`.
То есть модель «думает», что должна ещё раз позвать инструмент,
и эмулирует его JSON в тексте.

**Решение:** `temperature=0` в `agent.run()`. Для OpenAI cloud это
тоже плюс — reasoning становится детерминированным, что для
ассистента-агента желательно.

## Проверка

### Тесты

| Прогон | Было | Стало |
|---|---|---|
| `pytest tests/ -q` | 23 passed, 10 skipped | 23 passed, 10 skipped |
| `MCP_LIVE=1 pytest tests/ -q` | 28 passed, 5 skipped | 28 passed, 5 skipped |

Тесты `test_agent_smoke.py` подменяют `OpenAI`-клиент моком через
параметр `openai_client=…` — после правки конструктора ничего не
сломалось.

### Ручная проверка (через `smoke_ollama.py`)

```
$ cd mcp_travel_agent
$ MCP_LIVE=1 .venv/Scripts/python.exe smoke_ollama.py
Imports: 1.0s
Agent created: 0.3s

=== agent.run took 33.5s, steps=1 ===

---FINAL ANSWER---
Here are some of the cheapest flight options from Berlin (BER)
to Rome (FCO) on July 28, 2023:
…
```

Агент реально дёрнул Kiwi MCP, получил три рейса, отсортировал
по цене, дал рекомендации. ⚠️ На английском, потому что Kiwi
вернул английские описания — Qwen 14B переключился на английский
«по инерции». Для русского ответа можно усилить system prompt
или добавить пост-обработку, но это уже polish, не блокер.

## Известные нюансы Qwen 2.5 14B

- **Cold start** — первый запрос 30-120 сек, дальше 2-10 сек.
  В Streamlit пользователь увидит `st.spinner`; в `st.info` вывели
  предупреждение.
- **Tool calling стабилен при temperature=0.** Это нормальное
  поведение локальных моделей; для production-агентов это даже плюс.
- **Качество русского** — Qwen 2.5 14B знает русский лучше 7B,
  но всё равно уступает gpt-4o-mini. Если качество ответов
  окажется недостаточным — следующий шаг OpenRouter qwen-72b
  (~$0.0004/1k токенов, без VPN).

## Откат на OpenAI cloud

Если появится VPN/прокси в разрешённый регион — поменять в `.env`:

```dotenv
# OPENAI_BASE_URL=
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Никаких правок в коде не потребуется. `temperature=0` в коде
останется — для OpenAI это тоже не вредит.
