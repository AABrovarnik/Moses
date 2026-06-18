# Swarm review 2026-06-14: «Совет директоров» по проекту программного роя

> **Дата:** 2026-06-14
> **Назначение:** сводный отчёт трёх независимых перспектив (SRE, Operations, Security) по архитектуре v2 (`redteam-prompt-v2-with-openclaw.md`) с учётом уже проведённых двух рецензий (`redteam-review-2026-06-11.md`, `redteam-llm-swarm-review.md`).
> **Источник:** результаты запуска трёх параллельных агентов-критиков, рекомендации и замечания которых прошли кросс-валидацию между перспективами.
> **Целевая аудитория:** владелец проекта, архитектор.

---

## 0. TL;DR

| Параметр | Решение |
|---|---|
| **Вердикт «совета директоров»** | **Принять с обязательными доработками.** v2 жизнеспособна технически, но операционно хрупка, небезопасна «из коробки» и опирается на решения, которые работают только в сферическом вакууме. |
| **P0-блокеры до запуска MVP** | 6 пунктов (см. §10) |
| **Скрытые расходы, которых нет в бюджете** | $3000–6000/год в человеко-часах владельца + $500–2000/год прямых + $0–2000/год юридических (если SaaS с ПДн) |
| **Главный риск, общепризнанный всеми тремя** | Один разработчик = SPOF и для надёжности, и для безопасности, и для операций |
| **MVP готовность** | 10–14 дней при условии, что P0 закрыты **до** deploy в прод |

---

## 1. Контекст и материалы

Проект «swarm» — программный рой из 3 LLM-агентов (Izya-Speedy, Izya-Deep, Moysha++) и одного процедурного оркестратора Venya Core, развёрнутый на выделенном сервере с OpenClaw 2026.6.1. Исходный инцидент — 37-часовой лимит LLM-провайдера, во время которого все агенты одновременно перестали отвечать.

**Входные документы (5 файлов в `swarm/`):**
1. `Промпт.md` — исходный промпт v1: 12 принципов отказоустойчивой архитектуры.
2. `redteam-review-2026-06-11.md` — первая общая рецензия (v1).
3. `redteam-llm-swarm-review.md` — реализационная рецензия: подбор LLM, бюджет, код-костяк.
4. `redteam-prompt-v2-with-openclaw.md` — обновлённый промпт v2.
5. `server-spec-and-software.md` — ТЗ на сервер.

**«Совет директоров»** собран из трёх независимых перспектив:
- **SRE / Distributed Systems** — консенсус, репликация, observability.
- **Product / Operations (COO)** — человек-за-пультом, runbook, скрытые расходы.
- **Security / Threat Model** — prompt injection, insider threat, compliance.

---

## 2. Что «совет» единогласно подтвердил в v2

Все три перспективы сошлись на том, что **ядро концепции рабочее**:

- ✅ Разделение **Venya Core (без LLM)** и **исполнителей (с LLM)** — архитектурно верно.
- ✅ **4 семейства LLM** (Ollama local + Anthropic + OpenAI + Google) — правильное резервирование, не избыточно.
- ✅ **Один пакет передачи командования** вместо трёх — упрощение согласовано.
- ✅ **2 канала уведомлений** (Telegram + email) — правильный MVP-выбор.
- ✅ **5 режимов** (NORMAL, DEGRADED_*, HOLD, STANDBY) — корректная градация.
- ✅ **Chaos-тесты** — обязательная практика.
- ✅ **Moysha++ на другом провайдере** как критик — концепция верна, но требует доработки (см. §4.3).

---

## 3. Что «совет» единогласно считает сломанным

Список критических проблем, которые **все три** перспективы отметили как блокирующие.

### 3.1. `flock` ≠ distributed consensus (P0)

**Проблема.** `flock(2)` — advisory lock на локальной FS. Между VPS-1 и VPS-2 файловые системы **разные**, lock не координирует. Heartbeat 30 сек с TTL 15 сек — это **отрицательный TTL**: при partition > 15 сек оба экземпляра видят stale heartbeat и оба берут лидерство. Гарантированный split-brain.

**Цитата.** `redteam-prompt-v2-with-openclaw.md` §2.1.

**Что делать.** См. §6.1.

### 3.2. ssh-pull поверх живой SQLite (P0)

**Проблема.** `rsync --partial --inplace` раз в 5 минут по работающей SQLite WAL = corrupted WAL при восстановлении. Плюс при failover standby-VPS пишет в свою локальную БД; когда VPS-1 оживёт, `rsync` пойдёт обратно и перезапишет свежие решения standby-данными. **Восстановление теряет данные** — то, против чего v2 и строилась.

**Цитата.** `redteam-prompt-v2-with-openclaw.md` §2.4.

**Что делать.** См. §6.2.

### 3.3. Один инцидент = одно уведомление — семантически не определено (P0)

**Проблема.** `hash(incident_id)` + cooldown 5 мин — это дедуп на **один канал**. Если уведомление уходит в **два** канала (Telegram + email для SEV-1) — это одно уведомление или два? При реальном инциденте on-call получает 50 Telegram-сообщений и 10 email — и не понимает, один это инцидент или десять. Alert-fatigue через 2 недели, MTTD возвращается к 37 часам.

**Цитата.** `redteam-prompt-v2-with-openclaw.md` §2.5–2.6.

**Что делать.** См. §6.3.

### 3.4. Нет outbox-pattern для OpenClaw (P0)

