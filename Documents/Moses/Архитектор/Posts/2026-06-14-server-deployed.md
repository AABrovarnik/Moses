---
date: 2026-06-14
time: 19:31
status: в работе
project: C:\Users\aabro\Documents\Moses\Архитектор
session: server-deployment
related:
  - Posts/2026-06-14-swarm-audit.md
  - swarm/architecture-v3.md
  - swarm/server-spec-and-software.md
files_changed:
  - Posts/2026-06-14-server-deployed.md
  - Posts/_unfinished.md
  - Posts/journal.md
commands:
  - "ping -n 2 147.45.238.131"
---

# Сервер swarm развёрнут: 147.45.238.131

## Контекст
- Откуда пришло: пользователь сообщил — «сервер развернут по адресу 147.45.238.131».
- Что хотели получить: факт развёртывания зафиксирован как актив, обновлён `_unfinished.md`, понятен следующий шаг.

## Действия
1. Проверена сетевая связность: `ping 147.45.238.131` — 2/2, потери 0%, среднее 75 мс, TTL=50. Признак VPS-хостинга (Hetzner/OVH-диапазон).
2. **Не выполнялись** (нет данных): ssh-логин, опрос ОС/железа, проверка установленного стека, проверка systemd-юнитов, чтение `/etc/venya/`, сканирование открытых портов. Требуется ssh-доступ.

## Текущее состояние сервера (что нужно узнать)

| Параметр | Известно | Нужно уточнить |
|---|---|---|
| IP | 147.45.238.131 | ✓ |
| Хостер | неизвестно | по PTR/AS |
| ОС | неизвестно | по ssh |
| Железо (vCPU/RAM/диск) | неизвестно | по ssh, сверять с v3 §3.1 (Hetzner CCX 23) |
| Стек (Python 3.12, Node 20, OpenClaw) | неизвестно | по ssh, сверять с v3 §8 E1 |
| Домен / DNS | неизвестно | у пользователя |
| TLS-сертификаты | неизвестно | по ssh |
| Уже установлено (если что-то есть) | неизвестно | по ssh |
| OpenClaw закреплён (`/etc/venya/openclaw.pin`) | неизвестно | по ssh, критично для I8 |
| systemd-юниты для venya/openclaw/watchman | неизвестно | по ssh |
| /var/lib/venya/, /var/log/venya/ | неизвестно | по ssh |
| litestream сконфигурирован? | неизвестно | по ssh |
| nftables egress filter | неизвестно | по ssh |
| Timezone, NTP, chrony | неизвестно | по ssh, нужно для I13 |

## Артефакты
- Эта запись: `Posts/2026-06-14-server-deployed.md`

## Статус
в работе — сервер доступен по ICMP, состояние стека неизвестно, ssh-доступа у меня нет.

## Next steps
1. **Сверить сервер с v3 §3.1 бюджетом** — какой тариф куплен, совпадает ли с Hetzner CCX 23 (8 vCPU / 32 ГБ RAM, €30/мес)?
2. **Сверить с `server-spec-and-software.md`** — какие пункты ТЗ закрыты, какие нет.
3. **Определить, где мы в roadmap E1** — что уже сделано из E1 «Сервер + стек» (1 день): VPS, ufw, fail2ban, chrony, Python 3.12, Node.js 20, OpenClaw (закреплён).
4. **Проверить версию OpenClaw** — v3 требует 2026.6.1, закреплённую в `/etc/venya/openclaw.pin`. Если версия другая — обновить/откатить до пина **до** любых дальнейших шагов.
5. **Проверить systemd sandbox** для OpenClaw (I8) — `ProtectSystem=strict`, `ProtectHome=yes`, `NoNewPrivileges=yes`, `ReadWritePaths=/var/lib/venya/spool`.
6. **Проверить nftables egress** — allowlist IP-диапазонов Anthropic/OpenAI/Google/Telegram/Ollama.
7. **Проверить litestream** — статус реплики в Backblaze B2 EU, lag.
8. **Запросить ssh-доступ** (отдельным сообщением пользователю) для верификации 1–7.

## Открытые вопросы пользователю

- **Хостер**: Hetzner/OVH/другой? (для PTR/SPF/DKIM настройки, и для проверки соответствия v3 §3.1)
- **Тариф**: какой объём (vCPU, RAM, диск, цена/мес)?
- **Что уже развёрнуто**: «развёрнут» — это голая ОС, или уже с Python/Node/OpenClaw/litestream/systemd-юнитами?
- **Домен**: есть? (для TLS и email-DNS)
- **ssh-доступ**: могу ли я подключаться (отдельный ключ или через ваш jump-host)? Сейчас мне ssh не доступен.
- **2-й аккаунт Anthropic** (I18): заведён?
- **2-й Telegram-бот** (I9, §2.6): заведён?
- **Bitwarden-организация** (I11, §2.9): создана?
- **Backblaze B2 EU bucket** (I3): создан?
