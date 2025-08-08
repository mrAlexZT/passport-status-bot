# Standard library imports
import asyncio
from datetime import datetime

# Third party imports
from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

# Default rate limit (since DEFAULT_RATE_LIMIT was removed in aiogram v3)
DEFAULT_RATE_LIMIT = 3

# Local application imports
from bot.core.logger import log_function
from bot.core.models.request_log import RequestLog
from bot.core.utils import get_user_id_str


@log_function("rate_limit")
def rate_limit(limit: int, key=None):
    """

    Decorator for configuring rate limit and key in different functions.


    :param limit:

    :param key:

    :return:

    """

    @log_function("rate_limit_decorator")
    def decorator(func):
        setattr(func, "throttling_rate_limit", limit)

        if key:
            setattr(func, "throttling_key", key)

        return func

    return decorator


class ThrottlingMiddleware(BaseMiddleware):
    """
    Simple middleware for rate limiting
    """

    def __init__(self, limit=3, key_prefix="antiflood_"):
        self.rate_limit = limit
        self.prefix = key_prefix
        self.storage = {}  # Simple in-memory storage for demo
        super().__init__()

    @log_function("on_process_message")
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any]
    ) -> Any:
        # Log every incoming message
        try:
            await RequestLog(telegram_id=get_user_id_str(event), timestamp=datetime.utcnow()).insert()
        except Exception:
            pass

        # Simple rate limiting implementation
        user_id = event.from_user.id
        current_time = datetime.utcnow()
        
        # For demo purposes, we'll implement a simple rate limiter
        # In production, you might want to use Redis or another storage
        if user_id in self.storage:
            last_request_time = self.storage[user_id]
            time_diff = (current_time - last_request_time).total_seconds()
            
            if time_diff < self.rate_limit:
                # Rate limit exceeded, ignore the message
                await asyncio.sleep(self.rate_limit - time_diff)
        
        self.storage[user_id] = current_time
        
        # Call the next handler in the chain
        return await handler(event, data)

    @log_function("message_throttled")  
    async def message_throttled(self, message: types.Message, throttled_time: float):
        """
        Handle throttled messages - simplified for aiogram v3
        """
        # Simple implementation - just sleep
        await asyncio.sleep(throttled_time)