**Проблема.** OpenClaw Gateway — единственная точка координации. Если он упал **посреди** того, как агент получил команду и **до** записи `decision` в БД — при рестарте Gateway либо (а) дубль задачи (лимит сжигается), либо (б) потеря (пользователь не получил результат). Семантика транзакций не определена.

**Цитата.** `redteam-prompt-v2-with-openclaw.md` §1.4, §2.7.

**Что делать.** См. §6.4.

### 3.5. Threat model отсутствует полностью (P0)

**Проблема.** Ни одна из существующих рецензий не рассматривает:
- prompt injection через Telegram / email / web.search;
- утечку контекста через LLM-провайдеров (включая session-logs OpenClaw);
- компрометацию одной ноды = компрометация всего роя (БД, ssh-pull ключ, OpenClaw токен);
- GDPR / ФЗ-152 / CCPA (Hetzner DE + DeepSeek в Китае = трансграничная передача без SCC).

**Цитата.** отсутствует во всех 4 рецензиях.

**Что делать.** См. §6.5.

### 3.6. Один разработчик = SPOF (P0)

**Проблема.** 1 инженер на поддержку → bus-factor = 1. В отпуске / больнице / самолёте рой живёт без оперативного управления 1–14 дней. Backup-контакт, IAM-роли, time-limited ssh-доступ — отсутствуют. Скрытые расходы на найм SRE/security-фрилансера: $200–1500/мес **сверх** бюджета $140/мес.

**Цитата.** `redteam-prompt-v2-with-openclaw.md` §1.3.

**Что делать.** См. §6.6.

---

## 4. Голос SRE: распределённые системы и SRE-перспектива

### 4.1. Восемь критических проблем (см. также §3)

1. **`flock` не работает между нодами** (см. §3.1).
2. **ssh-pull поверх живой SQLite** (см. §3.2).
3. **systemd auto-restart маскирует crash-loop** — `Restart=always` без `OnFailure=` хука и `coredump` = рестарт при segfault 5 раз подряд → `failed state` → рой стоит, Watchman не различает «жив» от «перезапустился 5 раз».
4. **OpenClaw как SPOF без outbox** (см. §3.4).
5. **Дедуп семантически не определён** (см. §3.3).
6. **daily_tokens rate-limit vs. usage-based switching** — точка принятия решения не описана, in-flight запросы не обрабатываются. Circuit breaker должен жить в Venya Core, а не в агентах.
7. **chaos-тесты по cron в воскресенье 03:00 — кто смотрит результат?** Нет ownership, нет external ping о завершении.
8. **NTP-мониторинг отсутствует** — расхождение часов > 15 сек = массовый отзыв мандатов, `ts` в пакетах невалиден.

### 4.2. 10 скрытых SPOF в v2

| # | SPOF | Что произойдёт |
|---|------|----------------|
| 1 | `context.db` + WAL на одном диске | Диск заполнился → SQLite ENOSPC → рой стоит |
| 2 | Healthchecks.io (внешний SaaS) | Не узнаем, что Watchman молчит |
| 3 | Telegram-аккаунт (не бот) | Бан аккаунта = потеря обоих каналов |
| 4 | OpenClaw binary | Баг в 2026.6.1 / config corruption → агенты не стартуют |
| 5 | rsync SSH-ключ | Потеря ключа = молчаливый fail реплики каждые 5 мин |
| 6 | Ollama runtime | Модели не загружены на свежем VPS → DEGRADED_LOCAL не работает |
| 7 | `/etc/venya/venya.yaml` | Без git/etckeeper — drift, нет аудита правок |
| 8 | SMTP-провайдер для email | OAuth token expired → email-канал SEV-1 молча умирает |
| 9 | Watchman cron демон | Если cron упал — Watchman не запускается, никто не знает |
| 10 | NTP-источник | Все VPS на `pool.ntp.org` — пул недоступен = часы расходятся |

### 4.3. Что упростить

1. **ssh-pull SQLite → `litestream` на S3-совместимое хранилище** (Backblaze B2, $0.005/ГБ). Убирает второй VPS как standby, даёт RPO ≤ 10 сек, restore = `litestream restore` за минуту.
2. **flock + heartbeat + «внешний арбитр» → один Venya Core, без второго инстанса.** Проблема превращается из «как сделать failover» в «как быстро перезапустить на новом VPS» — 5 мин systemd + cold start.
3. **4 LLM-провайдера с per-agent fallback-цепочками → 2 провайдера + 1 локальный**, решение принимает Core (одна таблица `provider_priority`), а не агент.
4. **Outbox + дедуп → готовая либа** (`apprise` для уведомлений, persistent jobstore для outbox) — 600 строк своего кода = 12 багов.
5. **Chaos по cron в проде → chaos как CI-job** на ephemeral VM; в проде — только ежемесячный game day.

### 4.4. Топ-3 риска вне покрытия существующих рецензий

1. **Backup-recovery drill — описан, но не выполняется.** В `redteam-review-2026-06-11.md` §7 «раз в неделю», в `redteam-llm-swarm-review.md` §7 «удалить context.db → восстанавливается с реплики» — **нигде** нет ответа «кто, когда, в какой день, на каком сервере, как доказывает, что 7 дней решений восстановимы». Без регулярного drill'а «у нас есть бэкап» = ложь.
2. **Capacity planning / saturation.** Ни одна рецензия не рассматривает degraded-success: провайдер отвечает 200 OK, но качество деградировало (новая версия модели, A/B-тест). Moysha++ это поймает постфактум, Watchman — нет.
3. **Управление секретами и ротация.** OpenClaw token ротация раз в 90 дней упоминается, но: где хранятся env-переменные, как ротируется API-ключ Anthropic при компрометации прямо сейчас, кто имеет root, как ssh-pull ключ защищён от компрометации — ответов нет.

