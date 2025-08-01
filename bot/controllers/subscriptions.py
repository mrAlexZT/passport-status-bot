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
from bot.core.logger import log_function, log_error
from bot.core.models.application import ApplicationModel, StatusModel
from bot.core.models.push import PushModel
from bot.core.models.user import SubscriptionModel, UserModel
from bot.core.notificator import notify_subscribers
from bot.core.utils import (
    check_subscription_limit,
    create_status_models_from_api_response,
    format_new_status_message,
    format_subscription_list,
    get_user_by_telegram_id,
    handle_generic_error,
    handle_invalid_session_id,
    handle_scraper_error,
    process_status_update,
    safe_edit_message,
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
    application = await ApplicationModel.find_one({"session_id": session_id})
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
    _message = await show_typing_and_wait_message(message, "Зачекайте, будь ласка, триває перевірка...")
    if not _message:
        return
    
    try:
        parts = message.text.split(" ")
        if len(parts) <= 1:
            await handle_invalid_session_id(_message, "/subscribe")
            return
        
        # Check subscription limit first
        if await check_subscription_limit(message.from_user.id):
            await safe_edit_message(
                _message,
                "Ви досягли максимальної кількості підписок на сповіщення про зміну статусу заявки"
            )
            return
        
        session_ids = parts[1:]
        successful_subscriptions = 0
        
        for session_id in session_ids:
            await safe_edit_message(
                _message,
                f"Зачекайте, будь ласка, триває оформлення підписки #{session_id}..."
            )
            
            if await _create_subscription_for_session(message.from_user.id, session_id):
                successful_subscriptions += 1
        
        if successful_subscriptions > 0:
            await safe_edit_message(_message, "Ви успішно підписані на сповіщення про зміну статусу")
        else:
            await safe_edit_message(_message, "Не вдалося створити підписки. Перевірте правильність ідентифікаторів.")
    
    except Exception as e:
        log_error("subscribe failed", getattr(message.from_user, 'id', None), e)
        await handle_generic_error(_message, "підписці")


@log_function("unsubscribe")
async def unsubscribe(message: types.Message) -> None:
    """Unsubscribe the user from notifications for a session ID."""
    _message = await show_typing_and_wait_message(message, "Зачекайте, будь ласка, триває перевірка...")
    if not _message:
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await handle_invalid_session_id(_message, "/unsubscribe")
            return
        
        session_id = parts[1]
        subscription = await SubscriptionModel.find_one(
            {"telegram_id": str(message.from_user.id), "session_id": session_id}
        )
        
        if not subscription:
            await safe_edit_message(
                _message,
                "Ви не підписані на сповіщення про зміну статусу заявки"
            )
            return
        
        await subscription.delete()
        await safe_edit_message(
            _message,
            "Ви успішно відписані від сповіщень про зміну статусу заявки"
        )
    except Exception as e:
        log_error("unsubscribe failed", getattr(message.from_user, 'id', None), e)
        await handle_generic_error(_message, "відписці")


@log_function("subscriptions")
async def subscriptions(message: types.Message) -> None:
    """Show the user's current subscriptions."""
    _message = await show_typing_and_wait_message(message, "Зачекайте, будь ласка, триває отримання даних...")
    if not _message:
        return
    
    try:
        user_subscriptions = await SubscriptionModel.find(
            {"telegram_id": str(message.from_user.id)}
        ).to_list()
        
        msg_text = format_subscription_list(user_subscriptions, include_count=True)
        await safe_edit_message(_message, msg_text, parse_mode="Markdown")
    except Exception as e:
        log_error("subscriptions failed", getattr(message.from_user, 'id', None), e)
        await handle_generic_error(_message, "отриманні підписок")


@log_function("manual_application_update")
async def manual_application_update(message: types.Message) -> None:
    """Manually update the user's application status."""
    _message = await message.answer("Зачекайте, будь ласка, триває отримання даних...")
    await message.answer_chat_action("typing")
    try:
        _user = await UserModel.find_one({"telegram_id": str(message.from_user.id)})
        _application = await ApplicationModel.find_one(
            {"session_id": _user.session_id} if _user else {}
        )
        if not _user or not _application:
            await _message.edit_text(
                "Вашого ідентифікатора не знайдено або заявка не знайдена."
            )
            return

        # Set wait time based on admin status
        _wait_time_minutes = 2 if is_admin(_user.telegram_id) else 60

        if _application.last_update > datetime.now() - timedelta(minutes=_wait_time_minutes):

            await _message.edit_text(
                f"Останнє оновлення було менше {_wait_time_minutes} хв тому, спробуйте пізніше.",
                parse_mode="Markdown",
            )
            return

        scraper = Scraper()
        status = scraper.check(_application.session_id, retrive_all=True)

        if not status:
            await _message.edit_text(
                "Виникла помилка перевірки ідентифікатора, можливо дані некоректні чи ще не внесені в базу, спробуйте пізніше."
            )
            return

        _statuses = []
        for s in status:
            _statuses.append(
                StatusModel(
                    status=s.get("status"),
                    date=s.get("date"),
                )
            )
        if len(_statuses) > len(_application.statuses):
            # find new statuses
            new_statuses = _statuses[len(_application.statuses) :]
            # notify subscribers
            await notify_subscribers()

            _msg_text = f"""
            Ми помітили зміну статусу заявки *#{_user.session_id}:*
            """

            for i, s in enumerate(new_statuses):
                _date = datetime.fromtimestamp(int(s.date) / 1000).strftime(
                    "%Y-%m-%d %H:%M"
                )
                _msg_text += f"{i+1}. *{s.status}* \n_{_date}_\n\n"

            await _message.edit_text(_msg_text, parse_mode="Markdown")
        else:
            await _message.edit_text(f"Статуси не змінилися.\n\n/cabinet - персональний кабінет", parse_mode="Markdown")

        _application.statuses = _statuses
        _application.last_update = datetime.now()

        await _application.save()
    except Exception as e:
        log_error("manual_application_update failed", getattr(message.from_user, 'id', None), e)
        await _message.edit_text("Виникла помилка при оновленні заявки. Спробуйте пізніше.")


@log_function("enable_push")
async def enable_push(message: types.Message):
    _push = await PushModel.find_one({"telegram_id": str(message.from_user.id)})
    if _push:
        await message.answer(
            f"Ви вже підписані на сповіщення про зміну статусу заявки.\nTopic: `MFA_{message.from_id}_{_push.secret_id}`",
            parse_mode="Markdown",
        )

        return

    # generate random secret id for push - lenght 32
    _secret_id = secrets.token_hex(16)

    _push = PushModel(
        telegram_id=str(message.from_user.id),
        secret_id=_secret_id,
    )
    await _push.insert()

    await message.answer(
        dedent(
            f"""
                Ви успішно підписані на сповіщення про зміну статусу заявки
                Ваш секретний ідентифікатор: {_secret_id}

                Щоб підписатиня на сповіщення, додайте наступний топік до NTFY.sh:
                `MFA_{message.from_id}_{_secret_id}`
            """,
        ),
        parse_mode="Markdown",
    )


@log_function("dump_subscriptions")
async def dump_subscriptions(message: types.Message):
    _subscriptions = await SubscriptionModel.find(
        {"telegram_id": str(message.from_user.id)}
    ).to_list()

    if not _subscriptions:
        await message.answer("Ви не підписані на сповіщення про зміну статусу заявки")
        return

    _msg_text = dedent(
        f"""
            *Ваші підписки:*
        """
    )

    for i, s in enumerate(_subscriptions):
        _msg_text += f"{i+1}. *{s.session_id}* \n"

    _msg_text += dedent(
        f"""
            Всього: {len(_subscriptions)}
        """
    )

    _message = await message.answer(_msg_text, parse_mode="Markdown")

    applications = await ApplicationModel.find(
        {"session_id": {"$in": [s.session_id for s in _subscriptions]}}
    ).to_list()

    _msg_text = dedent(
        f"""
            *Заявки:*
        """
    )

    for i, s in enumerate(_subscriptions):
        _msg_text += f"\n📑*{s.session_id}* \n"
        # add statuses
        _application = next(
            filter(lambda a: a.session_id == s.session_id, applications), None
        )
        if not _application:
            continue
        for j, st in enumerate(_application.statuses):
            _date = datetime.fromtimestamp(int(st.date) / 1000).strftime(
                "%Y-%m-%d %H:%M"
            )
            _msg_text += f"     *{st.status}* \n          _{_date}_\n"

    _msg_text += dedent(f"\nВсього: {len(_subscriptions)}")

    await _message.edit_text(_msg_text, parse_mode="Markdown")
