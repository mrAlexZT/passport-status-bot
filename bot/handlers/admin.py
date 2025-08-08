from aiogram import Dispatcher
from aiogram.filters import Command

from bot.controllers.admin import users_list, cleanup_db, cleanup_callback


def setup(dp: Dispatcher):
    """Register admin command handlers."""
    dp.message.register(users_list, Command("users"))
    dp.message.register(cleanup_db, Command("cleanup"))
    dp.callback_query.register(cleanup_callback, lambda c: c.data.startswith("cleanup_"))