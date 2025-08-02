# Standard library imports
import secrets
from datetime import datetime, timedelta
from textwrap import dedent
from typing import Optional

# Third party imports
from aiogram import types

# Local application imports
from bot.__main__ import is_admin
from bot.core.api import Scraper
from bot.core.constants import *
from bot.core.logger import log_function, log_error
from bot.core.models.application import ApplicationModel, StatusModel
from bot.core.models.push import PushModel
from bot.core.models.user import SubscriptionModel, UserModel
from bot.core.notificator import notify_subscribers
from bot.core.utils import (
    get_application_by_session_id,
    _format_status_with_custom_template,
    check_subscription_limit,
    create_status_models_from_api_response,
    format_new_status_message,
    format_subscription_list,
    get_push_by_message,
    get_user_by_message,
    get_user_id_str,
    handle_generic_error,
    handle_invalid_session_id,
    handle_scraper_error,
    log_handler_error,
    process_status_update,
    safe_edit_message,
    safe_edit_message_markdown,
    show_typing_and_wait_message,
)


async def _create_subscription_for_session(user_id: int, session_id: str) -> bool:
    """Create a subscription for a specific session ID. Returns True if successful."""
    # Check if subscription already exists
    existing_subscription = await SubscriptionModel.find_one(
        {"telegram_id": str(user_id), "session_id": session_id}
    )
    if existing_subscription:
        return False  # Already subscribed
    
    # Create application record if it doesn't exist
    application = await get_application_by_session_id(session_id)
    if not application:
        scraper = Scraper()
        status_data = scraper.check(session_id, retrive_all=True)
        if not status_data:
            return False  # Invalid session ID
        
        application = ApplicationModel(
            session_id=session_id,
            statuses=create_status_models_from_api_response(status_data),
            last_update=datetime.now(),
        )
        await application.insert()
    
    # Create subscription
    subscription = SubscriptionModel(
        telegram_id=str(user_id),
        session_id=session_id,
    )
    await subscription.insert()
    return True


@log_function("subscribe")
async def subscribe(message: types.Message) -> None:
    """Subscribe the user to notifications for one or more session IDs."""
    _message = await show_typing_and_wait_message(message, WAIT_CHECKING)
    if not _message:
        return
    
    try:
        parts = message.text.split(" ")
        if len(parts) <= 1:
            await handle_invalid_session_id(_message, "/subscribe")
            return
        
        # Check subscription limit first
        if await check_subscription_limit(message.from_user.id):
            await safe_edit_message(_message, SUBSCRIPTION_LIMIT_REACHED)
            return
        
        session_ids = parts[1:]
        successful_subscriptions = 0
        
        for session_id in session_ids:
            await safe_edit_message(
                _message,
                WAIT_SUBSCRIPTION_PROCESSING.format(session_id=session_id)
            )
            
            if await _create_subscription_for_session(message.from_user.id, session_id):
                successful_subscriptions += 1
        
        if successful_subscriptions > 0:
            await safe_edit_message(_message, SUCCESS_SUBSCRIPTION_CREATED)
        else:
            await safe_edit_message(_message, SUBSCRIPTION_CREATE_FAILED)
    
    except Exception as e:
        log_handler_error("subscribe", message, e)
        await handle_generic_error(_message, "підписці")


@log_function("unsubscribe")
async def unsubscribe(message: types.Message) -> None:
    """Unsubscribe the user from notifications for a session ID."""
    _message = await show_typing_and_wait_message(message, WAIT_CHECKING)
    if not _message:
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await handle_invalid_session_id(_message, "/unsubscribe")
            return
        
        session_id = parts[1]
        subscription = await SubscriptionModel.find_one(
            {"telegram_id": get_user_id_str(message), "session_id": session_id}
        )
        
        if not subscription:
            await safe_edit_message(_message, NOT_SUBSCRIBED)
            return
        
        await subscription.delete()
        await safe_edit_message(_message, SUCCESS_UNSUBSCRIPTION)
    except Exception as e:
        log_handler_error("unsubscribe", message, e)
        await handle_generic_error(_message, "відписці")


