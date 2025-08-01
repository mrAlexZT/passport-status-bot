from datetime import datetime
from aiogram import types
from PIL import Image
import numpy as np
from qreader import QReader
import cv2
from bot.core.api import Scraper
from bot.core.logger import log_function, log_error


@log_function("custom_check")
async def custom_check(message: types.Message) -> None:
    """Check application status by ID and reply with formatted status list."""
    _message = await message.answer("Зачекайте, будь ласка, триває перевірка...")
    await message.answer_chat_action("typing")
    try:
        scraper = Scraper()
        status = scraper.check(message.text, retrive_all=True)
        if not status:
            await _message.edit_text("Виникла помилка, спробуйте пізніше.")
            return
        _msg_text = f"Статуси заявки *#{message.text}:*\n\n"
        for i, s in enumerate(status):
            _date = datetime.fromtimestamp(int(s.get("date")) / 1000).strftime(
                "%Y-%m-%d %H:%M"
            )
            _msg_text += f"{i+1}. *{s.get('status')}* \n_{_date}_\n\n"
        await _message.edit_text(_msg_text, parse_mode="Markdown")
    except Exception as e:
        log_error("custom_check failed", getattr(message.from_user, 'id', None), e)
        await _message.edit_text("Виникла помилка при перевірці. Спробуйте пізніше.")


@log_function("image_qr_recognition")
async def image_qr_recognition(message: types.Message) -> None:
    """Recognize QR code from an image and reply with the decoded value or error."""
    _message = await message.answer("Зачекайте, будь ласка, триває аналіз фото...")
    await message.answer_chat_action("typing")
    try:
        file = await message.bot.get_file(message.photo[-1].file_id)
        download_file = await message.bot.download_file(file.file_path)
        photo: Image = Image.open(download_file)
        image = cv2.cvtColor(np.array(photo), cv2.COLOR_RGB2BGR)
        qr = QReader()
        decoded = qr.detect_and_decode(image=image)
        if not decoded:
            await _message.edit_text("QR-код не розпізнано. Переконайтеся, що фото чітке та спробуйте ще раз.")
            return
        await _message.edit_text(f"Розпізнано QR-код: `{decoded}`", parse_mode="Markdown")
    except Exception as e:
        log_error("image_qr_recognition failed", getattr(message.from_user, 'id', None), e)
        await _message.edit_text("Виникла помилка при розпізнаванні QR-коду. Спробуйте пізніше.")
