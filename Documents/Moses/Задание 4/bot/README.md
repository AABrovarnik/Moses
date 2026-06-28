# Teplyy Kontur — гибридный Telegram-бот

Чат-бот для компании «Тёплый контур» (строительство SIP-домов). Совмещает жёсткий сценарий (квалификация, кнопки, ветвление) и гибкий диалог через LLM (OpenRouter). Маршрутизация между режимами — по контексту и триггерам.

## Стек

- **aiogram 3.13** — Telegram-фреймворк.
- **aiosqlite** — состояние диалогов в SQLite.
- **httpx** — асинхронный клиент к OpenRouter.
- **OpenRouter API** — LLM для мягкого режима (модель по умолчанию `openai/gpt-4o-mini`).

## Структура

```
bot/
├── bot.py               # точка входа
├── config.py            # загрузка .env
├── storage.py           # SQLite-хранилище состояний
├── states.py            # FSM через aiogram
├── keyboards.py         # inline-кнопки
├── notifications.py     # webhook в чат менеджера
├── llm/
│   ├── client.py        # OpenRouter-клиент
│   └── prompts.py       # system prompt
├── handlers/
│   ├── hard.py          # жёсткий сценарий
│   └── soft.py          # мягкий сценарий (LLM)
├── deploy/
│   └── teplyy-kontur-bot.service
├── requirements.txt
└── .env.example
```

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # заполните своими ключами
python bot.py
```

## Развёртывание на VPS

Подробная инструкция — `Posts/2026-06-29-deploy-teplyy-kontur-bot-vps.md`.

Краткая версия:

```bash
scp -r bot/ root@<VPS_IP>:/opt/teplyy_kontur_bot
ssh root@<VPS_IP>
cd /opt/teplyy_kontur_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp deploy/teplyy-kontur-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now teplyy-kontur-bot
journalctl -u teplyy-kontur-bot -f
```

## Управление

```bash
systemctl status teplyy-kontur-bot   # статус
systemctl restart teplyy-kontur-bot  # перезапуск
journalctl -u teplyy-kontur-bot -n 100 --no-pager  # последние 100 строк лога
```

## Переменные окружения

| Имя | Что значит |
|---|---|
| `BOT_TOKEN` | токен от @BotFather |
| `OPENROUTER_API_KEY` | ключ OpenRouter для LLM |
| `OPENROUTER_MODEL` | модель (по умолчанию `openai/gpt-4o-mini`) |
| `MANAGER_CHAT_ID` | ID чата/пользователя для уведомлений о горячих лидах |

## Сценарий

1. `/start` → приветствие с 4 inline-кнопками.
2. «1 — Видео + PDF» → выдача лид-магнита, переход в мягкий режим.
3. «2 — Калькулятор» → ссылка на сайт + SMS-бонус.
4. «3 — Видеоконсультация» → 4 шага квалификации (тип дома, площадь, бюджет, участок) → ветвление «горячий / тёплый / холодный» → запись на видеоконсультацию (имя, телефон, время) → webhook менеджеру.
5. «4 — Просто спросить» → мягкий режим через LLM (ответы на типовые возражения).

Свободный текст в середине жёсткого сценария автоматически переключает на LLM. Возврат в жёсткий — по inline-кнопке или явной фразе «хочу записаться».