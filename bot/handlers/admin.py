from aiogram import Dispatcher

from bot.controllers.admin import users_list, cleanup_db, cleanup_callback


def setup(dp: Dispatcher):
    """Register admin command handlers."""
    dp.register_message_handler(users_list, commands=["users"], state="*")
    dp.register_message_handler(cleanup_db, commands=["cleanup"], state="*")
    dp.register_callback_query_handler(cleanup_callback, lambda c: c.data.startswith("cleanup_"), state="*")