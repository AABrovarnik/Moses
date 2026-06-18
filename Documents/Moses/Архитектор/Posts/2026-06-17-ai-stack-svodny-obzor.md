# Сводный обзор: стек для AI-агентной разработки в РФ (2026)

**Дата:** 17.06.2026
**Основан на:** обзорах [vibe-кодинг](2026-06-17-vibe-coding-obzor.md) и [мультиагенты/MCP/swarm](2026-06-17-multiagent-mcp-swarm-obzor.md)

---

## 0. Пояснение про Ollama как «launch Claude»-прокси

В запросе упомянута конструкция вида `ollama launch claude --model minimax-m3:cloud`. **Такой команды в Ollama CLI не существует** — это вымышленный синтаксис. Однако **идея реальна и реализуется так:**

```bash
# Запуск Ollama как локального OpenAI-compatible сервера
ollama serve                    # поднимает http://localhost:11434

# Локальные модели
ollama run qwen3-coder:30b      # Qwen3-Coder локально
ollama run deepseek-v3:67b      # DeepSeek-V3 локально

# Ollama как прокси к облачным провайдерам (через OpenAI-compatible API)
# В Cline / LangGraph / Claude Agent указывается:
#   Base URL:  http://localhost:11434/v1
#   API Key:   ollama (или реальный ключ, пересылаемый через proxy)
```

**Что это даёт:**
- **Единый endpoint** для Cline, LangGraph, Claude Code, любого MCP-клиента.
- **Единая авторизация** — Ollama-сервер сам решает, какие модели локальные, какие проксируются.
- **Совместимость с MCP** — Ollama-сервер совместим с MCP через community-адаптеры (ollama-mcp-bridge).
- **On-prem fallback** — если облачный провайдер недоступен, агент автоматически переключается на локальную модель.

**Реальные модели в Ollama-экосистеме (на середину 2026):**
- `qwen3-coder:30b` (≈18 GB VRAM)
- `qwen3-coder:480b-cloud` (облачная, через провайдера)
- `deepseek-v3:67b` (≈40 GB VRAM)
- `deepseek-r1:70b` (reasoning)
- `llama-3.3-70b`, `mistral-large`, `gemma-3-27b`
- Прокси к Claude / GPT-5 через `litellm` перед Ollama

**В обзоре ниже я использую термин «Ollama-runtime»** — это Ollama-сервер с миксом локальных моделей и прокси к облачным. Это рабочая замена вымышленной команды и совместимая с Cline/LangGraph/MCP архитектура.

---

## 1. Сводная сравнительная таблица (среда + модель + фреймворк)

### 1.1. Уровень 1: среда разработки (vibe-coding)

| Среда | Vendor | Лицензия | Доступ РФ | Цена/мес (₽) | Качество | Гибкость | Production | Итого |
|---|---|---|:--:|---:|:--:|:--:|:--:|---:|
| **Cline** | OSS-сообщество | Apache 2.0 | ✅ on-prem | 0 + модель | 8 | **10** | 8 | **8.4** |
| **Claude Code** | Anthropic | Проприетарный | ⚠️ посредник | 9 000–18 000 | **10** | 9 | **10** | **8.1** |
| **Cursor** | Anysphere | Проприетарный | ⚠️ посредник | 1 800–18 000 | 9 | 7 | 8 | 7.7 |
| **Windsurf/Devin** | Cognition | Проприетарный | ⚠️ посредник | 1 800–18 000 | 8 | 7 | 7 | 7.0 |

### 1.2. Уровень 2: модель (LLM)

| Модель | Провайдер | Доступ РФ | Качество кода | Reasoning | Context | MCP/Tools | Цена | Итого |
|---|---|:--:|:--:|:--:|:--:|:--:|---:|---:|
| **Sonnet 4.6** | Anthropic | ⚠️ | **9** | 8 | **10** (1M) | 9 | 8 | **8.0** |
| **Opus 4.7** | Anthropic | ⚠️ | **10** | **10** | **10** (1M) | **10** | 6 | **8.0** |
| **Qwen3-Coder** | Alibaba | ✅ on-prem | 8 | 7 | 8 | 7 | 8 | 7.7 |
| **DeepSeek-V3** | DeepSeek | ✅ on-prem | 7 | 8 (R1) | 6 | 6 | **10** | 7.7 |
| **GPT-5.5** | OpenAI | ⚠️ | 9 | 9 | 7 | 9 | 7 | 7.4 |
| **YandexGPT 4** | Яндекс | ✅ | 6 | 5 | 4 | 6 | 9 | 7.0 |
| **GigaChat** | Сбер | ✅ | 6 | 5 | 5 | 5 | 9 | 6.9 |

