# Standard library imports
from datetime import datetime

# Third party imports
from aiogram import types
from motor.motor_asyncio import AsyncIOMotorCollection

# Local application imports
from bot.core.logger import log_function, log_error
from bot.core.models.user import UserModel, SubscriptionModel
from bot.core.utils import (
    admin_permission_check,
    safe_answer_message,
    safe_edit_message,
    show_typing_and_wait_message,
)
from bot.core.constants import WAIT_DATA_LOADING, ERROR_GENERIC


@log_function("users_list")
async def users_list(message: types.Message) -> None:
    """Show list of all users and their subscriptions (admin only)."""
    # Check admin permission
    if not await admin_permission_check(message):
        return
    
    _message = await show_typing_and_wait_message(message, WAIT_DATA_LOADING)
    if not _message:
        return
    
    try:
        # Get raw data from collections to avoid Pydantic validation issues
        users_collection: AsyncIOMotorCollection = UserModel.get_motor_collection()
        subs_collection: AsyncIOMotorCollection = SubscriptionModel.get_motor_collection()
        
        users_cursor = users_collection.find({})
        subs_cursor = subs_collection.find({})
        
        users = await users_cursor.to_list(length=None)
        subscriptions = await subs_cursor.to_list(length=None)
        
        # Group subscriptions by user
        user_subscriptions = {}
        for sub in subscriptions:
            telegram_id = sub.get('telegram_id')
            if not telegram_id:
                continue
            if telegram_id not in user_subscriptions:
                user_subscriptions[telegram_id] = []
            user_subscriptions[telegram_id].append(sub.get('session_id', 'Unknown'))
        
        # Format message
        msg_lines = ["📊 Список користувачів:\\n"]
        
        for user in users:
            telegram_id = user.get('telegram_id')
            if not telegram_id:
                continue
                
            # Get user's subscriptions
            user_subs = user_subscriptions.get(telegram_id, [])
            
            msg_lines.append(f"👤 ID: {telegram_id}")
            msg_lines.append(f"   Сесія: {user.get('session_id', 'Не встановлено')}")
            
            if user_subs:
                msg_lines.append("   Підписки:")
                for sub_id in user_subs:
                    msg_lines.append(f"   • {sub_id}")
            else:
                msg_lines.append("   Підписки: немає")
            msg_lines.append("")  # Empty line between users
        
        msg_lines.append(f"\\nВсього користувачів: {len(users)}")
        msg_lines.append(f"Всього підписок: {len(subscriptions)}")
        
        # Send message
        await safe_edit_message(_message, "\\n".join(msg_lines))
        
    except Exception as e:
        log_error("users_list failed", message.from_user.id, e)
        await safe_edit_message(_message, ERROR_GENERIC)