---

## 5. Голос Operations (COO): человек-за-пультом

### 5.1. Десять операционных пробелов (см. также §3)

1. **Cron каждые 60 сек — наивное допущение.** Cron не гарантирует интервал, не имеет watchdog'а на себя. **Что делать:** systemd-timer `OnUnitActiveSec=30s` + `Persistent=true` + external Healthchecks.io + Venya Core сам алертит если Watchman молчит 120 сек.
2. **Telegram-бот как единственный «живой» канал в 3 часа ночи.** Бот могут забанить, IP Hetzner/OVH попадает в spam у Gmail автоматически. **Что делать:** Pushover/ntfy.sh/Telegram-бот №2 на отдельном номере, прогрев email-IP 2 недели, decision tree в runbook.
3. **daily_tokens budget: что если Anthropic/OpenAI заблокирует ключ по «abuse review» на 24–72 часа?** Appeals — отдельная форма для каждого провайдера, ответ 24–48 часов в раб. дни, до 72 ч в выходные. **Что делать:** 2 аккаунта Anthropic, status code taxonomy в `providers` таблице (`429_exhausted` ≠ `403_abuse` ≠ `503_down`), заготовленные appeals-шаблоны.
4. **«Восстановление ≤ 5 мин» — сферически в вакууме.** DNS-кэш Telegram 5–15 мин, maintenance window Hetzner с возвратом старого MAC/IP, split-horizon DNS. **Что делать:** Healthchecks.io извне через nginx + Let's Encrypt, fencing на локальном диске (не NFS/SSHFS), DNS TTL ≤ 60 сек.
5. **Runbook 5 bash-команд.** Нет decision tree, нет скрипта `triage.sh`, нет эскалации, нет ASCII-диаграммы. **Что делать:** полноценный 2-tier runbook (для backup-человека — read-only + ack, для владельца — полный), контакт-карточка с эскалацией.
6. **Watchman 7 проверок → 5 false-positive в день → alert-fatigue.** **Что делать:** сократить до 3 проверок в MVP (Core жив, Gateway 200, БД пишется), inline `ack` в Telegram, разные каналы по SEV.
7. **OpenClaw как SPOF без escape hatch.** Если upstream бросят/переименуют/сменят лицензию — нет плана Б. **Что делать:** зафиксировать версию в `/etc/venya/openclaw.pin`, отключить автообновление, escape-hatch `manual_mode.sh` (прямые HTTP-вызовы к LLM), мониторинг upstream releases.
8. **ssh-pull 5 мин + SPOF ssh-ключ.** 5-мин окно потери данных + компрометация VPS-2 = ssh-доступ к VPS-1. **Что делать:** отдельный ключ с `command="rsync --server ..."` в `authorized_keys`, WAL-режим с 30-сек pull, restore-drill 1×/нед, hardening VPS-2.
9. **Один email-аккаунт, один Telegram-аккаунт — канальный SPOF.** **Что делать:** 3 уровня SEV-1 эскалации (Pushover + запасной контакт + публичный status-канал), SMTP с 2FA-Recovery (Fastmail/ProtonMail/Workspace), backup Telegram-аккаунт на физ. SIM.
10. **SQLite + WAL + бэкап без verify = «бэкап есть, восстановиться не можем».** **Что делать:** `PRAGMA synchronous=FULL` + ежедневный `VACUUM INTO` в verified snapshot, cold-restore на test-VPS 1×/нед, `verify_backup.sh` в cron.

### 5.2. Точки, где v2 потребует роста команды

1. **On-call 24/7:** первый SEV-1 в 3 часа ночи потребует либо SRE-фрилансера ($500–1500/мес), либо managed-service ($200–500/мес).
2. **Database administration:** SQLite с 3 агентами уже на грани (lock-contention при failover = 5 записей/сек), миграция на Postgres при росте до 10 агентов.
3. **Security operations:** CVE-мониторинг, PTR/SPF/DKIM/DMARC, incident response — 1 час/неделю минимум.
4. **LLM-ops:** 4 провайдера = 4 changelog'а, 4 appeals-процедуры, 4 rate-limit'а; major-апдейт Sonnet/GPT/Gemini = 1 неделя полной занятости.

### 5.3. Метрики успеха (actionable, не «monitoring ради мониторинга»)

| Метрика | Целевой порог | Что говорит |
|---|---|---|
| **MTTD для SEV-1** | ≤ 5 мин в 95% случаев | Система сама себя мониторит, или узнаём от пользователей? |
| **MTTR по режимам отказа** | Anthropic down ≤ 5 мин, VPS down ≤ 30 мин, OpenClaw down ≤ 10 мин | Как быстро чиним |
| **% времени в NORMAL-режиме** | ≥ 90% за неделю, ≥ 95% за месяц | Хронически отказоустойчивая или реально работает |
| **Daily LLM cost per provider** | $3/день Anthropic, $2 OpenAI, $1 Google | В рамках бюджета или нет |
| **SEV-1 alerts/week + ack time** | ≤ 1 истинного/нед, ack ≤ 5 мин | Сигнал или шум |
| **% задач с ответом ≤ 60 сек** | ≥ 99% SLO | Пользователь получает результат или зависает |
| **Restore-drill success rate** | 100% weekly, минимум 1/мес | Если VPS сгорит, восстановимся или будем 2 дня поднимать |

