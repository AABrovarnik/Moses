import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from storage import init_db
from handlers import hard, soft
from notifications import shutdown_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(hard.router)
dp.include_router(soft.router)


async def main():
    await init_db()
    logging.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await shutdown_bot()


if __name__ == "__main__":
    asyncio.run(main())