import asyncio

from aiogram import Dispatcher, types
from aiogram.dispatcher import DEFAULT_RATE_LIMIT
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import Throttled

from bot.core.logger import log_info, log_error, log_function
from bot.core.utils import get_safe_user_id


class LoggerMiddleware(BaseMiddleware):
    @log_function("setup_logger_middleware")
    async def on_process_message(self, message: types.Message, data: dict):
        """
        This handler is called when dispatcher receives a message
        """
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "No username"
            message_text = message.text or message.caption or "[Media/File]"

            # Log the message
            log_info(f"Message from @{username}: {message_text}", user_id)

            # Also keep the old file logging for backward compatibility
            with open("out.txt", "a", encoding="utf-8") as f:
                print(
                    f"\nПрийшло повідомлення від {user_id} (@{username}) з текстом: {message_text}",
                    file=f,
                )
        except Exception as e:
            log_error("Error in LoggerMiddleware", get_safe_user_id(message), e)
