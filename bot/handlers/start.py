from aiogram import Dispatcher
from aiogram.filters import Command
from bot.controllers.start import start, policy, help
from bot.core.logger import log_function


@log_function("setup_start_handlers")
def setup(dp: Dispatcher):
    dp.message.register(start, Command("start"))
    dp.message.register(policy, Command("policy"))
    dp.message.register(help, Command("help"))
