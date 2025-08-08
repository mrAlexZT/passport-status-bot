import asyncio
from aiogram import Bot
from bot.core.config import settings
from bot.core.logger import log_function


@log_function("notify_admin")
async def notify_admin(text: str):
    admin_id = getattr(settings, "ADMIN_ID", None)
    token = getattr(settings, "TOKEN", None)
    if not admin_id or not token:
        return
    try:
        bot = Bot(token=token)
        await bot.send_message(chat_id=admin_id, text=text)
        await bot.session.close()
    except Exception as e:
        # Optionally log this error somewhere
        pass