### 5.4. Скрытые расходы (владелец не учёл)

| Категория | $/год | Чел-часы/год |
|---|---|---|
| Ротация API-ключей и сертификатов (12 процедур × 30 мин) | $0 | 10–15 |
| Chaos-тесты (6 сценариев × 15 мин/нед) | $0 | 48–72 |
| Зависимости + CVE-мониторинг (Python/Node/Ollama/OpenClaw) | $0 | 50–80 |
| Cold start после 2–3 дневного простоя (3–5 раз/год × 4–8 ч) | $200–400 × 4 = $1000–2000 | 12–40 |
| Email-IP прогрев + DNS (10–15 ч setup + повтор на каждом новом VPS) | $30–100 | 10–15 |
| Backup-storage offsite (S3/B2 EU) | $60–240 | 2–4 |
| Обновление LLM (Sonnet 5, GPT 6, Gemini 3 — тест+миграция) | $0 | 8–15 дней |
| Юридические (DPA Anthropic/OpenAI/Google, ФЗ-152 если SaaS) | $0–2000 | 1–3 дня |
| Онбординг backup-человека (при смене владельца) | $0 | 3–5 дней |
| Healthchecks.io + Pushover + домен + 2-я SIM | $150–500 | 5–10 |
| **ИТОГО** | **$1240–4840** прямых | **150–250** часов/год |

**Реалистичный годовой бюджет:** $140 (заявлено) + **$1240–4840 (скрытое деньги) + $7500–12500 (скрытое время при $50/ч) = $9000–17000/год** реальной стоимости владения. Из них только ~15% — железо и LLM, остальные 85% — операционные.

### 5.5. Топ-3 вопроса без ответа

1. **«Что делать, когда Anthropic/OpenAI/Google блокирует ключ по abuse review на 24–72 ч, и роевая логика не различает `429_exhausted` от `403_abuse`?»** Нет status code taxonomy, нет appeals-шаблонов, нет 2-account strategy.
2. **«Кто дежурит в 3 часа ночи, и что он физически успеет за 5 мин до восстановления? Runbook рассчитан на владельца-ИТ-шника.»** Нет 2-tier runbook, нет backup-человека, нет IAM с TTL, нет onboarding-чеклиста.
3. **«Что делать, когда OpenClaw проект будет заброшен, переименован, форкнут или сменит лицензию?»** Нет dependency matrix, нет escape-hatch (`manual_mode.sh`), нет форк-плана, нет мониторинга upstream.

---

## 6. Голос Security: модель угроз

### 6.1. Prompt injection — 5 сценариев (все реализуемы «из коробки»)

| Сценарий | Поверхность | Что получает атакующий | Митигация |
|---|---|---|---|
| **1. «Друг» шлёт в Telegram-бот инструкцию** | Telegram-бот без allowlist chat_id | RCE через `tmux send-keys`, утечка `context.db` и OpenClaw токена | allowlist `ALLOWED_CHAT_IDS`, санитайзер-парсер на 1–3 whitelisted-команды, LLM получает только JSON парсинга |
| **2. Email-вложение через himalaya** | himalaya → mime-парсер → LLM | Утечка `openclaw.json` (внутри токены всех 4 LLM) | `PrivateTmp=yes`, `ProtectHome=yes`, `ReadWritePaths=/var/lib/venya/inbox`, defusedxml, never передавать вложение в контекст |
| **3. Moysha++ как критик отравлен тем же входом** | Пакет передачи в свободной форме | Moysha++ исполняет отравленную команду при failover | `next_action_type` ∈ enum, whitelist роли преемника, `confirm(restrictions_hash, allowed_actions_list)` |
| **4. ssh-pull с standby-VPS шлёт отравленный context.db** | Standby-VPS скомпрометирован | При promote standby → primary, Venya Core исполняет «решения» из `decisions` | Ed25519-подписи Venya Core primary, read-only mount на standby, restore-only команда в `authorized_keys` |
| **5. OpenClaw `coding-agent` + skill `tmux` = shell как сервис** | OpenClaw + skill `tmux` | RCE на сервере через LLM, post-exploit = root | systemd sandbox: `User=openclaw`, `ProtectSystem=strict`, `ProtectHome=yes`, `NoNewPrivileges=yes`, `RestrictNamespaces=yes`; egress filter nftables |

### 6.2. Скомпрометация одной ноды = всего роя

| Компрометация | Что получает атакующий |
|---|---|
| **Venya Core** (RCE через sqlite3/requests) | Запись `epoch=999999, agent='evil'`, генерация `fencing token` для «нового лидера», все исполнители принимают |
| **`/var/lib/venya/context.db`** (нет шифрования at-rest) | Полный дамп: `outbox` (с email SEV-1, PII), `decisions`, `incidents`, `providers.daily_tokens` (косвенно API-ключи) |
| **ssh-pull ключ standby-VPS** | Lateral movement на VPS-1 как root, отравление `context.db` |
| **OpenClaw токен** (через RCE gateway или чтение EnvironmentFile) | Свой биллинг на счёт жертвы: до $15K в первые сутки (Sonnet без лимитов) |
| **Telegram-аккаунт** (SIM-swap, перехват SMS) | Все SEV-1/SMS-эквивалент, ложные HOLD/ESCALATE от имени бота |
| **NTP-сервер** (расхождение > 15 сек) | Ложный split-brain при работающей сети |

