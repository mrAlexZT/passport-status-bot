import asyncio

from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

from bot.core.logger import log_info, log_error, log_function
from bot.core.utils import get_safe_user_id


class LoggerMiddleware(BaseMiddleware):
    @log_function("setup_logger_middleware")
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any]
    ) -> Any:
        """
        This handler is called when dispatcher receives a message
        """
        try:
            user_id = event.from_user.id
            username = event.from_user.username or "No username"
            message_text = event.text or event.caption or "[Media/File]"

            # Log the message
            log_info(f"Message from @{username}: {message_text}", user_id)

            # Also keep the old file logging for backward compatibility
            with open("out.txt", "a", encoding="utf-8") as f:
                print(
                    f"\nПрийшло повідомлення від {user_id} (@{username}) з текстом: {message_text}",
                    file=f,
                )
        except Exception as e:
            log_error("Error in LoggerMiddleware", get_safe_user_id(event), e)
        
        # Call the next handler in the chain
        return await handler(event, data)
