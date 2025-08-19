"""
Main bot application with clean architecture.
All commands are organized in this single module to eliminate redundancy.
"""

import asyncio

from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.bot_instance import bot
from bot.commands.admin import AdminCommands
from bot.commands.subscription import SubscriptionCommands
from bot.commands.system import SystemCommands
from bot.commands.user import UserCommands
from bot.core.config import settings
from bot.core.constants import BOT_STOPPED_MANUALLY
from bot.core.logger import log_error, log_function, log_info
from bot.core.scheduler import JOB_ID, scheduler_job, set_scheduler
from bot.middlewares.antiflood import ThrottlingMiddleware
from bot.middlewares.debug import LoggerMiddleware
from bot.services import StartupService


class BotApplication:
    """Main bot application class with integrated command handling."""

    @log_function("__init__")
    def __init__(self) -> None:
        self.dp = Dispatcher(storage=MemoryStorage())
        self.scheduler = AsyncIOScheduler()
        self._setup_middleware()
        self._setup_handlers()
        self._setup_scheduler()

    @log_function("_setup_middleware")
    def _setup_middleware(self) -> None:
        """Setup middleware for the dispatcher."""
        self.dp.message.middleware(ThrottlingMiddleware())
        self.dp.callback_query.middleware(ThrottlingMiddleware())
        self.dp.message.middleware(LoggerMiddleware())

    @log_function("_setup_handlers")
    def _setup_handlers(self) -> None:
        """Setup all command and message handlers."""
        # System commands (available to all users)
        self.dp.message.register(SystemCommands.ping, Command("ping"))
        self.dp.message.register(SystemCommands.time, Command("time"))
        self.dp.message.register(SystemCommands.start, Command("start"))
        self.dp.message.register(SystemCommands.help, Command("help"))
        self.dp.message.register(SystemCommands.policy, Command("policy"))
        self.dp.message.register(SystemCommands.authors, Command("authors"))
        self.dp.message.register(SystemCommands.version, Command("version"))

        # User management commands
        self.dp.message.register(UserCommands.cabinet, Command("cabinet"))
        self.dp.message.register(UserCommands.link, Command("link"))
        self.dp.message.register(UserCommands.unlink, Command("unlink"))

        # Subscription commands
        self.dp.message.register(SubscriptionCommands.subscribe, Command("subscribe"))
        self.dp.message.register(
            SubscriptionCommands.unsubscribe, Command("unsubscribe")
        )
        self.dp.message.register(
            SubscriptionCommands.subscriptions_list, Command("subscriptions")
        )
        self.dp.message.register(SubscriptionCommands.update_status, Command("update"))
        self.dp.message.register(
            SubscriptionCommands.push_notifications, Command("push")
        )
        self.dp.message.register(
            SubscriptionCommands.dump_subscriptions, Command("dump")
        )

        # Admin commands
        self.dp.message.register(
            AdminCommands.toggle_logging, Command("toggle_logging")
        )
        self.dp.message.register(AdminCommands.get_logs, Command("logs"))
        self.dp.message.register(AdminCommands.broadcast, Command("broadcast"))
        self.dp.message.register(AdminCommands.get_out_txt, Command("get_out_txt"))
        self.dp.message.register(AdminCommands.stats, Command("stats"))
        self.dp.message.register(AdminCommands.stats_graph, Command("stats_graph"))
        self.dp.message.register(AdminCommands.users_list, Command("users"))
        self.dp.message.register(AdminCommands.cleanup_db, Command("cleanup"))
        self.dp.message.register(AdminCommands.set_interval, Command("set_interval"))
        self.dp.message.register(AdminCommands.get_interval, Command("get_interval"))

        # Callback handlers
        self.dp.callback_query.register(
            AdminCommands.cleanup_callback, lambda c: c.data.startswith("cleanup_")
        )

        # Message handlers
        self.dp.message.register(
            UserCommands.custom_check, lambda msg: msg.text and msg.text.isdigit()
        )
        self.dp.message.register(
            UserCommands.image_qr_recognition, lambda msg: msg.photo
        )

        # Command not found handler
        self.dp.message.register(
            SystemCommands.command_not_found, self._is_unknown_command
        )

    @log_function("_is_unknown_command")
    def _is_unknown_command(self, message: types.Message) -> bool:
        """Check if message is an unknown command."""
        if not message.text or not message.text.startswith("/"):
            return False

        from bot.core.command_registry import CommandRegistry

        command = message.text.split()[0].split("@")[0]
        return not CommandRegistry.is_valid_command(command)

    @log_function("_setup_scheduler")
    def _setup_scheduler(self) -> None:
        """Setup periodic tasks scheduler."""

        @log_function("async_scheduler_wrapper")
        async def async_scheduler_wrapper(
            max_retries: int = settings.SCHEDULER_MAX_RETRIES,
        ) -> None:
            """Wrapper to run scheduler_job with retries and timeout."""

            @log_function("log_retry")
            def log_retry(retry: int, error_type: str) -> None:
                log_error(
                    f"Scheduler job failed due to {error_type} on retry {retry}/{max_retries}"
                )

            for retry in range(1, max_retries + 1):
                try:
                    await asyncio.wait_for(
                        scheduler_job(), timeout=settings.SCHEDULER_TIMEOUT
                    )
                    log_info("Scheduler job completed successfully")
                    return
                except TimeoutError:
                    log_retry(retry, "timeout")
                except ConnectionError:
                    log_retry(retry, "connection error")
                except Exception as e:
                    log_error("Scheduler job failed with unexpected error", exception=e)
                    return

                # Sleep only once between retries
                if retry < max_retries:
                    await asyncio.sleep(settings.SCHEDULER_WAIT_SECONDS)

            log_error("Scheduler job failed after max retries")

        self.scheduler.add_job(
            async_scheduler_wrapper,
            "interval",
            id=JOB_ID,
            minutes=settings.SCHEDULER_INTERVAL_MINUTES,
            max_instances=settings.SCHEDULER_MAX_INSTANCES,
            coalesce=True,
            kwargs={"max_retries": settings.SCHEDULER_MAX_RETRIES},
        )
        set_scheduler(self.scheduler)

    @log_function("start")
    async def start(self) -> None:
        """Start the bot application."""
        try:
            await StartupService.startup()
            self.scheduler.start()

            await self.dp.start_polling(
                bot,
                on_shutdown=StartupService.shutdown,
                polling_timeout=10,
                drop_pending_updates=True,
            )

        except (KeyboardInterrupt, SystemExit):
            log_info(BOT_STOPPED_MANUALLY)
        except Exception as e:
            log_error("Bot crashed", None, e)
            raise
        finally:
            if self.scheduler.running:
                self.scheduler.shutdown()


@log_function("main")
def main() -> None:
    """Main entry point."""
    app = BotApplication()
    asyncio.run(app.start())


if __name__ == "__main__":
    main()
