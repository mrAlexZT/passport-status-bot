from aiogram import Dispatcher

from bot.controllers.admin import users_list


def setup(dp: Dispatcher):
    """Register admin command handlers."""
    dp.register_message_handler(users_list, commands=["users"], state="*")