# Standard library imports
from datetime import datetime

# Third party imports
from aiogram import types

# Local application imports
from bot.core.logger import log_function
from bot.core.models.user import UserModel, SubscriptionModel
from bot.core.utils import (
    admin_permission_check,
    safe_answer_message,
    safe_edit_message_markdown,
    show_typing_and_wait_message,
)
from bot.core.constants import WAIT_DATA_LOADING


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
        # Get all users
        users = await UserModel.find_all().to_list()
        
        # Get all subscriptions
        subscriptions = await SubscriptionModel.find_all().to_list()
        
        # Group subscriptions by user
        user_subscriptions = {}
        for sub in subscriptions:
            if sub.telegram_id not in user_subscriptions:
                user_subscriptions[sub.telegram_id] = []
            user_subscriptions[sub.telegram_id].append(sub.session_id)
        
        # Format message
        msg_lines = ["*📊 Список користувачів:*\n"]
        
        for user in users:
            # Get user's subscriptions
            user_subs = user_subscriptions.get(user.telegram_id, [])
            
            msg_lines.append(f"👤 *ID:* `{user.telegram_id}`")
            msg_lines.append(f"   *Сесія:* `{user.session_id}`")
            
            if user_subs:
                msg_lines.append("   *Підписки:*")
                for sub_id in user_subs:
                    msg_lines.append(f"   • `{sub_id}`")
            else:
                msg_lines.append("   *Підписки:* немає")
            msg_lines.append("")  # Empty line between users
        
        msg_lines.append(f"\n*Всього користувачів:* {len(users)}")
        msg_lines.append(f"*Всього підписок:* {len(subscriptions)}")
        
        # Send message
        await safe_edit_message_markdown(_message, "\n".join(msg_lines))
        
    except Exception as e:
        await safe_edit_message_markdown(
            _message,
            f"❌ Помилка при отриманні списку користувачів: {str(e)}"
        )