# -*- coding: utf-8 -*-
"""
Constants for messages and text used throughout the bot application.
Centralizes all duplicated text to ensure consistency and easy maintenance.
"""

# === WAIT MESSAGES ===
WAIT_CHECKING = "Зачекайте, будь ласка, триває перевірка..."
WAIT_DATA_LOADING = "Зачекайте, будь ласка, триває отримання даних..."
WAIT_PHOTO_ANALYSIS = "Зачекайте, будь ласка, триває аналіз фото..."
WAIT_SUBSCRIPTION_PROCESSING = "Зачекайте, будь ласка, триває оформлення підписки #{session_id}..."

# === SUCCESS MESSAGES ===
SUCCESS_SUBSCRIPTION_CREATED = "Ви успішно підписані на сповіщення про зміну статусу"
SUCCESS_SUBSCRIPTION_CREATED_DETAILED = "Ви успішно підписані на сповіщення про зміну статусу заявки"
SUCCESS_UNSUBSCRIPTION = "Ви успішно відписані від сповіщень про зміну статусу заявки"
SUCCESS_LINK_CREATED = "Ваш Telegram ID успішно прив'язаний до ідентифікатора {session_id}"
SUCCESS_LINK_REMOVED = "Ваш Telegram ID успішно відв'язаний від ідентифікатора {session_id}"

# === ERROR MESSAGES ===
ERROR_GENERIC = "Виникла помилка. Спробуйте пізніше."
ERROR_GENERIC_DETAILED = "Виникла помилка при {operation}. Спробуйте пізніше."
ERROR_CHECKING = "Виникла помилка, спробуйте пізніше."
ERROR_IDENTIFIER_VALIDATION = "Виникла помилка перевірки ідентифікатора, можливо дані некоректні чи ще не внесені в базу, спробуйте пізніше."
ERROR_QR_RECOGNITION = "Виникла помилка при розпізнаванні QR-коду. Спробуйте пізніше."
ERROR_APPLICATION_UPDATE = "Виникла помилка при оновленні заявки. Спробуйте пізніше."

# === NOT FOUND MESSAGES ===
NOT_FOUND_IDENTIFIER = "Вашого ідентифікатора не знайдено, надішліть його, будь ласка використовуючи команду /link \nНаприклад /link 1006655"
NOT_FOUND_IDENTIFIER_OR_APPLICATION = "Вашого ідентифікатора не знайдено або заявка не знайдена."
NOT_SUBSCRIBED = "Ви не підписані на сповіщення про зміну статусу заявки"

# === INSTRUCTION MESSAGES ===
INSTRUCTION_INVALID_SESSION_ID = "Надішліть ваш ідентифікатор, будь ласка використовуючи команду {command} \nНаприклад {command} 1006655"

# === STATUS MESSAGES ===
STATUS_NOT_CHANGED = "Статуси не змінилися.\n\n/cabinet - персональний кабінет"
STATUS_CHANGE_DETECTED = "Ми помітили зміну статусу заявки *#{session_id}:*\n"
STATUS_APPLICATION_HEADER = "Статуси заявки *#{session_id}:*\n\n"
STATUS_GENERAL_HEADER = "Статуси:\n\n"

# === SUBSCRIPTION MESSAGES ===
SUBSCRIPTION_LIMIT_REACHED = "Ви досягли максимальної кількості підписок на сповіщення про зміну статусу заявки"
SUBSCRIPTION_ALREADY_EXISTS = "Ви вже підписані на сповіщення про зміну статусу заявки.\nTopic: `MFA_{user_id}_{secret_id}`"
SUBSCRIPTION_CREATE_FAILED = "Не вдалося створити підписки. Перевірте правильність ідентифікаторів."

# === QR CODE MESSAGES ===
QR_NOT_RECOGNIZED = "QR-код не розпізнано. Переконайтеся, що фото чітке та спробуйте ще раз."
QR_RECOGNIZED = "Розпізнано QR-код: `{code}`"

# === SECTION HEADERS ===
HEADER_YOUR_SUBSCRIPTIONS = "*Ваші підписки:*\n"
HEADER_YOUR_CABINET = "*Ваш кабінет:*\nTelegram ID: `{user_id}`\nСесія: `{session_id}`\n"
HEADER_APPLICATION_STATUSES = "*Статуси заявки:*\n"
HEADER_APPLICATIONS = "*Заявки:*\n"

# === ADMIN MESSAGES ===
ADMIN_ONLY_COMMAND = "❌ Тільки адміністратор може користуватися цією командою!"

# === TIME FORMATTING ===
LAST_UPDATE_FORMAT = "Останнє оновлення: {timestamp}"
SUBSCRIPTION_COUNT_FORMAT = "Всього: {count}"

# === PUSH NOTIFICATION MESSAGES ===
PUSH_SUCCESS_MESSAGE = """Ви успішно підписані на сповіщення про зміну статусу заявки
Ваш секретний ідентифікатор: {secret_id}

Щоб підписатиня на сповіщення, додайте наступний топік до NTFY.sh:
`MFA_{user_id}_{secret_id}`"""

# === RATE LIMIT MESSAGES ===
RATE_LIMIT_WAIT_MESSAGE = "Останнє оновлення було менше {minutes} хв тому, спробуйте пізніше."