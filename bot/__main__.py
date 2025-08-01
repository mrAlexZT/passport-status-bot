            f"📨 Requests: {request_count}\n"
            f"🚨 Errors today: {error_count}"
        )
    except Exception as e:
        log_error("Stats command failed", message.from_user.id, e)
try:
        log_info("Bot shutdown initiated")
        await notify_admin(f"🛑 Bot stopped at {datetime.datetime.now().isoformat()}")
@log_function("stats_graph_command")
        log_info("Bot shutdown completed successfully")
    except Exception as e:
        log_error("Bot shutdown failed", exception=e)
import datetime
    try:
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
    except Exception as e:
        log_error("Stats graph command failed", message.from_user.id, e)
from aiogram.utils import executor
from bot.core.models.application import ApplicationModel
@dp.message_handler(commands=["logs"])
    try:
        log_info("Initializing bot")
        dp.middleware.setup(LoggerMiddleware())  # Enable logger middleware
        dp.middleware.setup(ThrottlingMiddleware())
        scheduler.add_job(
            scheduler_job,
            "interval",
            hours=1,
        )
        scheduler.start()
        handlers_setup.setup(dp)

        if not logs_dir.exists():
            await message.answer("📁 Директорія з логами не знайдена")
            return

        today_log = logs_dir / f"bot_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        error_log = logs_dir / f"errors_{datetime.datetime.now().strftime('%Y%m%d')}.log"

        if today_log.exists():
            with open(today_log, 'r', encoding='utf-8') as f:
                content = f.read()
                # Get last 50 lines
                lines = content.split('\n')
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                recent_content = '\n'.join(recent_lines)

                if len(recent_content) > 4000:  # Telegram message limit
                error_content = f.read()
                if error_content.strip():
                    error_lines = error_content.split('\n')
                    recent_errors = error_lines[-20:] if len(error_lines) > 20 else error_lines


                else:
                    await message.answer("✅ Помилок не знайдено")
    except Exception as e:
        await message.answer("❌ Помилка при отриманні логів")
            types.BotCommand(command="/start", description="Почати роботу з ботом"),
            types.BotCommand(command="/help", description="Допомога"),
            types.BotCommand(command="/subscribe", description="Підписатися на сповіщення"),
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.bot_instance import bot, loop, version as bot_version, link, codename

from bot.core.database import db

            types.BotCommand(
            ),
from bot.core.models.user import SubscriptionModel, UserModel
from bot.core.models.request_log import RequestLog
from bot.core.scheduler import scheduler_job
                description="Отримати весь дамп доступних даних на ваші підписки",
from bot.handlers import setup as handlers_setup
from bot.middlewares.antiflood import ThrottlingMiddleware, rate_limit
from bot.middlewares.debug import LoggerMiddleware
        ]
from bot.core.config import settings
from bot.core.notify_admin import notify_admin
from bot.core.logger import global_logger, log_function, log_error, log_info
        log_info("Bot commands set successfully")
scheduler = AsyncIOScheduler()
                PushModel,
dp = Dispatcher(
    bot,
    loop=loop,
    storage=MemoryStorage(),
)
        )

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return str(user_id) == str(settings.ADMIN_ID)


@log_function("startup")

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
    if is_admin(user_id):
        await bot.set_my_commands(admin_commands, scope=types.BotCommandScopeChat(user_id))
    else:
        await bot.set_my_commands(user_commands, scope=types.BotCommandScopeChat(user_id))


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await set_user_commands(message.from_user.id)
    # ...existing code for /start...