### 1.3. Уровень 3: оркестрация (мультиагенты / MCP / swarm)

| Фреймворк | Лицензия | Доступ РФ | Production | Гибкость оркестрации | MCP | Экономика | Vendor lock | Итого |
|---|---|---|:--:|:--:|:--:|:--:|:--:|---:|
| **LangGraph** | MIT | ✅ | **10** | **10** | **10** | **10** | 9 (нейтрален) | **9.4** |
| **CrewAI** | MIT | ✅ | 8 | 8 | 8 | 8 | 9 (нейтрален) | 8.0 |
| **Claude Agent SDK** | Проприетарный | ⚠️ | 9 | 7 | **10** | 6 | 4 (Anthropic) | 6.9 |
| **AutoGen** | MIT/CC | ✅ | 6 | 9 | 7 | 4 | 6 (Microsoft) | 6.8 |
| **OpenAI Agents SDK** | Apache 2.0 | ⚠️ | 8 | 7 | 9 | 8 | 4 (OpenAI) | 6.6 |
| **MCP (протокол)** | Open spec | ✅ | 7 | — | **10** (транспорт) | — | 10 | 9.0 |

### 1.4. Уровень 4: observability (must-have для production)

| Инструмент | Лицензия | Доступ РФ | LangGraph | CrewAI | AutoGen | Стоимость (1000 трейсов/мес) |
|---|---|---|:--:|:--:|:--:|---:|
| **LangSmith** | Проприетарный | ⚠️ | ✅ first-class | ⚠️ | ⚠️ | $0–$39/мес (до 5K трейсов) |
| **Langfuse** | MIT | ✅ on-prem | ✅ | ✅ | ✅ | **$0** (self-hosted) |
| **AgentOps** | MIT | ✅ | ✅ | ✅ | ✅ | $0–$49/мес |
| **OpenTelemetry + Jaeger** | Apache 2.0 | ✅ on-prem | ⚠️ (DIY) | ⚠️ (DIY) | ✅ нативно | $0 |

### 1.5. Сводный стек по слоям (РФ-рекомендация)

```
┌─────────────────────────────────────────────────────────────┐
│  СРЕДА РАЗРАБОТКИ:  Cline (open source)                     │
├─────────────────────────────────────────────────────────────┤
│  LLM-РОУТЕР:         Ollama-runtime (local + proxy)         │
│                      ├─ Qwen3-Coder (локально, on-prem)     │
│                      ├─ DeepSeek-V3 (локально, fallback)    │
│                      ├─ YandexGPT 4 (облако, compliance)    │
│                      └─ Sonnet 4.6 (через посредника, max)  │
├─────────────────────────────────────────────────────────────┤
│  ОРКЕСТРАЦИЯ:        LangGraph (MIT, vendor-нейтрален)      │
│                      └─ CrewAI (внутри узлов, где нужна     │
│                         гибкость)                            │
├─────────────────────────────────────────────────────────────┤
│  ТРАНСПОРТ ДАННЫХ:   MCP (open spec)                        │
│                      ├─ GitHub MCP                          │
│                      ├─ Postgres MCP                        │
│                      ├─ Notion MCP                          │
│                      └─ self-hosted корпоративные MCP        │
├─────────────────────────────────────────────────────────────┤
│  OBSERVABILITY:      Langfuse (MIT, self-hosted)            │
├─────────────────────────────────────────────────────────────┤
│  ИНФРА:              on-prem (K8s + GPU A100/H100) или      │
│                      Yandex Cloud (152-ФЗ)                   │
└─────────────────────────────────────────────────────────────┘
```

**Совместимость (всё open source на уровне ядра):**
- Cline → Ollama-runtime: `Base URL: http://localhost:11434/v1`
- LangGraph → Ollama-runtime: через `ChatOpenAI(base_url=...)`
- MCP-клиенты → Ollama-runtime: через `ollama-mcp-bridge`
- Langfuse → LangGraph: нативная интеграция через `LangChainCallbackHandler`

