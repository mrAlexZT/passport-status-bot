from aiogram import Dispatcher

from bot.controllers.cabinet import cabinet, link, unlink
from bot.core.logger import log_function


@log_function("setup_cabinet_handlers")
def setup(dp: Dispatcher):
    dp.register_message_handler(cabinet, commands=["cabinet"], state="*")
    dp.register_message_handler(link, commands=["link"], state="*")
    dp.register_message_handler(unlink, commands=["unlink"], state="*")