### 6.3. Insider threat (1 разработчик = SPOF безопасности)

1. **Потеря ноутбука с SSH-ключами** — v2 рекомендует ключи **без** passphrase, нет revocation-процедуры, нет hardware key. Потеря ноутбука = захват VPS-1 как root, чтение `context.db`, модификация `decisions` с backdoor, последующий RCE при failover.
2. **Компрометация credentials** — EnvironmentFile может быть `chmod 644` или в dotfile-backup репозитории, SMTP credentials в `/etc/msmtprc` без отдельного 2FA.
3. **Злой умысел** — нет tamper-evident logs, нет внешнего audit (digest на email, к которому разработчик не имеет доступа), нет separation of duties.

### 6.4. Утечка через LLM-провайдеров

v2 отправляет провайдерам:
1. **Промпты целиком**, включая `goal`, `state`, `restrictions`, `next_action` из пакета передачи — метаданные о содержимом внутреннего репозитория.
2. **decisions при failover** — Moysha++ (Gemini) получает доступ к решениям, которые принимал Izya-Deep (Sonnet), и наоборот.
3. **OpenClaw session-logs** — дословный дамп разговоров: внутренние имена хостов, IP standby-VPS, пути вроде `/var/lib/venya/context.db`, email-адреса, токены (если разработчик вставил в `restrictions`).
4. **OpenClaw analytics endpoint** (`model-usage`) — провайдер OpenClaw видит, какие модели, сколько токенов, в какое время, с какого IP. Timing-pattern раскрывает рабочий график «1 инженера».

**Митимизация (отсутствует в v2):** PII-фильтр на исходящие (presidio-analyzer или regex), отключить session-logs в проде, отключить analytics, opt-out из training для каждого провайдера, TLS pinning.

### 6.5. GDPR / ФЗ-152 / CCPA — 6 нарушений

1. **Нет правового основания** для обработки (GDPR Art. 6) — `outbox.recipient` (email, chat_id) — ПДн, без consent/legitimate interest/contract.
2. **Трансграничная передача в США/Китай без SCC** — Moysha++ (Google Gemini, US) + DeepSeek (Китай) + рекомендация Hetzner DE/FI = данные европейских пользователей в США/Китай **без** Standard Contractual Clauses и без Transfer Impact Assessment. Нарушение GDPR Chap. V.
3. **Нарушение ФЗ-152 ст. 18** для граждан РФ — нет локализации ПДн на сервере в РФ.
4. **Нет data retention policy** (GDPR Art. 5(1)(e), CCPA §1798.105) — `incidents` и `outbox` без ротации; право на удаление за 45 дней не реализовано.
5. **Security of processing** (GDPR Art. 32) — нет шифрования БД at-rest, нет MFA для SSH, нет audit log обращений к `context.db`. При утечке БД уведомление supervisory authority за 72 часа (Art. 33) невозможно — нет инструмента детектирования.
6. **Автоматическое принятие решений без human-in-the-loop** (GDPR Art. 22) — `HOLD`/`DEGRADED_*` режимы выбираются автоматически; если влияют на юридически значимые действия — запрещено.

### 6.6. Топ-3 атаки вне покрытия существующих рецензий

1. **«Отравление контекста через длительный планируемый простой».** Read-only доступ к VPS-1 + короткое окно write на standby при promote = отравленные `decisions` в БД. Тривиально, потому что v2 не подписывает записи.
2. **«LLM provider poisoning» через shared edge-infra.** Anthropic, OpenAI, Google делят Cloudflare, Fastly, AWS us-east-1. BGP hijack / DNS poisoning / TLS interception = все 3 провайдера падают одновременно, рой переходит на Ollama — а Ollama-модели тоже могут быть отравлены при `ollama pull`.
3. **«Telegram-бот как kill-switch для роя» (DoS через Bot API rate limit).** 30 ботов одновременно шлют одному «нашему» бот-аккаунту → rate-limit срабатывает → SEV-1 не доходят **именно в момент реального инцидента**. Аналогично email-канал: спам от имени нашего SMTP → IP-репутация падает → SEV-1 в spam.

---

## 7. Кросс-валидация: где три перспективы совпали

| Тезис | SRE | COO | Security |
|---|:---:|:---:|:---:|
| `flock` не решает distributed consensus | ✅ | — | — |
| ssh-pull 5 мин = потеря данных | ✅ | ✅ | — |
| Нет outbox для in-flight запросов | ✅ | — | — |
| Дедуп уведомлений семантически сломан | ✅ | ✅ | — |
| Backup-drill описан, не выполняется | ✅ | ✅ | — |
| NTP-мониторинг отсутствует | ✅ | ✅ | — |
| Alert-fatigue через 2 недели | ✅ | ✅ | — |
| 1 разработчик = SPOF | ✅ | ✅ | ✅ |
| Скрытые расходы не учтены | — | ✅ | — |
| Threat model отсутствует | — | — | ✅ |
| Prompt injection не рассмотрен | — | — | ✅ |
| GDPR/ФЗ-152 не рассмотрен | — | — | ✅ |
| Канальная избыточность недостаточна | — | ✅ | ✅ |
| OpenClaw SPOF без escape hatch | — | ✅ | ✅ |

