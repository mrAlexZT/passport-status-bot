# Standard library imports
import asyncio
import datetime
import io
from collections import Counter
from pathlib import Path

# Third party imports
import matplotlib.pyplot as plt
from aiogram import types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from beanie import init_beanie

# Local application imports
from bot.bot_instance import (
    bot, loop, bot_version, bot_link,
    update_version, get_bot_version
)
from bot.core.config import settings
from bot.core.database import db
from bot.core.constants import VERSION_ERROR, VERSION_FORMAT, VERSION_UPDATE_ERROR
from bot.core.logger import global_logger, log_function, log_error, log_info
from bot.core.models.application import ApplicationModel
from bot.core.models.push import PushModel
from bot.core.models.request_log import RequestLog
from bot.core.utils import admin_permission_check, get_application_by_session_id
from bot.core.models.user import SubscriptionModel, UserModel
from bot.core.notify_admin import notify_admin
from bot.core.scheduler import scheduler_job
from bot.handlers import setup as handlers_setup
from bot.middlewares.antiflood import ThrottlingMiddleware, rate_limit
from bot.middlewares.debug import LoggerMiddleware

scheduler = AsyncIOScheduler()

dp = Dispatcher(
    bot,
    loop=loop,
    storage=MemoryStorage(),
)

# --- Command Constants ---
ADMIN_COMMANDS = [
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
    types.BotCommand(command="/toggle_logging", description="Увімкнути/вимкнути логування"),
    types.BotCommand(command="/logs", description="Переглянути логи"),
    types.BotCommand(command="/users", description="Список користувачів"),
    types.BotCommand(command="/cleanup", description="Очистити базу даних"),
]
ADMIN_ONLY_COMMANDS = {"/broadcast", "/get_out_txt", "/stats", "/stats_graph", "/toggle_logging", "/logs", "/users", "/cleanup"}


def get_user_commands(is_admin: bool) -> list[types.BotCommand]:
    """Return the list of commands for a user depending on admin status."""
    if is_admin:
        return ADMIN_COMMANDS
    return [cmd for cmd in ADMIN_COMMANDS if cmd.command not in ADMIN_ONLY_COMMANDS]


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return str(user_id) == str(settings.ADMIN_ID)


def read_log_tail(log_path: Path, lines: int = 50) -> str:
    """Read the last N lines from a log file, return as a string."""
    if not log_path.exists():
        return ""
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()
        split_lines = content.split('\n')
        tail = split_lines[-lines:] if len(split_lines) > lines else split_lines
        return '\n'.join(tail)


@log_function("startup")
async def startup(dp: Dispatcher):
    try:
        log_info("Bot startup initiated")
        # Use default user commands (non-admin) for initial setup
        commands = get_user_commands(is_admin=False)
        await bot.set_my_commands(commands)
        log_info("Bot commands set successfully")

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
        log_info("Database initialized successfully")

        await notify_admin(f"🚀 Bot started at {datetime.datetime.now().isoformat()}")
        log_info("Bot startup completed successfully")
    except Exception as e:
        log_error("Bot startup failed", exception=e)
        await notify_admin(f"❌ Bot startup failed: {str(e)}")
        raise


@log_function("shutdown")
async def shutdown(dp: Dispatcher):
    try:
        log_info("Bot shutdown initiated")
        await notify_admin(f"🛑 Bot stopped at {datetime.datetime.now().isoformat()}")
        log_info("Bot shutdown completed successfully")
    except Exception as e:
        log_error("Bot shutdown failed", exception=e)


@dp.message_handler(commands=["ping"])
@rate_limit(5, "ping")
@log_function("ping_command")
async def ping(message: types.Message):
    try:
        await message.answer("Pong!")
    except Exception as e:
        log_error("Ping command failed", message.from_user.id, e)


@dp.message_handler(commands=["time"])
@log_function("time_command")
async def time(message: types.Message):
    try:
        await message.answer(f"Server time is: {str(datetime.datetime.now())}")
    except Exception as e:
        log_error("Time command failed", message.from_user.id, e)


