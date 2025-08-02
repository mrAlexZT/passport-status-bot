# Standard library imports
from datetime import datetime

# Third party imports
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    ADMIN_CLEANUP_START,
    ADMIN_CLEANUP_ANALYZING,
    ADMIN_CLEANUP_DELETING,
    ADMIN_CLEANUP_CONFIRM,
    ADMIN_CLEANUP_CONFIRM_BUTTON,
    ADMIN_CLEANUP_CANCEL_BUTTON,
    ADMIN_CLEANUP_CANCELLED,
    ADMIN_CLEANUP_PROCESSING,
    ADMIN_CLEANUP_CANCELLED_POPUP,
    ADMIN_CLEANUP_NO_PERMISSION,
    ADMIN_CLEANUP_EXPIRED,
    ADMIN_CLEANUP_RESULT,
    ADMIN_CLEANUP_ERROR,
    ADMIN_CLEANUP_NOTHING,
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


@log_function("analyze_db")
async def analyze_db(message: types.Message = None):
    """Analyze database for invalid records. Optionally updates progress message."""
    # Get raw collections
    users_collection: AsyncIOMotorCollection = UserModel.get_motor_collection()
    subs_collection: AsyncIOMotorCollection = SubscriptionModel.get_motor_collection()
    
    # Get all users and subscriptions
    users = await users_collection.find({}).to_list(length=None)
    subscriptions = await subs_collection.find({}).to_list(length=None)
    
    # Track statistics
    stats = {
        "users_no_id": 0,
        "users_invalid": 0,
        "subs_no_id": 0,
        "subs_no_session": 0,
        "subs_orphaned": 0
    }
    
    # Collect invalid user IDs for deletion
    users_to_delete = []
    valid_user_ids = set()
    
    for user in users:
        telegram_id = user.get('telegram_id')
        if not telegram_id:
            users_to_delete.append(user['_id'])
            stats["users_no_id"] += 1
            continue
        
        # Keep track of valid user IDs for subscription cleanup
        valid_user_ids.add(telegram_id)
        
        # Check for other required fields (add more as needed)
        if not user.get('session_id'):
            users_to_delete.append(user['_id'])
            stats["users_invalid"] += 1
            continue
    
    # Collect invalid subscriptions for deletion
    subs_to_delete = []
    
    for sub in subscriptions:
        telegram_id = sub.get('telegram_id')
        session_id = sub.get('session_id')
        
        if not telegram_id:
            subs_to_delete.append(sub['_id'])
            stats["subs_no_id"] += 1
            continue
            
        if not session_id:
            subs_to_delete.append(sub['_id'])
            stats["subs_no_session"] += 1
            continue
        
        # Check if subscription belongs to a valid user
        if telegram_id not in valid_user_ids:
            subs_to_delete.append(sub['_id'])
            stats["subs_orphaned"] += 1
            continue
    
    return users_to_delete, subs_to_delete, stats


async def perform_cleanup(users_to_delete, subs_to_delete, message: types.Message = None):
    """Actually delete the invalid records. Optionally updates progress message."""
    users_collection: AsyncIOMotorCollection = UserModel.get_motor_collection()
    subs_collection: AsyncIOMotorCollection = SubscriptionModel.get_motor_collection()
    
    # Delete invalid users
    if users_to_delete:
        result = await users_collection.delete_many({'_id': {'$in': users_to_delete}})
        total_users_deleted = result.deleted_count
    else:
        total_users_deleted = 0
    
    # Delete invalid subscriptions
    if subs_to_delete:
        result = await subs_collection.delete_many({'_id': {'$in': subs_to_delete}})
        total_subs_deleted = result.deleted_count
    else:
        total_subs_deleted = 0
    
    return total_users_deleted, total_subs_deleted


@log_function("cleanup_db")
async def cleanup_db(message: types.Message) -> None:
    """Remove invalid data from the database (admin only)."""
    # Check admin permission
    if not await admin_permission_check(message):
        return
    
    _message = await show_typing_and_wait_message(message, ADMIN_CLEANUP_START)
    if not _message:
        return
    
    try:
        # Update status and analyze database
        await _message.edit_text(ADMIN_CLEANUP_ANALYZING, parse_mode="Markdown")
        users_to_delete, subs_to_delete, stats = await analyze_db(_message)
        
        # If nothing to delete
        if not users_to_delete and not subs_to_delete:
            await safe_edit_message_markdown(_message, ADMIN_CLEANUP_NOTHING)
            return
        
        # Create inline keyboard
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(
                ADMIN_CLEANUP_CONFIRM_BUTTON,
                callback_data=f"cleanup_confirm_{len(users_to_delete)}_{len(subs_to_delete)}"
            ),
            InlineKeyboardButton(
                ADMIN_CLEANUP_CANCEL_BUTTON,
                callback_data="cleanup_cancel"
            )
        )
        
        # Show confirmation message with buttons
        await _message.edit_text(
            ADMIN_CLEANUP_CONFIRM.format(
                users=len(users_to_delete),
                subs=len(subs_to_delete),
                **stats
            ),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        log_error("cleanup_db failed", message.from_user.id, e)
        await safe_edit_message(_message, ADMIN_CLEANUP_ERROR)


@log_function("cleanup_callback")
async def cleanup_callback(callback_query: types.CallbackQuery) -> None:
    """Handle cleanup confirmation callback."""
    message = callback_query.message
    
    # Check admin permission using from_user from callback_query
    if not await admin_permission_check(callback_query):
        await callback_query.answer(ADMIN_CLEANUP_NO_PERMISSION)
        return
    
    try:
        parts = callback_query.data.split("_")
        action = parts[1]
        
        if action == "cancel":
            # Remove buttons and add cancelled note
            await message.edit_text(
                message.text + "\n\n" + ADMIN_CLEANUP_CANCELLED,
                parse_mode="Markdown"
            )
            await callback_query.answer(ADMIN_CLEANUP_CANCELLED_POPUP)
            return
        
        # Extract expected counts from callback data
        expected_users = int(parts[2])
        expected_subs = int(parts[3])
        
        # Show analyzing message
        await callback_query.answer(ADMIN_CLEANUP_PROCESSING)
        await message.edit_text(ADMIN_CLEANUP_ANALYZING, parse_mode="Markdown")
        
        # Re-analyze database
        users_to_delete, subs_to_delete, stats = await analyze_db(message)
        
        # Check if data has changed
        if len(users_to_delete) != expected_users or len(subs_to_delete) != expected_subs:
            await message.edit_text(ADMIN_CLEANUP_EXPIRED, parse_mode="Markdown")
            return
        
        # Show deleting message
        await message.edit_text(ADMIN_CLEANUP_DELETING, parse_mode="Markdown")
        
        # Perform the cleanup
        total_users_deleted, total_subs_deleted = await perform_cleanup(
            users_to_delete, subs_to_delete, message
        )
        
        # Show results
        await message.edit_text(
            ADMIN_CLEANUP_RESULT.format(
                users=total_users_deleted,
                subs=total_subs_deleted,
                **stats
            ),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        log_error("cleanup_callback failed", callback_query.from_user.id, e)
        await message.edit_text(ADMIN_CLEANUP_ERROR, parse_mode="Markdown")