**Где совпали все три:** один разработчик — это SPOF и для надёжности, и для безопасности, и для операций. Это центральная рекомендация всех трёх перспектив: **до запуска в прод нужно либо нанять backup-человека, либо передать эксплуатацию managed-service** (~$200–500/мес).

---

## 8. Минимальный жизнеспособный MVP после доработок

С учётом всех замечаний, MVP за 10–14 дней **реально**, но требует жёстких упрощений:

```
┌─────────────────────────────────────────────────────┐
│  Venya Core (Python, 1 процесс, VPS-1)              │
│  ├─ leader election — single instance,              │
│  │  systemd Restart=on-failure                      │
│  ├─ SQLite WAL, ed25519-подписи решений             │
│  ├─ outbox-pattern для in-flight запросов            │
│  ├─ circuit breaker для провайдеров                 │
│  └─ systemd sandbox: User=venya, ProtectHome=yes    │
├─────────────────────────────────────────────────────┤
│  Агенты (3 шт.):                                    │
│  ├─ Izya-Speedy: Claude Haiku 4.5                   │
│  ├─ Izya-Deep: Claude Sonnet 4.6                    │
│  └─ Moysha++: Gemini 2.5 Pro (другой провайдер)     │
├─────────────────────────────────────────────────────┤
│  Watchman (systemd-timer 30с, external Healthchecks) │
│  ├─ 3 проверки: Core жив, Gateway 200, БД пишется   │
│  ├─ alert: telegram (SEV-2/3), email+pushover (SEV-1)│
│  └─ inline ack в Telegram                           │
├─────────────────────────────────────────────────────┤
│  БД: SQLite WAL + litestream → Backblaze B2 EU      │
│  + ежедневный VACUUM INTO snapshot                   │
│  + verify_backup.sh в cron (PASS → 1 алерт/нед OK)  │
├─────────────────────────────────────────────────────┤
│  Каналы: Telegram (2 аккаунта) + email (Fastmail)   │
│  + Pushover для SEV-1                               │
├─────────────────────────────────────────────────────┤
│  Backup-человек: 1 человек, on-call rotation         │
│  + Bitwarden/Vault для ssh-ключей с TTL             │
└─────────────────────────────────────────────────────┘
```

**Ключевые отличия от v2:**
- 1 Venya Core (не 2 + арбитр)
- `litestream` вместо ssh-pull
- `ed25519`-подписи БД
- systemd-timer вместо cron
- 3 канала вместо 2 (Telegram основной + запасной + email + Pushover)
- 2 account Anthropic
- Backup-человек обязателен

---

## 9. Порядок внедрения (обновлённый)

| Этап | Дни | Что делается | Блокирует? |
|---|---|---|---|
| **E0. Threat model + IAM** | 1 | Документ угроз, IAM-роли, Bitwarden для backup-человека | Все остальные |
| **E1. Сервер + стек** | 1 | VPS, ufw, fail2ban, Python 3.12, Node.js 20, OpenClaw | E2–E6 |
| **E2. Backup-стратегия** | 1 | litestream → B2, daily VACUUM, verify_backup.sh | E3 |
| **E3. Venya Core** | 2 | ed25519-подписи, outbox, circuit breaker, systemd sandbox | E4–E6 |
| **E4. Агенты + маршрутизация** | 2 | 3 агента, table provider_priority | E5 |
| **E5. Watchman + каналы** | 1 | systemd-timer 30с, 3 проверки, Telegram (2 акка) + email + Pushover | E6 |
| **E6. Restore-drill + chaos** | 1 | Drill на test-VPS, chaos-test по чек-листу | E7 |
| **E7. Onboarding backup-человека** | 1 | 2 ч теории + 1 ч live-fire drill | E8 |
| **E8. Документация + runbook** | 0.5 | Decision tree, appeals-шаблоны, escalation contacts | — |
| **ИТОГО** | **10.5 дней** | | |

**После MVP (месяц 2–3):**
- Восстановление backup-drill как ритуал
- Калибровка Moysha++ (recalibrate уровень критики)
- Пересмотр бюджета на основе реального MTTD/MTTR
- Решение: оставаться на 1 инженере или брать SRE-фрилансера

---

## 10. Обязательные инварианты и проверки

| # | Инвариант | Проверка | Приоритет |
|---|-----------|----------|-----------|
| I1 | **В каждый момент ≤ 1 активный командир** | Один Venya Core, systemd Type=notify, /readyz перед promotion | P0 |
| I2 | **Решения в `decisions` подписаны Ed25519** | Verify при каждом read, не проходит → HOLD | P0 |
| I3 | **RPO ≤ 5 мин** | litestream replica lag, alert при > 60 сек | P0 |
| I4 | **Watchman шлёт ≤ 1 уведомление на инцидент** | Дедуп по `(incident_class, incident_id, channel)`, не по hash общему | P0 |
| I5 | **In-flight запросы переживают рестарт OpenClaw** | outbox-pattern с retry+idempotency | P0 |
| I6 | **All 4 LLM-providers не на одной инфраструктуре** | Разные cloud account, разные billing, разные AS egress | P0 |
| I7 | **Restore-drill проходит раз в неделю** | verify_backup.sh + cold-restore на test-VPS | P0 |
| I8 | **NTP offset ≤ 250 ms между VPS-1 и VPS-2** | chrony + alert | P1 |
| I9 | **Chaos-тесты в CI** | pytest на ephemeral VM | P1 |
| I10 | **Telegram-бот не может выполнить shell** | OpenClaw skill `tmux` отключён на уровне runtime | P0 |
| I11 | **OpenClaw egress только на LLM/Telegram** | nftables filter | P0 |
| I12 | **PII-фильтр на исходящие промпты** | presidio-analyzer или regex | P1 |
| I13 | **session-logs в проде отключены** | OpenClaw config | P1 |
| I14 | **Moysha++ на LLM, отличном от Deep и Speedy** | Другой провайдер, другой cloud account | P0 |
| I15 | **Backup-человек имеет read-only triage доступ** | Bitwarden ssh-key TTL 1ч | P0 |
| I16 | **Status page публичный** | Telegram-канал «Swarm Status» | P2 |
| I17 | **2-account strategy для Anthropic** | 2 cloud account, 2 billing | P0 |
| I18 | **Appeals templates готовы** | 3 файла в /root/venya/runbooks/ | P1 |
| I19 | **circuit breaker в Venya Core, не в агентах** | state machine CLOSED→OPEN→HALF_OPEN | P0 |
| I20 | **GDPR/ФЗ-152 compliance check раз в квартал** | DPA Anthropic/OpenAI/Google, retention policy | P2 |

