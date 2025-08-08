from aiogram import Dispatcher
from aiogram.filters import Command

from bot.controllers.cabinet import cabinet, link, unlink
from bot.core.logger import log_function


@log_function("setup_cabinet_handlers")
def setup(dp: Dispatcher):
    dp.message.register(cabinet, Command("cabinet"))
    dp.message.register(link, Command("link"))
    dp.message.register(unlink, Command("unlink"))
