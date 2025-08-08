from aiogram import Dispatcher, F

from bot.controllers.message import custom_check, image_qr_recognition
from bot.core.logger import log_function


@log_function("setup_message_handlers")
def setup(dp: Dispatcher):
    dp.message.register(custom_check, F.text.regexp(r"^\d{6,7}$"))
    dp.message.register(image_qr_recognition, F.photo)