---

## 2. Архитектурные шаблоны РФ-проекта

### 2.1. Шаблон A: «Стартап-MVP» (1–3 разработчика, бюджет до 50 000 ₽/мес)

**Стек:**
- **Среда:** Cline (VS Code extension, open source).
- **Модели:** DeepSeek-V3 через Ollama-локально (основная) + YandexGPT 4 (для русскоязычных задач).
- **Агенты:** пока не нужны — single-agent достаточно для MVP.
- **MCP:** GitHub MCP + Notion MCP (готовые).
- **Observability:** логи в файл + периодический ручной разбор.

**Схема:**
```
[Разработчик] → Cline → Ollama-runtime → DeepSeek-V3 / YandexGPT 4
                                       ↓
                              [MCP: GitHub, Notion]
```

**TCO:**
- Cline: 0 ₽
- Ollama + DeepSeek-V3 (67B) локально: ~80 000 ₽ (GPU A100 80GB б/у) + 5 000 ₽/мес электричество
- YandexGPT 4: ~3 000–5 000 ₽/мес при 100K задач
- **Итого: ~5 000–10 000 ₽/мес операционные + 80 000 ₽ стартовых**

**Когда выбирать:**
- MVP, прототип, проверка гипотезы
- Бюджет минимален
- Compliance не критичен
- Данные не уходят в облако

---

### 2.2. Шаблон B: «Production-MVP» (3–10 разработчиков, бюджет 200 000–500 000 ₽/мес)

**Стек:**
- **Среда:** Cline (большинство) + Claude Code Max 5x (для критичных рефакторингов).
- **Модели:** Qwen3-Coder через Ollama-локально (основная) + Sonnet 4.6 через посредника (сложные задачи) + YandexGPT 4 (compliance-critical).
- **Оркестрация:** LangGraph (начинать с него сразу — потом не переделывать).
- **MCP:** GitHub + Postgres + Notion + Jira + self-hosted внутренние.
- **Observability:** Langfuse (self-hosted, open source).

**Схема:**
```
[Разработчики]
    ├─ Cline → Ollama-runtime
    │             ├─ Qwen3-Coder (локально, default)
    │             ├─ DeepSeek-V3 (локально, fallback)
    │             └─ Sonnet 4.6 (через посредника, premium)
    └─ Claude Code (CLI)
              └─ Sonnet 4.6 (подписка Max 5x)
                          ↓
                   [LangGraph API]
                          ↓
                   [MCP-серверы]
                          ↓
                   [Langfuse (self-hosted)]
```

**TCO (12 мес):**
- Cline: 0 ₽
- Ollama + GPU A100×2: 400 000 ₽ стартовые + 120 000 ₽/год электричество
- Claude Code Max 5x: 140 000 ₽/год (через посредника)
- Sonnet 4.6 API (premium-задачи): 60 000 ₽/год
- YandexGPT 4 (compliance): 50 000 ₽/год
- Langfuse (self-hosted): 0 + 60 000 ₽/год (1/4 FTE на поддержку)
- Инфра (K8s on-prem или Yandex Cloud): 600 000 ₽/год
- **Итого: ~1 350 000 ₽/год + 400 000 ₽ стартовые = ~1 750 000 ₽ за первый год**

**Когда выбирать:**
- Production с реальными пользователями
- Нужна observability и error recovery
- Есть бюджет на 200K+/мес
- Compliance частичный (не крит)

---

### 2.3. Шаблон C: «Enterprise / compliance-critical» (10+ разработчиков, финсектор/госсектор/медицина)

**Стек:**
- **Среда:** Cline + Claude Code (только для архитектурных решений, не в проде).
- **Модели:** **только on-prem** — Qwen3-Coder + GigaChat (через Сбер) + YandexGPT 4 (в изолированном сегменте Yandex Cloud).
- **Оркестрация:** LangGraph + CrewAI (внутри узлов) + A2A для межсервисного взаимодействия.
- **MCP:** self-hosted корпоративные MCP-серверы (1С, внутренние API, CRM, БД).
- **Observability:** Langfuse + OpenTelemetry + Jaeger + Sentry (on-prem).
- **Безопасность:** Vault для секретов, DLP, audit-log всех действий агентов.

