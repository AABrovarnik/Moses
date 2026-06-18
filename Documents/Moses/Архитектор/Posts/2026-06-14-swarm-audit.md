---
date: 2026-06-14
time: 19:09
status: выполнено
project: C:\Users\aabro\Documents\Moses\Архитектор
session: task-journal-start-point
related:
  - Posts/2026-06-14-task-journal-bootstrap.md
  - Posts/2026-06-14-start-point.md
  - swarm/architecture-v3.md
  - swarm/README.md
files_changed:
  - Posts/2026-06-14-swarm-audit.md
  - Posts/journal.md
  - Posts/_unfinished.md
commands:
  - "find C:/Users/aabro/Documents/Moses/Архитектор/swarm/ -maxdepth 4 -type f"
  - "ls -la C:/Users/aabro/Documents/Moses/Архитектор/swarm/"
---

# Аудит папки swarm/ — что требует доработки и завершения

## Контекст
- Откуда пришло: запрос пользователя — «проанализируй папку swarm, проверь какие задачи требуют доработки и завершения».
- Что хотели получить: обзор состояния подпроекта swarm (программный рой AI-агентов), выявление незавершённых работ и обязательных доработок.

## Действия
1. Просканирован `C:\Users\aabro\Documents\Moses\Архитектор\swarm\` — это **отдельный git-репозиторий** (.git присутствует), 8 файлов:
   - `README.md` (5.2 КБ) — индекс
   - `architecture-v3.md` (29.5 КБ) — **сводный архитектурный документ v3, актуален на 2026-06-14**
   - `Промпт.md` (5 КБ) — исходный промпт v1 (история)
   - `Промпт-v3.md` (25 КБ) — промпт v3 для red-team review архитектуры v3
   - `redteam-review-2026-06-11.md` (31.8 КБ) — первая рецензия v1
   - `redteam-llm-swarm-review.md` (28.3 КБ) — реализационная рецензия v2
   - `redteam-prompt-v2-with-openclaw.md` (16.7 КБ) — промпт v2
   - `server-spec-and-software.md` (26.8 КБ) — ТЗ на сервер
2. Прочитаны `README.md` и `architecture-v3.md` (428 строк, v3.0 от 2026-06-14).
3. Остальные 5 файлов — предыдущие версии и рецензии, по статусу вторичны (см. README §"Состав").

## Артефакты
- Эта запись: `Posts/2026-06-14-swarm-audit.md`
- Сводный отчёт по результатам: **см. ниже «Сводка»** и опциональный файл `Posts/2026-06-14-swarm-audit-detail.md` (НЕ создавался — ответ дан в чате; создать по запросу).

## Сводка: что требует доработки и завершения

### A. P0-блокеры v3 (10 шт., НЕ закрыты) — обязательно до deploy

Из `architecture-v3.md` §10 и упоминания в README:
1. **Threat model + IAM** (E0, 1 день) — документ угроз не создан, IAM-роли не описаны.
2. **Ed25519-подписи решений** (I2) — схема описана, но ключ не сгенерирован, verify-логика не реализована.
3. **Outbox-pattern** (I5) — таблица описана, retry с idempotency-key не реализован.
4. **litestream → Backblaze B2 EU** (I3) — bucket не создан, replica не настроена, RPO не верифицирован.
5. **systemd sandbox для OpenClaw** (I8) — unit-файл не написан, nftables egress filter не настроен.
6. **nftables egress filter** — allowlist IP-диапазонов Anthropic/OpenAI/Google/Telegram/Ollama.
7. **Allowlist chat_id в Telegram-санитайзере** (I9) — санитайзер-парсер не реализован.
8. **Restore-drill** (I7) — `verify_backup.sh` не написан, drill не проведён.
9. **Circuit breaker в Core** (I10) — state machine не реализована.
10. **2-account strategy для Anthropic** (I18) — второй аккаунт не заведён.

### B. Не начато (E0–E9 из §8, 11 дней) — порядок внедрения

| Этап | Дни | Статус |
|---|---|---|
| E0. Threat model + IAM | 1 | ❌ |
| E1. Сервер + стек | 1 | ❌ |
| E2. Backup-стратегия | 1 | ❌ |
| E3. Venya Core | 2 | ❌ |
| E4. OpenClaw sandbox | 0.5 | ❌ |
| E5. Агенты + маршрутизация | 2 | ❌ |
| E6. Watchman + каналы | 1 | ❌ |
| E7. Restore-drill + chaos | 1 | ❌ |
| E8. Onboarding backup-человека | 1 | ❌ |
| E9. Документация + runbook | 0.5 | ❌ |

**Кодинг НЕ начат.** Только документы.

### C. Архитектурные вопросы без ответа (Приложение B)

- План форка OpenClaw, если проект будет заброшен.
- Экономика LLM-рой как продукта (монетизация не описана).
- Disaster Recovery в другом регионе (B2 EU = страховка данных, не инфраструктуры).
- On-call rotation через несколько людей.
- Юридические аспекты автоматического failover.
- Open-source vs proprietary runtime OpenClaw.

### D. P1-инварианты (некритичные, но должны быть в roadmap)

Из §9 (I13–I20): NTP-мониторинг, chaos-тесты в CI, отключённые session-logs, PII-фильтр (presidio-analyzer), appeals templates, GDPR retention policy.

### E. Документы, требующие review/актуализации

- `Промпт-v3.md` (25 КБ) — подан ли уже в работу, есть ли отчёт red-team по нему? В `Posts/` лежит `redteam-prompt-v2-with-openclaw.md`, но не по v3.
- `server-spec-and-software.md` (26.8 КБ) — насколько он согласован с v3 (особенно по бюджету и iron-choices)? Пересекается ли с E1?
- README §"Контакты" ссылается на GitHub `https://github.com/AABrovarnik/swarm` — существует ли remote? (В текущем коммите git не публиковался — проверить отдельно.)

## Статус
выполнено — проведён экспресс-аудит, незаконченные работы выявлены и разложены по приоритетам (A/B/C/D/E).

## Next steps
1. **Подтвердить приоритет работ.** Рекомендую начать с E0 (Threat model) — он блокирует все остальные этапы и закладывает IAM для backup-человека.
2. **Определить backup-человека** (I11) — без этого MVP не запускается по правилам v3.
3. **Завести Backblaze B2 EU bucket** — лёгкий инфраструктурный шаг, не зависит от кода.
4. **Создать `Промпт-v3.md`-ревью** — заказать у Мойши/`venya-report` отчёт по 30 замечаниям, по аналогии с v2.
5. **Сверить `server-spec-and-software.md` с v3 §3 (бюджет)** — были ли изменения после 2026-06-12.