---

## 11. Сводная таблица: замечание → риск → предлагаемое исправление → приоритет

| # | Замечание | Риск | Исправление | Приоритет |
|---|-----------|------|-------------|-----------|
| 1 | `flock` ≠ distributed consensus | Split-brain при partition | Один Venya Core + systemd Type=notify | **P0** |
| 2 | ssh-pull поверх живой SQLite | Corrupted WAL, потеря данных | `litestream` → S3-compatible + `VACUUM INTO` | **P0** |
| 3 | Дедуп уведомлений семантически сломан | Alert-fatigue, MTTD → 37 ч | `(incident_class, incident_id, channel)` ключ | **P0** |
| 4 | Нет outbox для OpenClaw | Потеря/дубль задач при рестарте | outbox-pattern + idempotency | **P0** |
| 5 | Threat model отсутствует | Prompt injection, утечка, GDPR | E0: документ угроз + Ed25519 + systemd sandbox | **P0** |
| 6 | 1 разработчик = SPOF | Отпуск/болезнь = потеря управления | Backup-человек + Bitwarden TTL + 2-tier runbook | **P0** |
| 7 | systemd auto-restart без `OnFailure=` | Crash-loop, рой стоит | `StartLimitBurst=5` + coredump + alert | P1 |
| 8 | NTP-мониторинг отсутствует | Ложный split-brain при расхождении часов | chrony + alert при offset > 250 ms | P1 |
| 9 | Chaos-тесты без ownership | Theatre of reliability | `trap` rollback + Healthchecks.io ping + on-call | P1 |
| 10 | Backup-drill не выполняется | «Бэкап есть, восстановиться не можем» | verify_backup.sh в cron, weekly drill | P0 |
| 11 | daily_tokens vs. abuse review не различимы | Appeals 24–72 ч не инициируются | Status code taxonomy + 2-account strategy | P0 |
| 12 | 4 канала не описаны (Telegram/email) | Канальный SPOF | 3 уровня: Pushover + запасной + публичный status | P1 |
| 13 | Runbook 5 bash-команд | Невозможно triage в 3 ч ночи | `triage.sh` + decision tree + контакт-карточка | P0 |
| 14 | OpenClaw SPOF без escape hatch | Зависимость от upstream | `openclaw.pin` + `manual_mode.sh` + мониторинг releases | P1 |
| 15 | ssh-pull ключ без ограничений | Компрометация VPS-2 = root на VPS-1 | `command="rsync --server ..."` в authorized_keys | P1 |
| 16 | Watchman 7 проверок | Alert-fatigue через 2 недели | 3 проверки в MVP + inline ack | P0 |
| 17 | Capacity planning / degraded-success | Moysha++ ловит постфактум | Калибровка Moysha на снижение quality, не только outages | P1 |
| 18 | Ротация секретов | Компрометация при утечке ноутбука | `etckeeper` + key passphrase + Bitwarden | P1 |
| 19 | Email-IP не прогрет | SEV-1 в spam | 2 недели прогрева + PTR/SPF/DKIM/DMARC | P1 |
| 20 | Telegram-бот без allowlist | Prompt injection через ЛС | `ALLOWED_CHAT_IDS` env + санитайзер-парсер | **P0** |
| 21 | OpenClaw без sandbox | RCE через prompt injection = root | `User=openclaw` + `ProtectHome=yes` + nftables egress | **P0** |
| 22 | LLM provider poisoning | Edge-infra compromise | Ed25519-подписи БД + verify Ollama blob hashes | P1 |
| 23 | Telegram Bot API DoS | Rate-limit исчерпан → SEV-1 не доходят | 2 аккаунта + Pushover как 3-й канал | P1 |
| 24 | GDPR Art. 6 (нет правового основания) | Штрафы до €20M или 4% оборота | Privacy notice + retention policy | P2 |
| 25 | GDPR Chap. V (трансграничная передача) | DeepSeek в Китае = нарушение | Отказаться от DeepSeek, или SCC + TIA | **P0** |
| 26 | ФЗ-152 ст. 18 (для РФ) | Штрафы + блокировка | Локализация ПДн граждан РФ на сервере в РФ | P2 (если SaaS в РФ) |
| 27 | GDPR Art. 32 (нет audit log) | Утечка БД не детектируется | auditd + tamper-evident log | P1 |
| 28 | GDPR Art. 22 (auto decisions) | Юридически значимые действия без human | Human-in-the-loop для SEV-1+HOLD | P2 |
| 29 | Скрытые расходы не учтены | Реально $9K–17K/год, не $140/мес | Заложить в бюджет: $200/мес операционные | P0 |
| 30 | Backup-человек не обучен | Первый же инцидент в 3 ч ночи = потеря данных | 2 ч теории + 1 ч live-fire drill + 1 ч shadowing | P0 |