**Схема:**
```
[Разработчики (Cline)]
        ↓
[Ollama-runtime (on-prem, изолированный сегмент)]
        ├─ Qwen3-Coder (default)
        ├─ GigaChat (Сбер on-prem)
        └─ YandexGPT 4 (Yandex Cloud, изолированный VPC)
                ↓
[LangGraph (оркестратор)]
        ├─ CrewAI (ролевые узлы)
        └─ A2A (между изолированными сервисами)
                ↓
[self-hosted MCP]
        ├─ 1С MCP
        ├─ Internal CRM MCP
        ├─ PostgreSQL MCP
        └─ File system MCP
                ↓
[Observability stack (on-prem)]
        ├─ Langfuse
        ├─ OpenTelemetry → Jaeger
        └─ Sentry
                ↓
[Compliance layer]
        ├─ Vault (секреты)
        ├─ DLP (Data Loss Prevention)
        └─ Audit-log (все действия агентов)
```

**TCO (12 мес, оценка для команды 10 человек):**
- GPU-кластер (4× A100 80GB): 1 600 000 ₽ стартовые + 480 000 ₽/год электричество
- LangGraph + CrewAI (open source): 0 ₽
- GigaChat on-prem (Сбер): договорная, ~300 000–600 000 ₽/год
- YandexGPT 4 (изолированный VPC): 200 000 ₽/год
- Langfuse + Jaeger + Sentry (on-prem): 0 ₽ + поддержка (1 FTE) = 1 800 000 ₽/год
- Инфра (K8s on-prem): 1 200 000 ₽/год
- Безопасность (Vault, DLP, audit): 600 000 ₽/год
- **Итого: ~4 500 000 ₽/год операционные + 1 600 000 ₽ стартовые**

**Когда выбирать:**
- 152-ФЗ, финсектор, госкомпании, оборонка
- Чувствительные данные (ПДн, медицинские, финансовые)
- Аудит и регуляторика обязательны
- Бюджет не ограничен жёстко

---

### 2.4. Шаблон D: «Coding swarm» (10+ разработчиков, большая кодовая база)

**Стек:**
- **Среда:** Claude Code (Max 20x) с Agent Teams + Cline для повседневной работы.
- **Модели:** Sonnet 4.6 (через Claude Code) + Opus 4.7 (для критичных PR) + Qwen3-Coder on-prem (для CI/CD пайплайна).
- **Оркестрация:** Claude Agent Teams + LangGraph (для сложных многошаговых задач).
- **MCP:** GitHub + Linear + Sentry + Jenkins + custom CI/CD MCP.
- **Observability:** LangSmith (платный, но окупается).

**Схема:**
```
[Разработчики]
    ├─ Claude Code Max 20x (Agent Teams)
    │       └─ Sonnet 4.6 + Opus 4.7
    └─ Cline (повседневные задачи)
            └─ Ollama-runtime → Qwen3-Coder
                    ↓
[LangGraph (сложные workflow)]
        ↓
[MCP: GitHub, Linear, Sentry, Jenkins]
        ↓
[LangSmith (observability)]
```

**TCO (12 мес, команда 10):**
- Claude Code Max 20x × 3 ключевых разработчика: 540 000 ₽/год (через посредника)
- Cline (для остальных 7): 0 ₽
- Ollama + Qwen3-Coder для CI: 200 000 ₽ стартовые + 60 000 ₽/год
- Sonnet 4.6 API (по необходимости): 100 000 ₽/год
- LangSmith: 360 000 ₽/год
- **Итого: ~1 260 000 ₽/год + 200 000 ₽ стартовые**

**Когда выбирать:**
- Большая кодовая база (100K+ LOC)
- Параллельная работа над несколькими репозиториями
- Нужны автономные PR от AI
- Бюджет на observability оправдан

---

## 3. Чек-лист «Как выбрать стек для своего проекта»

### 3.1. Шаг 1: определить класс задачи

```
❓ Это MVP / прототип?
   → Да  → Шаблон A (Cline + DeepSeek локально)
   → Нет → К шагу 2

❓ Это production с реальными пользователями?
   → Да  → К шагу 2
   → Нет → К шагу 3

❓ Это compliance-critical (финсектор, госкомпании, медицина)?
   → Да  → Шаблон C (полный on-prem)
   → Нет → К шагу 2
```

### 3.2. Шаг 2: оценить бюджет и команду

