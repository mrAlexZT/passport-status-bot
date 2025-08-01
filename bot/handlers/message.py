from aiogram import Dispatcher

from bot.controllers.message import custom_check, image_qr_recognition
from bot.core.logger import log_function


@log_function("setup_message_handlers")
def setup(dp: Dispatcher):
    dp.register_message_handler(custom_check, regexp=r"^\d{6,7}$", state="*")
    dp.register_message_handler(
        image_qr_recognition, content_types=["photo"], state="*"
    )
