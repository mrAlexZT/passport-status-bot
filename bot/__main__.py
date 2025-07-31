import datetime
import matplotlib.pyplot as plt
import io

from beanie import init_beanie

from aiogram import types
from aiogram.dispatcher import Dispatcher

from aiogram.contrib.fsm_storage.memory import MemoryStorage

import asyncio
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.bot_instance import bot, loop, version as bot_version, link, codename

from bot.core.database import db

from bot.core.models.application import ApplicationModel
from bot.core.models.push import PushModel
from bot.core.models.user import SubscriptionModel, UserModel
from bot.core.models.request_log import RequestLog
from bot.core.scheduler import scheduler_job

from bot.handlers import setup as handlers_setup
from bot.middlewares.antiflood import ThrottlingMiddleware, rate_limit
from bot.middlewares.debug import LoggerMiddleware

from bot.core.config import settings
from bot.core.notify_admin import notify_admin

scheduler = AsyncIOScheduler()

dp = Dispatcher(
    bot,
    loop=loop,
    storage=MemoryStorage(),
)


async def startup(dp: Dispatcher):
    commands = [
        types.BotCommand(command="/start", description="Почати роботу з ботом"),
        types.BotCommand(command="/help", description="Допомога"),
        types.BotCommand(
            command="/policy", description="Політика бота та конфіденційність"
        ),
        types.BotCommand(command="/cabinet", description="Персональний кабінет"),
        types.BotCommand(command="/link", description="Прив'язати ідентифікатор"),
        types.BotCommand(
            command="/unlink",
            description="Відв'язати ідентифікатор та видалити профіль",
        ),
        types.BotCommand(command="/subscribe", description="Підписатися на сповіщення"),
        types.BotCommand(
            command="/unsubscribe", description="Відписатися від сповіщень"
        ),
        types.BotCommand(command="/subscriptions", description="Список підписок"),
        types.BotCommand(command="/update", description="Оновити статус заявки вручну"),
        types.BotCommand(
            command="/push", description="Підписатися на сповіщення через NTFY.sh"
        ),
        types.BotCommand(
            command="/dump",
            description="Отримати весь дамп доступних даних на ваші підписки",
        ),
        types.BotCommand(command="/ping", description="Перевірити чи працює бот"),
        types.BotCommand(command="/time", description="Поточний час сервера"),
        types.BotCommand(command="/version", description="Версія бота"),
    ]

    await bot.set_my_commands(commands)
    await init_beanie(
        database=db,
        document_models=[
            UserModel,
            SubscriptionModel,
            ApplicationModel,
            PushModel,
            RequestLog,
        ],
    )
    await notify_admin(f"🚀 Bot started at {datetime.datetime.now().isoformat()}")


async def shutdown(dp: Dispatcher):
    await notify_admin(f"🛑 Bot stopped at {datetime.datetime.now().isoformat()}")


@dp.message_handler(commands=["ping"])
@rate_limit(5, "ping")
async def ping(message: types.Message):
    await message.answer("Pong!")


@dp.message_handler(commands=["time"])
async def time(message: types.Message):
    await message.answer(f"Server time is: {str(datetime.datetime.now())}")


@dp.message_handler(commands=["version"])
async def version(message: types.Message):
    await message.answer(
        f"Bot version:\n*v{bot_version}*\n\nSource Code:\n[mrAlexZT/passport-status-bot/{link.split('/')[-1]}]({link})\n\nCodename:\n*{codename}*",
        parse_mode="Markdown",
    )