| Бюджет/мес | Команда | Шаблон |
|---|---|---|
| <50 000 ₽ | 1–3 | A (стартап-MVP) |
| 50 000–200 000 ₽ | 3–10 | A → переход на B через 3 мес |
| 200 000–500 000 ₽ | 3–10 | B (production-MVP) |
| 200 000–500 000 ₽ | 10+ | D (coding swarm) |
| >500 000 ₽ | 10+ | C (enterprise) или D |

### 3.3. Шаг 3: оценить данные и compliance

| Тип данных | Требование | Решение |
|---|---|---|
| Open source, публичный код | Нет | Любой шаблон |
| Коммерческий код, не sensitive | Нет | Шаблон A или B |
| ПДн, финданные | 152-ФЗ | Шаблон C, on-prem |
| Гостайна / DLP-критичные | Полная изоляция | Шаблон C, **только** on-prem, **только** GigaChat/Qwen3-Coder |

### 3.4. Шаг 4: оценить риски vendor lock-in

| Вопрос | Если «да» |
|---|---|
| Готовы зависеть от Anthropic/OpenAI? | Нет → мульти-роутинг через Ollama-runtime |
| Допустим риск отключения подписки? | Нет → on-prem fallback (Qwen3-Coder, DeepSeek-V3) |
| Нужна независимость от платёжных систем? | Да → on-prem (Qwen3-Coder + LangGraph) |
| Могут ли быть санкционные ограничения? | Да → мульти-роутинг, российские модели в проде |

### 3.5. Шаг 5: выбрать observability

| Бюджет на observability | Решение |
|---|---|
| 0 ₽ | Langfuse (self-hosted) или просто логи |
| <300 000 ₽/год | Langfuse (self-hosted) + OpenTelemetry + Jaeger |
| >300 000 ₽/год | LangSmith (готовый, поддержка включена) |

### 3.6. Шаг 6: выбрать модель по умолчанию

| Критерий | Модель по умолчанию |
|---|---|
| Максимальное качество кода (без санкций) | Opus 4.7 (через Claude Code Max 20x) |
| Баланс цена/качество (с санкциями) | Sonnet 4.6 (через посредника) или Qwen3-Coder (on-prem) |
| Экономия (с приемлемым качеством) | DeepSeek-V3 (on-prem) |
| Русский язык + compliance | YandexGPT 4 (облако) или GigaChat (on-prem) |
| Локальный fallback | Qwen3-Coder:30b через Ollama (≈18 GB VRAM) |

### 3.7. Шаг 7: выбрать фреймворк

| Критерий | Фреймворк |
|---|---|
| Production с observability | LangGraph + Langfuse |
| Быстрый прототип с ролями | CrewAI |
| OpenAI-центричный стек | OpenAI Agents SDK |
| Anthropic-центричный стек | Claude Agent SDK |
| Multi-model, vendor-нейтральный | LangGraph |
| Coding swarm | Claude Code Agent Teams + LangGraph |

### 3.8. Шаг 8: финальная сборка (пример)

**Типичный ответ для среднего российского проекта (5 разработчиков, финтех, бюджет 300 000 ₽/мес):**

```
✅ Среда:           Cline (5 лицензий) + Claude Code Max 5x (1 лицензия для архитектора)
✅ Модели:          Qwen3-Coder (on-prem, default) + Sonnet 4.6 (premium, через посредника)
✅ Оркестрация:     LangGraph (1 кластер) + CrewAI (для content-задач)
✅ Транспорт:       MCP (GitHub, Jira, Postgres, внутренний 1С MCP)
✅ Observability:   Langfuse (self-hosted) + OpenTelemetry
✅ Инфра:           on-prem K8s + 2× A100 80GB + Yandex Cloud (для внешних API)
✅ Безопасность:    Vault + DLP + audit-log всех действий агентов

TCO:  ~2 000 000 ₽/год + 600 000 ₽ стартовые
```

**Критерий «стоп»: если ваш стек содержит ≥3 проприетарных зависимости без open-source fallback — вы в зоне риска.** Пересмотрите.

---

## 4. Матрица быстрого выбора (одна картинка)

