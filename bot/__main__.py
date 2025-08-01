import datetime
import matplotlib.pyplot as plt
import io
import asyncio
from collections import Counter
from pathlib import Path

from beanie import init_beanie
from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
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
from bot.core.logger import global_logger, log_function, log_error, log_info

scheduler = AsyncIOScheduler()

dp = Dispatcher(
    bot,
    loop=loop,
    storage=MemoryStorage(),
)


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return str(user_id) == str(settings.ADMIN_ID)


@log_function("startup")
async def startup(dp: Dispatcher):
    try:
        log_info("Bot startup initiated")
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


async def set_user_commands(user_id):
    """Optimize: cache admin status and set commands efficiently"""
    try:
        is_user_admin = is_admin(user_id)

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
            types.BotCommand(command="/toggle_logging", description="Увімкнути/вимкнути логування"),
            types.BotCommand(command="/logs", description="Переглянути логи"),
        ]

        if is_user_admin:
            await bot.set_my_commands(admin_commands, scope=types.BotCommandScopeChat(user_id))
        else:
            # Filter out admin-only commands for regular users
            admin_only_commands = {"/broadcast", "/get_out_txt", "/stats", "/stats_graph", "/toggle_logging", "/logs"}
            user_commands = [cmd for cmd in admin_commands if cmd.command not in admin_only_commands]
            await bot.set_my_commands(user_commands, scope=types.BotCommandScopeChat(user_id))
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


@dp.message_handler(commands=["broadcast"])
@log_function("broadcast_command")
async def broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Тільки адміністратор може користуватися цією командою!")
        return

    try:
        if not message.reply_to_message:
            await message.answer("❌ Відповідайте на повідомлення, яке потрібно розіслати")
            return

        # Parse excluded users from command
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        excepted_users = set(args)  # Use set for O(1) lookup
        users = await UserModel.all().to_list()
        log_info(f"Broadcasting message to {len(users)} users, excluding {len(excepted_users)} users")
        success_count = 0
        blocked_count = 0
        error_count = 0
        progress_msg = None
        if len(users) > 100:
            progress_msg = await message.answer(f"📢 Розпочинаю розсилку для {len(users)} користувачів...")
        for i, user in enumerate(users):
            try:
                user_id_str = str(getattr(user, 'telgram_id', None))
                if not user_id_str or is_admin(user.telgram_id) or user_id_str in excepted_users:
                    continue
                await bot.copy_message(
                    user.telgram_id,
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
                log_error(f"Failed to send broadcast to user {getattr(user, 'telgram_id', 'unknown')}: {str(e)}")
                with open("out_blocked.txt", "a", encoding='utf-8') as f:
                    print(f"User {getattr(user, 'telgram_id', 'unknown')} - {str(e)}", file=f)
        result_text = (
            f"📢 Розсилка завершена:\n"
            f"✅ Надіслано: {success_count}\n"
            f"❌ Заблоковано: {blocked_count}\n"
            f"⚠️ Помилки: {error_count}"
        )
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
    if not is_admin(message.from_user.id):
        await message.answer("❌ Тільки адміністратор може користуватися цією командою!")
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
    if not is_admin(message.from_user.id):
        await message.answer("❌ Тільки адміністратор може користуватися цією командою!")
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
            error_log = Path("logs") / f"errors_{datetime.datetime.now().strftime('%Y%m%d')}.log"
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
    if not is_admin(message.from_user.id):
        await message.answer("❌ Тільки адміністратор може користуватися цією командою!")
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
