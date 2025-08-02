from aiogram import Dispatcher

from bot.core.logger import log_function
from bot.handlers import start, message, cabinet, subscriptions, admin


@log_function("setup_handlers")
def setup(dp: Dispatcher):
    start.setup(dp)
    message.setup(dp)
    cabinet.setup(dp)
    subscriptions.setup(dp)
    admin.setup(dp)