@dp.message_handler(commands=["broadcast"])
async def broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("You are not admin!")
        return
    excepted_users = message.text.split(" ")
    users = await UserModel.all().to_list()
    print(users)
    for user in users:
        try:
            if is_admin(user.telgram_id) or str(user.telgram_id) in excepted_users:
                continue
            if message.reply_to_message:
    try:
        log_info("Bot shutdown initiated")
        await notify_admin(f"🛑 Bot stopped at {datetime.datetime.now().isoformat()}")
        log_info("Bot shutdown completed successfully")
    except Exception as e:
        log_error("Bot shutdown failed", exception=e)
                await bot.copy_message(
                    user.telgram_id,
                    message.chat.id,
                    message.reply_to_message.message_id,
@log_function("ping_command")
                )
    try:
        await message.answer("Pong!")
    except Exception as e:
        log_error("Ping command failed", message.from_user.id, e)
            with open("out_blocked.txt", "a") as f:
                print(f"User {user.telgram_id} blocked bot", file=f)

@log_function("time_command")

    try:
        await message.answer(f"Server time is: {str(datetime.datetime.now())}")
    except Exception as e:
        log_error("Time command failed", message.from_user.id, e)
async def get_out_txt(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("You are not admin!")
@log_function("version_command")
        return
    try:
        await message.answer(
            f"Bot version:\n*v{bot_version}*\n\nSource Code:\n[mrAlexZT/passport-status-bot/{link.split('/')[-1]}]({link})\n\nCodename:\n*{codename}*",
            parse_mode="Markdown",
        )
    except Exception as e:
        log_error("Version command failed", message.from_user.id, e)


@dp.message_handler(commands=["toggle_logging"])
async def toggle_logging(message: types.Message):
    """Admin command to enable/disable logging"""
    try:
        result = global_logger.toggle_logging(message.from_user.id)
        await message.answer(result)
    except Exception as e:
        log_error("Toggle logging command failed", message.from_user.id, e)
        await message.answer("❌ Помилка при зміні налаштувань логування")


@dp.message_handler(commands=["logs"])
async def get_logs(message: types.Message):
    """Admin command to get recent logs"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Тільки адміністратор може переглядати логи")
        return

    try:
        from pathlib import Path

        logs_dir = Path("logs")
        if not logs_dir.exists():
            await message.answer("📁 Директорія з логами не знайдена")
            return

        today_log = logs_dir / f"bot_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        error_log = logs_dir / f"errors_{datetime.datetime.now().strftime('%Y%m%d')}.log"

        if today_log.exists():
            with open(today_log, 'r', encoding='utf-8') as f:
                content = f.read()
                # Get last 50 lines
                lines = content.split('\n')
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                recent_content = '\n'.join(recent_lines)

                if len(recent_content) > 4000:  # Telegram message limit
                    recent_content = recent_content[-4000:]

                await message.answer(f"📊 Останні записи логів:\n\n```\n{recent_content}\n```", parse_mode="Markdown")

        if error_log.exists():
            with open(error_log, 'r', encoding='utf-8') as f:
                error_content = f.read()
                if error_content.strip():
                    error_lines = error_content.split('\n')
                    recent_errors = error_lines[-20:] if len(error_lines) > 20 else error_lines
                    error_text = '\n'.join(recent_errors)

                    if len(error_text) > 4000:
                        error_text = error_text[-4000:]

                    await message.answer(f"🚨 Останні помилки:\n\n```\n{error_text}\n```", parse_mode="Markdown")
                else:
                    await message.answer("✅ Помилок не знайдено")
    except Exception as e:
        log_error("Get logs command failed", message.from_user.id, e)
        await message.answer("❌ Помилка при отриманні логів")
@dp.message_handler(commands=["stats"])
async def stats(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("You are not admin!")
        return
    user_count = await UserModel.count()
    subscription_count = await SubscriptionModel.count()
    request_count = await RequestLog.count()
    await message.answer(
        f"📊 Statistics:\n\n"
        f"👤 Users: {user_count}\n"
        types.BotCommand(command="/unsubscribe", description="Відписатися від сповіщень"),
        types.BotCommand(command="/subscriptions", description="Список підписок"),
        types.BotCommand(command="/update", description="Оновити статус заявки вручну"),
        types.BotCommand(command="/push", description="Підписатися на сповіщення через NTFY.sh"),
        f"🔔 Subscriptions: {subscription_count}\n"
        f"📨 Requests: {request_count}"
    )


@dp.message_handler(commands=["stats_graph"])
async def stats_graph(message: types.Message):
    if not is_admin(message.from_user.id):
        types.BotCommand(command="/toggle_logging", description="Увімкнути/вимкнути логування"),
        types.BotCommand(command="/logs", description="Переглянути логи"),
        await message.answer("You are not admin!")
    user_commands = [cmd for cmd in admin_commands if cmd.command not in ["/broadcast", "/get_out_txt", "/stats", "/stats_graph", "/toggle_logging", "/logs"]]
    # Aggregate requests per day
    logs = await RequestLog.find_all().to_list()
    from collections import Counter
    from datetime import datetime
    days = [log.timestamp.date() for log in logs]
    counter = Counter(days)
    if not counter:
@log_function("start_command")
        await message.answer("No request data available.")
    try:
        await set_user_commands(message.from_user.id)
        # Add your existing start command logic here
        await message.answer("Бот запущено! Використовуйте команди для роботи.")
    except Exception as e:
        log_error("Start command failed", message.from_user.id, e)
    counts = [counter[day] for day in days_sorted]
    # Plot
    plt.figure(figsize=(8,4))
@log_function("broadcast_command")
    plt.plot(days_sorted, counts, marker='o')
    plt.title('Requests per day')
    plt.xlabel('Date')
    plt.ylabel('Requests')
    try:
        excepted_users = message.text.split(" ")
        users = await UserModel.all().to_list()
        log_info(f"Broadcasting message to {len(users)} users")

        success_count = 0
        blocked_count = 0

        for user in users:
            try:
                if is_admin(user.telgram_id) or str(user.telgram_id) in excepted_users:
                    continue
                if message.reply_to_message:
                    await bot.copy_message(
                        user.telgram_id,
                        message.chat.id,
                        message.reply_to_message.message_id,
                    )
                    success_count += 1
            except Exception as e:
                blocked_count += 1
                log_error(f"Failed to send broadcast to user {user.telgram_id}", exception=e)
                with open("out_blocked.txt", "a") as f:
                    print(f"User {user.telgram_id} blocked bot", file=f)

        log_info(f"Broadcast completed: {success_count} sent, {blocked_count} blocked")
        await message.answer(f"📢 Розсилка завершена:\n✅ Надіслано: {success_count}\n❌ Заблоковано: {blocked_count}")
    except Exception as e:
        log_error("Broadcast command failed", message.from_user.id, e)
    dp.middleware.setup(ThrottlingMiddleware())
    scheduler.add_job(
        scheduler_job,
@log_function("get_out_txt_command")
        "interval",
        hours=1,
    )
    scheduler.start()
    try:
        with open("out.txt", "r") as f:
            await message.answer_document(f)
    except Exception as e:
        log_error("Get out.txt command failed", message.from_user.id, e)
        log_info("Starting bot polling")
        executor.start_polling(
            dp,
@log_function("stats_command")
            loop=loop,
            skip_updates=True,
            on_startup=startup,
            on_shutdown=shutdown,
    try:
        user_count = await UserModel.count()
        subscription_count = await SubscriptionModel.count()
        request_count = await RequestLog.count()

        # Count errors from logs if available
        error_count = 0
        try:
            from pathlib import Path
            error_log = Path("logs") / f"errors_{datetime.datetime.now().strftime('%Y%m%d')}.log"
            if error_log.exists():
                with open(error_log, 'r', encoding='utf-8') as f:
                    error_count = len([line for line in f if line.strip()])
        except:
            pass

        await message.answer(
            f"📊 Statistics:\n\n"
            f"👤 Users: {user_count}\n"
            f"🔔 Subscriptions: {subscription_count}\n"