@dp.message_handler(commands=["version"])
@log_function("version_command")
async def version(message: types.Message):
    """Show bot version information."""
    try:
        # Force version check
        await update_version()

        bot_version = await get_bot_version()
        log_info(f"Bot version: {bot_version}")
        
        # Format version info
        version_text = VERSION_FORMAT.format(
            version=bot_version,
            link=bot_link
        ) if bot_version else VERSION_ERROR
        
        await message.answer(
            version_text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        log_error("Version command failed", message.from_user.id, e)
        await message.answer(VERSION_UPDATE_ERROR)


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
    if not await admin_permission_check(message):
        return

    try:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            await message.answer("📁 Директорія з логами не знайдена")
            return

        from bot.core.logger import get_log_filename
        today_log = logs_dir / get_log_filename("bot")
        error_log = logs_dir / get_log_filename("errors")

        if today_log.exists():
            recent_content = read_log_tail(today_log, 50)
            if len(recent_content) > 4000:  # Telegram message limit
                recent_content = recent_content[-4000:]

            await message.answer(f"📊 Останні записи логів:\n\n```\n{recent_content}\n```", parse_mode="Markdown")

        if error_log.exists():
            error_content = read_log_tail(error_log, 20)
            if error_content.strip():
                if len(error_content) > 4000:
                    error_content = error_content[-4000:]

                await message.answer(f"🚨 Останні помилки:\n\n```\n{error_content}\n```", parse_mode="Markdown")
            else:
                await message.answer("✅ Помилок не знайдено")
    except Exception as e:
        log_error("Get logs command failed", message.from_user.id, e)
        await message.answer("❌ Помилка при отриманні логів")


async def set_user_commands(user_id: int) -> None:
    """Set the list of commands for a user depending on admin status."""
    try:
        commands = get_user_commands(is_admin(user_id))
        await bot.set_my_commands(commands, scope=types.BotCommandScopeChat(user_id))
    except Exception as e:
        log_error(f"Failed to set user commands for {user_id}", user_id, e)


@dp.message_handler(commands=["start"])
@log_function("start_command")
async def start(message: types.Message):
    try:
        await set_user_commands(message.from_user.id)
        # Add your existing start command logic here
        await message.answer("Бот запущено! Використовуйте команди для роботи.")
    except Exception as e:
        log_error("Start command failed", message.from_user.id, e)


def filter_broadcast_users(users: list, excepted_users: set, admin_check) -> list:
    """Filter out admin and excepted users from the broadcast list."""
    return [user for user in users if getattr(user, 'telegram_id', None) and not admin_check(user.telegram_id) and str(user.telegram_id) not in excepted_users]

async def send_broadcast_message(
    users: list, message: types.Message, excepted_users: set
) -> tuple[int, int, int]:
    """Send broadcast message to users, return (success, blocked, error) counts."""
    success_count = 0
    blocked_count = 0
    error_count = 0
    for i, user in enumerate(users):
        try:
            await bot.copy_message(
                user.telegram_id,
                message.chat.id,
                message.reply_to_message.message_id,
            )
            success_count += 1
            if i > 0 and i % 30 == 0:
                await asyncio.sleep(1)
        except Exception as e:
            err_str = str(e).lower()
            if "blocked" in err_str or "forbidden" in err_str:
                blocked_count += 1
            else:
                error_count += 1
            log_error(f"Failed to send broadcast to user {getattr(user, 'telegram_id', 'unknown')}: {str(e)}")
            with open("out_blocked.txt", "a", encoding='utf-8') as f:
                print(f"User {getattr(user, 'telegram_id', 'unknown')} - {str(e)}", file=f)
    return success_count, blocked_count, error_count

def format_broadcast_result(success: int, blocked: int, error: int) -> str:
    """Format the broadcast result message."""
    return (
        f"📢 Розсилка завершена:\n"
        f"✅ Надіслано: {success}\n"
        f"❌ Заблоковано: {blocked}\n"
        f"⚠️ Помилки: {error}"
    )

@dp.message_handler(commands=["broadcast"])
@log_function("broadcast_command")
async def broadcast(message: types.Message) -> None:
    """Admin command to broadcast a message to all users except admins and excluded."""
    if not await admin_permission_check(message):
        return
    try:
        if not message.reply_to_message:
            await message.answer("❌ Відповідайте на повідомлення, яке потрібно розіслати")
            return
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        excepted_users = set(args)
        users = await UserModel.all().to_list()
        filtered_users = filter_broadcast_users(users, excepted_users, is_admin)
        log_info(f"Broadcasting message to {len(filtered_users)} users, excluding {len(excepted_users)} users")
        progress_msg = None
        if len(filtered_users) > 100:
            progress_msg = await message.answer(f"📢 Розпочинаю розсилку для {len(filtered_users)} користувачів...")
        success_count, blocked_count, error_count = await send_broadcast_message(filtered_users, message, excepted_users)
        result_text = format_broadcast_result(success_count, blocked_count, error_count)
        if progress_msg:
            await progress_msg.edit_text(result_text)
        else:
            await message.answer(result_text)
        log_info(f"Broadcast completed: {success_count} sent, {blocked_count} blocked, {error_count} errors")
    except Exception as e:
        log_error("Broadcast command failed", message.from_user.id, e)
        await message.answer("❌ Помилка при розсилці")


@dp.message_handler(commands=["get_out_txt"])
@log_function("get_out_txt_command")
async def get_out_txt(message: types.Message):
    if not await admin_permission_check(message):
        return
    try:
        with open("out.txt", "r", encoding='utf-8') as f:
            await message.answer_document(types.InputFile(f, filename="out.txt"))
    except FileNotFoundError:
        await message.answer("❌ Файл out.txt не знайдено")
    except Exception as e:
        log_error("Get out.txt command failed", message.from_user.id, e)
        await message.answer("❌ Помилка при отриманні файлу")


@dp.message_handler(commands=["stats"])
@log_function("stats_command")
async def stats(message: types.Message):
    if not await admin_permission_check(message):
        return
    try:
        # Use concurrent queries for better performance
        user_count_task = UserModel.count()
        subscription_count_task = SubscriptionModel.count()
        request_count_task = RequestLog.count()

        user_count, subscription_count, request_count = await asyncio.gather(
            user_count_task, subscription_count_task, request_count_task
        )

        # Count errors from logs if available
        error_count = 0
        try:
            from bot.core.logger import get_log_filename
            error_log = Path("logs") / get_log_filename("errors")
            if error_log.exists():
                with open(error_log, 'r', encoding='utf-8') as f:
                    error_count = sum(1 for line in f if line.strip())
        except:
            pass

        await message.answer(
            f"📊 Статистика:\n\n"
            f"👤 Користувачі: {user_count}\n"
            f"🔔 Підписки: {subscription_count}\n"
            f"📨 Запити: {request_count}\n"
            f"🚨 Помилки сьогодні: {error_count}"
        )
    except Exception as e:
        log_error("Stats command failed", message.from_user.id, e)
        await message.answer("❌ Помилка при отриманні статистики")


@dp.message_handler(commands=["stats_graph"])
@log_function("stats_graph_command")
async def stats_graph(message: types.Message):
    if not await admin_permission_check(message):
        return
    try:
        # Show progress for potentially slow operation
        progress_msg = await message.answer("📊 Генерую графік...")

        # Aggregate requests per day
        logs = await RequestLog.find_all().to_list()
        if not logs:
            await progress_msg.edit_text("❌ Немає даних для побудови графіку")
            return

        days = [log.timestamp.date() for log in logs]
        counter = Counter(days)
        days_sorted = sorted(counter.keys())
        counts = [counter[day] for day in days_sorted]

        # Create optimized plot
        plt.figure(figsize=(12, 6))
        plt.plot(days_sorted, counts, marker='o', linewidth=2, markersize=6)
        plt.title('Запити за днями', fontsize=14, fontweight='bold')
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Кількість запитів', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)

        await progress_msg.delete()
        await message.answer_photo(
            photo=types.InputFile(buf, filename="stats_graph.png"),
            caption=f"📊 Графік запитів за період\n📅 Всього днів: {len(days_sorted)}\n📨 Всього запитів: {sum(counts)}"
        )

        buf.close()
        plt.close()

    except Exception as e:
        log_error("Stats graph command failed", message.from_user.id, e)
        await message.answer("❌ Помилка при створенні графіку")


def main():
    try:
        log_info("Initializing bot")

        # Setup middlewares
        dp.middleware.setup(LoggerMiddleware())
        dp.middleware.setup(ThrottlingMiddleware())

        # Setup scheduler
        scheduler.add_job(
            scheduler_job,
            "interval",
            hours=1,
            max_instances=1  # Prevent overlapping jobs
        )
        scheduler.start()

        # Setup handlers
        handlers_setup.setup(dp)

        log_info("Starting bot polling")
        executor.start_polling(
            dp,
            loop=loop,
            skip_updates=True,
            on_startup=startup,
            on_shutdown=shutdown,
        )
    except Exception as e:
        log_error("Bot polling failed", exception=e)
        try:
            loop.run_until_complete(notify_admin(f"❗️ Bot error: {e}"))
        except:
            pass  # Don't let notification errors crash the app
        raise


if __name__ == "__main__":
    main()
