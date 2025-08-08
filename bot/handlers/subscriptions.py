from aiogram import Dispatcher
from aiogram.filters import Command

from bot.controllers.subscriptions import (
    subscribe,
    unsubscribe,
    subscriptions,
    manual_application_update,
    enable_push,
    dump_subscriptions,
)
from bot.core.logger import log_function


@log_function("setup_subscriptions_handlers")
def setup(dp: Dispatcher):
    dp.message.register(subscribe, Command("subscribe"))
    dp.message.register(unsubscribe, Command("unsubscribe"))
    dp.message.register(subscriptions, Command("subscriptions"))
    dp.message.register(manual_application_update, Command("update"))
    dp.message.register(enable_push, Command("push"))
    dp.message.register(dump_subscriptions, Command("dump"))