@log_function("subscriptions")
async def subscriptions(message: types.Message) -> None:
    """Show the user's current subscriptions."""
    _message = await show_typing_and_wait_message(message, WAIT_DATA_LOADING)
    if not _message:
        return
    
    try:
        user_subscriptions = await SubscriptionModel.find(
            {"telegram_id": get_user_id_str(message)}
        ).to_list()
        
        msg_text = format_subscription_list(user_subscriptions, include_count=True)
        await safe_edit_message_markdown(_message, msg_text)
    except Exception as e:
        log_handler_error("subscriptions", message, e)
        await handle_generic_error(_message, "отриманні підписок")


@log_function("manual_application_update")
async def manual_application_update(message: types.Message) -> None:
    """Manually update the user's application status."""
    _message = await show_typing_and_wait_message(message, WAIT_DATA_LOADING)
    if not _message:
        return
    
    try:
        _user = await get_user_by_message(message)
        _application = await get_application_by_session_id(_user.session_id) if _user else None
        if not _user or not _application:
            await safe_edit_message(_message, NOT_FOUND_IDENTIFIER_OR_APPLICATION)
            return

        # Set wait time based on admin status
        _wait_time_minutes = 2 if is_admin(_user.telegram_id) else 60

        if _application.last_update > datetime.now() - timedelta(minutes=_wait_time_minutes):
            await safe_edit_message(
                _message,
                RATE_LIMIT_WAIT_MESSAGE.format(minutes=_wait_time_minutes),
                parse_mode="Markdown",
            )
            return

        # Use the centralized status processing function
        has_new_statuses, new_statuses = await process_status_update(
            _application, Scraper(), notify_subscribers
        )

        if not has_new_statuses:
            await safe_edit_message(_message, STATUS_NOT_CHANGED, parse_mode="Markdown")
        else:
            # Format the new status message
            msg_text = format_new_status_message(_user.session_id, new_statuses)
            await safe_edit_message_markdown(_message, msg_text)

    except Exception as e:
        log_handler_error("manual_application_update", message, e)
        await safe_edit_message(_message, ERROR_APPLICATION_UPDATE)


@log_function("enable_push")
async def enable_push(message: types.Message):
    _push = await get_push_by_message(message)
    if _push:
        await message.answer(
            SUBSCRIPTION_ALREADY_EXISTS.format(
                user_id=message.from_id,
                secret_id=_push.secret_id
            ),
            parse_mode="Markdown",
        )
        return

    # Generate random secret id for push - length 32
    _secret_id = secrets.token_hex(16)

    _push = PushModel(
        telegram_id=get_user_id_str(message),
        secret_id=_secret_id,
    )
    await _push.insert()

    await message.answer(
        PUSH_SUCCESS_MESSAGE.format(
            secret_id=_secret_id,
            user_id=message.from_id
        ),
        parse_mode="Markdown",
    )


@log_function("dump_subscriptions")
async def dump_subscriptions(message: types.Message):
    _subscriptions = await SubscriptionModel.find(
        {"telegram_id": get_user_id_str(message)}
    ).to_list()

    if not _subscriptions:
        await message.answer(NOT_SUBSCRIBED)
        return

    # Use the centralized subscription formatting function
    subscription_text = format_subscription_list(_subscriptions, include_count=True)
    _message = await message.answer(subscription_text, parse_mode="Markdown")

    # Get applications for detailed dump
    applications = await ApplicationModel.find(
        {"session_id": {"$in": [s.session_id for s in _subscriptions]}}
    ).to_list()

    _msg_text = HEADER_APPLICATIONS

    for i, s in enumerate(_subscriptions):
        _msg_text += f"\n📑*{s.session_id}* \n"
        # Add statuses using centralized formatting
        _application = next(
            filter(lambda a: a.session_id == s.session_id, applications), None
        )
        if not _application:
            continue
        for j, st in enumerate(_application.statuses):
            _msg_text += _format_status_with_custom_template(st, "     *{status}* \n          _{date}_\n")

    _msg_text += f"\n{SUBSCRIPTION_COUNT_FORMAT.format(count=len(_subscriptions))}"

    await _message.edit_text(_msg_text, parse_mode="Markdown")
