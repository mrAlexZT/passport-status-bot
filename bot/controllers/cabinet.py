# Standard library imports
from datetime import datetime
from textwrap import dedent
from typing import Optional

# Third party imports
from aiogram import types

# Local application imports
from bot.core.api import Scraper
from bot.core.logger import log_function, log_error
from bot.core.models.application import ApplicationModel, StatusModel
from bot.core.models.user import UserModel
from bot.core.utils import (
    create_status_models_from_api_response,
    get_user_by_telegram_id,
    handle_invalid_session_id,
    handle_scraper_error,
    handle_user_not_found,
    safe_edit_message,
    show_typing_and_wait_message,
)


@log_function("cabinet")
async def cabinet(message: types.Message) -> None:
    """Show the user's cabinet with session and application status."""
    _message = await show_typing_and_wait_message(message, "Зачекайте, будь ласка, триває отримання даних...")
    if not _message:
        return

    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await handle_user_not_found(_message)
        return

    initial_message = dedent(
        f"""
            *Ваш кабінет:*
            Telegram ID: `{message.from_user.id}`
            Сесія: `{user.session_id}`
        """
    )

    await safe_edit_message(_message, initial_message, parse_mode="Markdown")

    application = await ApplicationModel.find_one({"session_id": user.session_id})
    if not application:
        return

    msg_text = initial_message + "\n*Статуси заявки:*\n"
    for i, s in enumerate(application.statuses, start=1):
        date = datetime.fromtimestamp(int(s.date) / 1000).strftime("%Y-%m-%d %H:%M")
        msg_text += f"{i}. *{s.status}* _{date}_\n\n"

    msg_text += dedent(
        f"""
            Останнє оновлення: {application.last_update.strftime("%Y-%m-%d %H:%M")}
        """
    )

    await safe_edit_message(_message, msg_text, parse_mode="Markdown")


@log_function("link")
async def link(message: types.Message) -> None:
    _message = await show_typing_and_wait_message(message, "Зачекайте, будь ласка, триває перевірка...")
    if not _message:
        return

    parts = message.text.split(" ")
    if len(parts) != 2:
        await handle_invalid_session_id(_message, "/link")
        return

    session_id = parts[1]

    # Check if user is already linked
    _user = await UserModel.find_one({"telegram_id": str(message.from_user.id)})
    if _user and _user.session_id:
        await safe_edit_message(
            _message,
            f"Ваш Telegram ID вже прив'язаний до ідентифікатора {_user.session_id}"
        )
        return

    # Validate session ID with scraper
    scraper = Scraper()
    status = scraper.check(session_id, retrive_all=True)

    if not status:
        await handle_scraper_error(_message)
        return

    # Create or update application
    _application = await ApplicationModel.find_one({"session_id": session_id})
    if not _application:
        _application = ApplicationModel(
            session_id=session_id,
            statuses=create_status_models_from_api_response(status),
            last_update=datetime.now(),
        )
        await _application.insert()

    # Create user record
    _user = UserModel(telegram_id=str(message.from_user.id), session_id=session_id)
    await _user.insert()

    await safe_edit_message(
        _message,
        f"Ваш Telegram ID успішно прив'язаний до ідентифікатора {_user.session_id}"
    )


@log_function("unlink")
async def unlink(message: types.Message) -> None:
    _message = await show_typing_and_wait_message(message, "Зачекайте, будь ласка, триває перевірка...")
    if not _message:
        return

    _user = await get_user_by_telegram_id(message.from_user.id)
    if not _user:
        await handle_user_not_found(_message)
        return

    session_id = _user.session_id
    await _user.delete()
    
    await safe_edit_message(
        _message,
        f"Ваш Telegram ID успішно відв'язаний від ідентифікатора {session_id}"
    )
