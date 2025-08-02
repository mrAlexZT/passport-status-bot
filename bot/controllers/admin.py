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
    safe_edit_message_markdown,
    show_typing_and_wait_message,
)
from bot.core.constants import (
    WAIT_DATA_LOADING,
    ERROR_GENERIC,
    ADMIN_USERS_LIST_HEADER,
    ADMIN_USER_ENTRY,
    ADMIN_USER_SESSION,
    ADMIN_USER_SUBSCRIPTIONS_HEADER,
    ADMIN_USER_NO_SUBSCRIPTIONS,
    ADMIN_USER_SUBSCRIPTION_ENTRY,
    ADMIN_TOTAL_STATS,
    ADMIN_INVALID_DATA_WARNING,
)


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
        
        # Group subscriptions by user and validate data
        user_subscriptions = {}
        invalid_subs = []
        for sub in subscriptions:
            telegram_id = sub.get('telegram_id')
            session_id = sub.get('session_id')
            if not telegram_id or not session_id:
                invalid_subs.append(sub)
                continue
            if telegram_id not in user_subscriptions:
                user_subscriptions[telegram_id] = []
            user_subscriptions[telegram_id].append(session_id)
        
        if invalid_subs:
            log_error("Found invalid subscriptions", message.from_user.id, {"invalid_subs": invalid_subs})
        
        # Format message
        msg_lines = [ADMIN_USERS_LIST_HEADER]
        
        invalid_users = []
        for user in users:
            telegram_id = user.get('telegram_id')
            session_id = user.get('session_id', 'Не встановлено')
            if not telegram_id:
                invalid_users.append(user)
                continue
                
            # Get user's subscriptions
            user_subs = user_subscriptions.get(telegram_id, [])
            
            msg_lines.append(ADMIN_USER_ENTRY.format(telegram_id=telegram_id))
            msg_lines.append(ADMIN_USER_SESSION.format(session_id=session_id))
            
            if user_subs:
                msg_lines.append(ADMIN_USER_SUBSCRIPTIONS_HEADER)
                for sub_id in user_subs:
                    msg_lines.append(ADMIN_USER_SUBSCRIPTION_ENTRY.format(sub_id=sub_id))
            else:
                msg_lines.append(ADMIN_USER_NO_SUBSCRIPTIONS)
            msg_lines.append("")  # Empty line between users
        
        if invalid_users:
            log_error("Found invalid users", message.from_user.id, {"invalid_users": invalid_users})

        valid_users = len(users) - len(invalid_users)
        valid_subs = len(subscriptions) - len(invalid_subs)
        
        msg_lines.append(ADMIN_TOTAL_STATS.format(users=valid_users, subs=valid_subs))
        if invalid_users or invalid_subs:
            msg_lines.append(ADMIN_INVALID_DATA_WARNING.format(
                invalid_users=len(invalid_users),
                invalid_subs=len(invalid_subs)
            ))
        
        # Send message with Markdown formatting
        await safe_edit_message_markdown(_message, "\n".join(msg_lines))
        
    except Exception as e:
        log_error("users_list failed", message.from_user.id, e)
        await safe_edit_message(_message, ERROR_GENERIC)