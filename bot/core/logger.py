# Standard library imports
import logging
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Optional

# Local application imports
from bot.core.config import settings

# Try to import CancelHandler for proper exception handling
try:
    from aiogram.dispatcher.handler import CancelHandler
except ImportError:
    CancelHandler = None


def get_log_filename(log_type: str = "bot") -> str:
    """Generate log filename with current date - eliminates duplication."""
    date_str = datetime.now().strftime('%Y%m%d')
    return f"{log_type}_{date_str}.log"


class GlobalLogger:
    _instance: Optional["GlobalLogger"] = None
    _initialized: bool = False

    def __new__(cls) -> "GlobalLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self.enabled: bool = True  # Default enabled, can be controlled by admin
            self.logger: logging.Logger = logging.getLogger("passport_bot")
            self.setup_logger()
            self._initialized = True

    def setup_logger(self) -> None:
        """Setup the logger with file and console handlers."""
        self.logger.setLevel(logging.INFO)
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            logs_dir / get_log_filename("bot"),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        error_handler = logging.FileHandler(
            logs_dir / get_log_filename("errors"),
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin - delegates to main is_admin function."""
        from bot.__main__ import is_admin
        return is_admin(user_id)

    def toggle_logging(self, user_id: int) -> str:
        """Toggle logging on/off (admin only)."""
        if not self.is_admin(user_id):
            return "❌ Тільки адміністратор може керувати логуванням"
        self.enabled = not self.enabled
        status = "увімкнено" if self.enabled else "вимкнено"
        self.info(f"Logging toggled by admin {user_id}: {self.enabled}")
        return f"📊 Логування {status}"

    def info(self, message: str, user_id: Optional[int] = None) -> None:
        """Log info message."""
        if not self.enabled:
            return
        log_msg = f"[User: {user_id}] {message}" if user_id else message
        self.logger.info(log_msg)

    def error(self, message: str, user_id: Optional[int] = None, exception: Optional[Exception] = None) -> None:
        """Log error message."""
        if not self.enabled:
            return
        log_msg = f"[User: {user_id}] {message}" if user_id else message
        if exception:
            log_msg += f" | Exception: {str(exception)}"
        self.logger.error(log_msg, exc_info=exception is not None)

    def warning(self, message: str, user_id: Optional[int] = None):
        """Log warning message"""
        if not self.enabled:
            return

        log_msg = f"[User: {user_id}] {message}" if user_id else message
        self.logger.warning(log_msg)

    def debug(self, message: str, user_id: Optional[int] = None):
        """Log debug message"""
        if not self.enabled:
            return

        log_msg = f"[User: {user_id}] {message}" if user_id else message
        self.logger.debug(log_msg)


# Global logger instance
global_logger = GlobalLogger()


def log_function(func_name: str = None):
    """Decorator to log function calls"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = func_name or func.__name__
            user_id = None

            # Try to extract user_id from arguments
            for arg in args:
                if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                    user_id = arg.from_user.id
                    break
                elif hasattr(arg, 'id'):
                    user_id = getattr(arg, 'id', None)
                    break

            global_logger.info(f"Function '{name}' called", user_id)

            try:
                result = await func(*args, **kwargs)
                global_logger.info(f"Function '{name}' completed successfully", user_id)
                return result
            except Exception as e:
                # Don't log aiogram's CancelHandler as it's used for flow control
                if CancelHandler and isinstance(e, CancelHandler):
                    raise
                global_logger.error(f"Function '{name}' failed", user_id, e)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = func_name or func.__name__
            user_id = None

            # Try to extract user_id from arguments
            for arg in args:
                if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                    user_id = arg.from_user.id
                    break
                elif hasattr(arg, 'id'):
                    user_id = getattr(arg, 'id', None)
                    break

            global_logger.info(f"Function '{name}' called", user_id)

            try:
                result = func(*args, **kwargs)
                global_logger.info(f"Function '{name}' completed successfully", user_id)
                return result
            except Exception as e:
                # Don't log aiogram's CancelHandler as it's used for flow control
                if CancelHandler and isinstance(e, CancelHandler):
                    raise
                global_logger.error(f"Function '{name}' failed", user_id, e)
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_error(message: str, user_id: Optional[int] = None, exception: Optional[Exception] = None):
    """Convenience function to log errors"""
    global_logger.error(message, user_id, exception)


def log_info(message: str, user_id: Optional[int] = None):
    """Convenience function to log info"""
    global_logger.info(message, user_id)


def log_warning(message: str, user_id: Optional[int] = None):
    """Convenience function to log warnings"""
    global_logger.warning(message, user_id)
