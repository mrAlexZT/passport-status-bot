# -*- coding: utf-8 -*-
"""
Utility functions for common patterns and operations.
"""
from datetime import datetime
from typing import Optional, List, Tuple
from aiogram import types
from textwrap import dedent

from bot.core.constants import *
from bot.core.logger import log_error
from bot.core.models.user import UserModel
from bot.core.models.application import ApplicationModel, StatusModel


async def get_user_by_telegram_id(telegram_id: int) -> Optional[UserModel]:
    """Helper to get a user by Telegram ID as string."""
    return await UserModel.find_one({"telegram_id": str(telegram_id)})


async def safe_edit_message(message: types.Message, text: str, parse_mode: str = None) -> None:
    """Safely edit a message with error handling."""
    try:
        await message.edit_text(text, parse_mode=parse_mode)
    except Exception as e:
        log_error("Failed to edit message", getattr(message, 'from_user', {}).get('id'), e)
        # Fallback: try to send a new message if editing fails
        try:
            await message.answer(text, parse_mode=parse_mode)
        except Exception as fallback_error:
            log_error("Failed to send fallback message", getattr(message, 'from_user', {}).get('id'), fallback_error)


async def safe_answer_message(message: types.Message, text: str, parse_mode: str = None) -> Optional[types.Message]:
    """Safely answer a message with error handling."""
    try:
        return await message.answer(text, parse_mode=parse_mode)
    except Exception as e:
        log_error("Failed to answer message", getattr(message, 'from_user', {}).get('id'), e)
        return None


def format_status_list(statuses: List[StatusModel], session_id: str = None) -> str:
    """Format a list of statuses into a readable text."""
    if not statuses:
        return "Немає статусів для відображення."
    
    header = STATUS_APPLICATION_HEADER.format(session_id=session_id) if session_id else STATUS_GENERAL_HEADER
    msg_text = header
    
    for i, status in enumerate(statuses, start=1):
        date = datetime.fromtimestamp(int(status.date) / 1000).strftime("%Y-%m-%d %H:%M")
        msg_text += f"{i}. *{status.status}* \n_{date}_\n\n"
    
    return msg_text


def format_application_statuses_section(statuses: List[StatusModel]) -> str:
    """Format application statuses section for cabinet display."""
    if not statuses:
        return ""
    
    msg_text = HEADER_APPLICATION_STATUSES
    for i, status in enumerate(statuses, start=1):
        date = datetime.fromtimestamp(int(status.date) / 1000).strftime("%Y-%m-%d %H:%M")
        msg_text += f"{i}. *{status.status}* _{date}_\n\n"
    
    return msg_text


def create_status_models_from_api_response(status_data: List[dict]) -> List[StatusModel]:
    """Convert API response status data to StatusModel objects."""
    return [
        StatusModel(status=s.get("status"), date=s.get("date"))
        for s in status_data
    ]


def get_new_statuses(current_statuses: List[StatusModel], previous_statuses: List[StatusModel]) -> List[StatusModel]:
    """Extract new statuses by comparing current with previous."""
    if len(current_statuses) > len(previous_statuses):
        return current_statuses[len(previous_statuses):]
    return []


async def handle_user_not_found(message: types.Message) -> None:
    """Handle case when user is not found in database."""
    await safe_edit_message(message, NOT_FOUND_IDENTIFIER)


async def handle_invalid_session_id(message: types.Message, command: str) -> None:
    """Handle case when session ID format is invalid."""
    await safe_edit_message(message, INSTRUCTION_INVALID_SESSION_ID.format(command=command))


async def handle_scraper_error(message: types.Message) -> None:
    """Handle case when scraper fails to get data."""
    await safe_edit_message(message, ERROR_IDENTIFIER_VALIDATION)


async def handle_generic_error(message: types.Message, operation: str) -> None:
    """Handle generic errors with consistent messaging."""
    await safe_edit_message(message, ERROR_GENERIC_DETAILED.format(operation=operation))


def format_subscription_list(subscriptions: List, include_count: bool = True) -> str:
    """Format subscription list into readable text."""
    if not subscriptions:
        return NOT_SUBSCRIBED
    
    msg_text = HEADER_YOUR_SUBSCRIPTIONS
    
    for i, subscription in enumerate(subscriptions, start=1):
        msg_text += f"{i}. *{subscription.session_id}* \n"
    
    if include_count:
        msg_text += f"\n{SUBSCRIPTION_COUNT_FORMAT.format(count=len(subscriptions))}"
    
    return msg_text


async def show_typing_and_wait_message(message: types.Message, wait_text: str = None) -> Optional[types.Message]:
    """Show typing indicator and send a wait message."""
    if wait_text is None:
        wait_text = WAIT_CHECKING
    await message.answer_chat_action("typing")
    return await safe_answer_message(message, wait_text)


async def process_status_update(application: ApplicationModel, scraper, notify_callback=None) -> Tuple[bool, List[StatusModel]]:
    """
    Process status update for an application.
    
    Returns:
        Tuple of (has_new_statuses, new_statuses)
    """
    from datetime import datetime
    
    status_data = scraper.check(application.session_id, retrive_all=True)
    if not status_data:
        return False, []
    
    new_statuses_list = create_status_models_from_api_response(status_data)
    new_statuses = get_new_statuses(new_statuses_list, application.statuses)
    
    if new_statuses and notify_callback:
        await notify_callback(target_application=application, new_statuses=new_statuses)
    
    # Update application
    application.statuses = new_statuses_list
    application.last_update = datetime.now()
    await application.save()
    
    return bool(new_statuses), new_statuses


def format_new_status_message(session_id: str, new_statuses: List[StatusModel]) -> str:
    """Format new status update message."""
    msg_text = STATUS_CHANGE_DETECTED.format(session_id=session_id)
    
    for i, status in enumerate(new_statuses, start=1):
        date = datetime.fromtimestamp(int(status.date) / 1000).strftime("%Y-%m-%d %H:%M")
        msg_text += f"{i}. *{status.status}* \n_{date}_\n\n"
    
    return msg_text


async def check_subscription_limit(user_id: int, max_subscriptions: int = 7) -> bool:
    """Check if user has reached subscription limit."""
    from bot.core.models.user import SubscriptionModel
    
    count = await SubscriptionModel.find({"telegram_id": str(user_id)}).count()
    return count >= max_subscriptions