from datetime import datetime
import requests

from bot.core.logger import log_function
from bot.core.models.application import ApplicationModel, StatusModel
from bot.core.models.push import PushModel
from bot.core.models.user import SubscriptionModel
from bot.core.utils import format_new_status_message
from bot.bot_instance import bot


@log_function("send_push")
def send_push(user, title, message):
    requests.post(
        f"https://ntfy.sh/{user}",
        data=message.encode(encoding="utf-8"),
        headers={
            "Title": title.encode(encoding="utf-8"),
            "Priority": "urgent",
        },
    )


@log_function("notify_subscribers")
async def notify_subscribers(
    target_application: ApplicationModel = None, new_statuses: list[StatusModel] = None
):
    if target_application:
        _subscriptions = await SubscriptionModel.find(
            {"session_id": target_application.session_id}
        ).to_list()
    else:
        _subscriptions = await SubscriptionModel.find({}).to_list()

    if not _subscriptions:
        return

    # Use centralized status message formatting
    _msg_text = format_new_status_message(target_application.session_id, new_statuses)

    for _subscription in _subscriptions:
        _push_subscription = await PushModel.find_one(
            {"telegram_id": _subscription.telegram_id}
        )
        if _push_subscription:
            _message = f""
            for status in new_statuses:
                _message += f"{status.status}\n"
            send_push(
                f"MFA_{_subscription.telegram_id}_{_push_subscription.secret_id}",
                f"Оновлення заявки #{target_application.session_id}",
                _message,
            )

        try:
            await bot.send_message(
                _subscription.telegram_id,
                _msg_text,
                parse_mode="Markdown",
            )
        except:
            pass