| Если у вас… | Среда | Модель | Фреймворк | MCP | Observ | TCO/год |
|---|---|---|---|---|---|---|
| **Стартап, 1–3 чел, <50K/мес** | Cline | DeepSeek-V3 (Ollama) | — | GitHub MCP | Логи | ~200K ₽ |
| **Production, 3–10 чел, 200–500K/мес** | Cline + Claude Code | Qwen3-Coder + Sonnet 4.6 | LangGraph | GitHub + Postgres + Notion | Langfuse | ~1.8M ₽ |
| **Enterprise, 10+ чел, compliance** | Cline | Qwen3-Coder + GigaChat | LangGraph + CrewAI | Self-hosted корпоративные | Langfuse + Jaeger | ~6M ₽ |
| **Coding swarm, 10+ чел, большая кодовая база** | Claude Code Max 20x + Cline | Sonnet 4.6 + Opus 4.7 | Claude Agent Teams + LangGraph | GitHub + Linear + Sentry | LangSmith | ~1.5M ₽ |
| **Open source, публичный код** | Cline | Qwen3-Coder (Ollama) | LangGraph | GitHub MCP | Логи | ~100K ₽ |
| **Госсектор, полная изоляция** | Cline | GigaChat (on-prem) | LangGraph | Self-hosted 1С MCP | Langfuse (on-prem) | ~5–8M ₽ |

---

## 5. Контрольный список перед запуском в прод

```
[ ] 1. Среда выбрана и протестирована на 2+ репо
[ ] 2. Модели: default + fallback + premium — все три определены
[ ] 3. Ollama-runtime настроен (если используется)
[ ] 4. MCP-серверы self-hosted, не зависят от внешних SaaS
[ ] 5. LangGraph (или выбранный фреймворк) с checkpointing
[ ] 6. Langfuse/LangSmith — все действия логируются
[ ] 7. Human-in-the-loop узлы для критичных операций
[ ] 8. Лимиты на сумму/частоту действий агентов
[ ] 9. Kill-switch (мгновенное отключение агента)
[ ] 10. Audit-log с привязкой к пользователю-инициатору
[ ] 11. 152-ФЗ compliance (если применимо)
[ ] 12. DLP на исходящий трафик (если применимо)
[ ] 13. Тест fallback: облако недоступно → on-prem подхватывает
[ ] 14. Тест rollback: агент сделал плохое действие → откат работает
[ ] 15. Тест observability: инцидент → трейсы нашлись за <5 минут
```

**Если 12+ пунктов ✓ — стек готов к проду. Если <9 — не запускайте.**

---

## 6. Источники

Базовые обзоры:
- [Обзор сред и LLM для vibe-кодинга](2026-06-17-vibe-coding-obzor.md)
- [Обзор фреймворков, MCP и swarm](2026-06-17-multiagent-mcp-swarm-obzor.md)

Внешние источники (из базовых обзоров):
- [Cursor Docs](https://cursor.com/ru/help/account-and-billing/pricing)
- [Anthropic — Claude Code Max plan](https://support.claude.com/ru/articles/11049741)
- [Cline — GitHub](https://github.com/Cline/Cline)
- [LangGraph vs CrewAI vs AutoGen (Lushbinary)](https://lushbinary.com/blog/langgraph-vs-crewai-vs-autogen-ai-agent-framework-comparison/)
- [MCP, LangGraph или CrewAI: выбор 2026 (vc.ru)](https://vc.ru/ai/2847529-mcp-langgraph-i-crewai-kak-vybrat-luchshij-instrument-dlja-orkestracii-llm)
- [Best AI Agent Frameworks 2026 (The Editorial)](https://theeditorial.news/ai-agents/best-ai-agent-frameworks-of-2026-langgraph-crewai-autogen-and-beyond-tested-in-production-mq6lh41n)
- [Multi-Agent Orchestration Frameworks 2026 (Presenc AI)](https://presenc.ai/research/multi-agent-orchestration-frameworks-2026)
- [Benchmarking Multi-Agent Frameworks (JATIR)](https://jatir.org/article.php?paperid=140332)

---

**Главная мысль сводного обзора:** в 2026 г. для РФ-проекта оптимальный стек — **Cline + Ollama-runtime (Qwen3-Coder + DeepSeek) + LangGraph + MCP + Langfuse**. Всё open source на уровне ядра, on-prem, без санкционных рисков, с полной observability. Западные модели (Sonnet 4.6, Opus 4.7) — как premium-опция для критичных задач через посредника.