---

## 12. Итоговое решение «совета директоров»

**Принять с обязательными доработками.**

v2 технически жизнеспособна, концепция рабочая, но **30 P0/P1 замечаний** должны быть закрыты **до** запуска в production. Из них **10 P0-блокеров** (помечены жирным в §11).

**Что принимается безусловно:**
- Ядро концепции (Venya Core без LLM, 3 агента, 4 провайдера, 1 пакет передачи, 2 канала).
- Бюджет ($50–120/мес на LLM) и сроки MVP (10–14 дней).
- Chaos-тесты как обязательная практика.
- Moysha++ как критик на другом провайдере.

**Что требует обязательной доработки (P0, до MVP):**
1. Заменить `flock` на single Venya Core + systemd `Type=notify`.
2. Заменить ssh-pull на `litestream` → S3-совместимое хранилище.
3. Переопределить дедуп уведомлений по `(incident_class, incident_id, channel)`.
4. Реализовать outbox-pattern для in-flight запросов.
5. Сделать threat model документом (E0), реализовать Ed25519-подписи `decisions`, systemd sandbox для OpenClaw, allowlist `chat_id` для Telegram-бота, egress-filter nftables.
6. Отказаться от DeepSeek для ПДн (GDPR) или провести TIA+SCC.
7. Обеспечить 2-account strategy для Anthropic.
8. Сократить Watchman до 3 проверок, добавить external Healthchecks.io + Venya Core сам алертит если Watchman молчит.
9. Внедрить restore-drill как еженедельный ритуал с verify_backup.sh в cron.
10. Найти backup-человека и провести onboarding.

**Что требует доработки в первые 3 месяца эксплуатации (P1):**
- Все остальные 19 замечаний из §11.
- Пересмотр бюджета на основе реального MTTD/MTTR.
- Решение: оставаться на 1 инженере или брать SRE/security-фрилансера.

**Что отклоняется:**
- 5-канальная схема в первой версии (но 3 уровня эскалации добавляются).
- 3-уровневая иерархия Izya-Speedy/Deep/Max.
- Автовыборы лидера.
- LLM-улучшатель формулировок.
- Открытие OpenClaw `coding-agent` skill и `tmux` skill в проде.

**Решающее правило:** центральный тезис v2 — «независимая защита не должна зависеть от той же инфраструктуры, что и LLM» — **не выполнен** в части операций и безопасности: 1 разработчик, 1 ssh-pull ключ, 1 OpenClaw binary, 1 Telegram-аккаунт, 1 msmtp-credentials. **Сначала people, потом quorum, потом роли.**

---

## Приложение А. Соответствие замечаний — три перспективы

| # | Замечание | SRE | COO | Sec |
|---|-----------|:---:|:---:|:---:|
| 1-4 | `flock`, ssh-pull, дедуп, outbox | ✅ | ✅ | — |
| 5 | Threat model | — | — | ✅ |
| 6 | 1 разработчик SPOF | ✅ | ✅ | ✅ |
| 7-9 | systemd, NTP, chaos ownership | ✅ | ✅ | — |
| 10 | Backup-drill | ✅ | ✅ | — |
| 11 | abuse review taxonomy | — | ✅ | — |
| 12-15 | Каналы, runbook, OpenClaw escape, ssh-pull ключ | — | ✅ | ✅ |
| 16-19 | Watchman 7→3, capacity, секреты, email-IP | ✅ | ✅ | — |
| 20-23 | Telegram allowlist, OpenClaw sandbox, LLM poisoning, Bot DoS | — | — | ✅ |
| 24-28 | GDPR/ФЗ-152 нарушения | — | — | ✅ |
| 29 | Скрытые расходы | — | ✅ | — |
| 30 | Backup-человек не обучен | ✅ | ✅ | — |

---

## Приложение B. Что НЕ вошло в ревью, но стоит обсудить отдельно

- **Экономика LLM-рой как продукта.** v2 описывает инфраструктуру, но не монетизацию. Если рой — это SaaS с пользователями, нужно отдельно: pricing, retention, support cost.
- **Observability как продукт.** Сейчас метрики внутренние. Если рой обслуживает внешних пользователей — нужен status page, метрики для клиентов, SLA/SLO-калькулятор.
- **Disaster Recovery в другом регионе/облаке.** Hetzner DE/FI + 1 standby = риск multi-AZ. Offsite backup в B2 EU — это страховка данных, не инфраструктуры.
- **On-call rotation через несколько людей.** При $140/мес бюджета — managed-service (Datadog/PagerDuty альтернативы) или 2-3 фрилансера с time-limited доступом.
- **Юридические аспекты автоматического failover.** Если преемник действует в юридически значимом контексте (платежи, медицина) — нужен human-in-the-loop и audit trail по каждому решению.
- **Open-source vs proprietary runtime.** Если OpenClaw форкнут — кто поддерживает? Сколько это стоит в год? 50% трудозатрат по rough estimate SRE-агента.