async def set_user_commands(user_id):
    admin_commands = [
        types.BotCommand(command="/start", description="Почати роботу з ботом"),
        types.BotCommand(command="/help", description="Допомога"),
        types.BotCommand(command="/policy", description="Політика бота та конфіденційність"),
        types.BotCommand(command="/cabinet", description="Персональний кабінет"),
        types.BotCommand(command="/link", description="Прив'язати ідентифікатор"),
        types.BotCommand(command="/unlink", description="Відв'язати ідентифікатор та видалити профіль"),
        types.BotCommand(command="/subscribe", description="Підписатися на сповіщення"),
        types.BotCommand(command="/unsubscribe", description="Відписатися від сповіщень"),
        types.BotCommand(command="/subscriptions", description="Список підписок"),
        types.BotCommand(command="/update", description="Оновити статус заявки вручну"),
        types.BotCommand(command="/push", description="Підписатися на сповіщення через NTFY.sh"),
        types.BotCommand(command="/dump", description="Отримати весь дамп доступних даних на ваші підписки"),
        types.BotCommand(command="/ping", description="Перевірити чи працює бот"),
        types.BotCommand(command="/time", description="Поточний час сервера"),
        types.BotCommand(command="/version", description="Версія бота"),
        types.BotCommand(command="/broadcast", description="Розсилка"),
        types.BotCommand(command="/get_out_txt", description="Отримати out.txt"),
        types.BotCommand(command="/stats", description="Статистика"),
        types.BotCommand(command="/stats_graph", description="Графік запитів"),
    ]
    user_commands = [cmd for cmd in admin_commands if cmd.command not in ["/broadcast", "/get_out_txt", "/stats", "/stats_graph"]]
    if str(user_id) == str(settings.ADMIN_ID):
        await bot.set_my_commands(admin_commands, scope=types.BotCommandScopeChat(user_id))
    else:
        await bot.set_my_commands(user_commands, scope=types.BotCommandScopeChat(user_id))


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await set_user_commands(message.from_user.id)
    # ...existing code for /start...


@dp.message_handler(commands=["broadcast"])
async def broadcast(message: types.Message):
    if str(message.from_user.id) != str(settings.ADMIN_ID):
        await message.answer("You are not admin!")
        return
    excepted_users = message.text.split(" ")
    users = await UserModel.all().to_list()
    print(users)
    for user in users:
        try:
            if (
                str(user.telgram_id) == settings.ADMIN_ID
                or str(user.telgram_id) in excepted_users
            ):
                continue
            if message.reply_to_message:
                await bot.copy_message(
                    user.telgram_id,
                    message.chat.id,
                    message.reply_to_message.message_id,
                )
        except Exception:
            with open("out_blocked.txt", "a") as f:
                print(f"User {user.telgram_id} blocked bot", file=f)


@dp.message_handler(commands=["get_out_txt"])
async def get_out_txt(message: types.Message):
    if str(message.from_user.id) != str(settings.ADMIN_ID):
        await message.answer("You are not admin!")
        return
    with open("out.txt", "r") as f:
        await message.answer_document(f)


@dp.message_handler(commands=["stats"])
async def stats(message: types.Message):
    if str(message.from_user.id) != str(settings.ADMIN_ID):
        await message.answer("You are not admin!")
        return
    user_count = await UserModel.count()
    subscription_count = await SubscriptionModel.count()
    request_count = await RequestLog.count()
    await message.answer(
        f"📊 Statistics:\n\n"
        f"👤 Users: {user_count}\n"
        f"🔔 Subscriptions: {subscription_count}\n"
        f"📨 Requests: {request_count}"
    )


@dp.message_handler(commands=["stats_graph"])
async def stats_graph(message: types.Message):
    if str(message.from_user.id) != str(settings.ADMIN_ID):
        await message.answer("You are not admin!")
        return
    # Aggregate requests per day
    logs = await RequestLog.find_all().to_list()
    from collections import Counter
    from datetime import datetime
    days = [log.timestamp.date() for log in logs]
    counter = Counter(days)
    if not counter:
        await message.answer("No request data available.")
        return
    days_sorted = sorted(counter.keys())
    counts = [counter[day] for day in days_sorted]
    # Plot
    plt.figure(figsize=(8,4))
    plt.plot(days_sorted, counts, marker='o')
    plt.title('Requests per day')
    plt.xlabel('Date')
    plt.ylabel('Requests')
    plt.grid(True)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    await message.answer_photo(photo=buf, caption="Requests per day")
    buf.close()
    plt.close()


def main():
    # dp.middleware.setup(LoggerMiddleware())
    dp.middleware.setup(ThrottlingMiddleware())
    scheduler.add_job(
        scheduler_job,
        "interval",
        hours=1,
    )
    scheduler.start()
    handlers_setup.setup(dp)
    try:
        executor.start_polling(
            dp,
            loop=loop,
            skip_updates=True,
            on_startup=startup,
            on_shutdown=shutdown,
        )
    except Exception as e:
        loop.run_until_complete(notify_admin(f"❗️ Bot error: {e}"))
        raise


if __name__ == "__main__":
    main()
