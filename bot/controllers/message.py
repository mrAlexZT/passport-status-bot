# Standard library imports
from datetime import datetime

# Third party imports
import cv2
import numpy as np
from aiogram import types
from PIL import Image
from qreader import QReader

# Local application imports
from bot.core.api import Scraper
from bot.core.constants import *
from bot.core.logger import log_function, log_error
from bot.core.utils import (
    format_status_list,
    log_handler_error,
    safe_answer_message,
    safe_edit_message,
    show_typing_action,
)


@log_function("custom_check")
async def custom_check(message: types.Message) -> None:
    """Check application status by ID and reply with formatted status list."""
    _message = await safe_answer_message(message, WAIT_CHECKING)
    if not _message:
        return
    
    await show_typing_action(message)
    try:
        scraper = Scraper()
        status_data = scraper.check(message.text, retrive_all=True)
        if not status_data:
            await safe_edit_message(_message, ERROR_CHECKING)
            return
        
        # Use the centralized status formatting function
        from bot.core.utils import create_status_models_from_api_response
        statuses = create_status_models_from_api_response(status_data)
        formatted_text = format_status_list(statuses, session_id=message.text)
        
        await safe_edit_message(_message, formatted_text, parse_mode="Markdown")
    except Exception as e:
        log_handler_error("custom_check", message, e)
        await safe_edit_message(_message, ERROR_GENERIC_DETAILED.format(operation="перевірці"))


@log_function("image_qr_recognition")
async def image_qr_recognition(message: types.Message) -> None:
    """Recognize QR code from an image and reply with the decoded value or error."""
    _message = await safe_answer_message(message, WAIT_PHOTO_ANALYSIS)
    if not _message:
        return
    
    await show_typing_action(message)
    try:
        file = await message.bot.get_file(message.photo[-1].file_id)
        download_file = await message.bot.download_file(file.file_path)
        photo: Image = Image.open(download_file)
        image = cv2.cvtColor(np.array(photo), cv2.COLOR_RGB2BGR)
        qr = QReader()
        decoded = qr.detect_and_decode(image=image)
        if not decoded:
            await safe_edit_message(_message, QR_NOT_RECOGNIZED)
            return
        await safe_edit_message(_message, QR_RECOGNIZED.format(code=decoded), parse_mode="Markdown")
    except Exception as e:
        log_handler_error("image_qr_recognition", message, e)
        await safe_edit_message(_message, ERROR_QR_RECOGNITION)
