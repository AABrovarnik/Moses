from aiogram import Bot
from config import MANAGER_CHAT_ID, BOT_TOKEN

_bot: Bot | None = None


def _get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=BOT_TOKEN)
    return _bot


async def notify_manager(payload: dict):
    if not MANAGER_CHAT_ID:
        return
    if payload.get("type") == "escalation":
        text = (
            f"[эскалация] {payload.get('reason', 'unknown')}\n"
            f"Текст: {payload.get('text', '')}"
        )
    else:
        v = payload
        text = (
            "[горячий] SIP-лид\n"
            f"Имя: {v.get('name', '—')}\n"
            f"Телефон: {v.get('phone', '—')}\n"
            f"Время: {v.get('meeting_time', '—')}\n"
            f"Тип дома: {v.get('house_type', '—')}\n"
            f"Площадь: {v.get('area', '—')}\n"
            f"Бюджет: {v.get('budget', '—')}\n"
            f"Участок: {v.get('land', '—')}"
        )

    try:
        await _get_bot().send_message(MANAGER_CHAT_ID, text)
    except Exception as e:
        print(f"notify_manager error: {e}")


async def shutdown_bot():
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None