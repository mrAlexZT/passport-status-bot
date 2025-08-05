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
ADMIN_USERS_LIST_HEADER = "*📊 Список користувачів:*\n"
ADMIN_CLEANUP_START = "*🔍 Аналіз бази даних...*"
ADMIN_CLEANUP_ANALYZING = "*⏳ Аналіз даних...*"
ADMIN_CLEANUP_DELETING = "*🗑 Видалення даних...*"
ADMIN_CLEANUP_CONFIRM = """*⚠️ Знайдено невалідні дані:*

*Користувачі для видалення:* `{users}`
*Підписки для видалення:* `{subs}`

*Деталі:*
• Користувачі без telegram\_id: `{users_no_id}`
• Користувачі з невалідними даними: `{users_invalid}`
• Підписки без telegram\_id: `{subs_no_id}`
• Підписки без session\_id: `{subs_no_session}`
• Підписки від видалених користувачів: `{subs_orphaned}`

⚠️ *Увага: Ця дія незворотня\!*"""

ADMIN_CLEANUP_CONFIRM_BUTTON = "✅ Підтвердити видалення"
ADMIN_CLEANUP_CANCEL_BUTTON = "❌ Скасувати"
ADMIN_CLEANUP_CANCELLED = "_Операцію скасовано_"
ADMIN_CLEANUP_PROCESSING = "Видалення..."
ADMIN_CLEANUP_CANCELLED_POPUP = "Операцію скасовано"
ADMIN_CLEANUP_NO_PERMISSION = "❌ Недостатньо прав"
ADMIN_CLEANUP_EXPIRED = "*⚠️ Дані застаріли. Будь ласка, запустіть команду /cleanup знову.*"
ADMIN_CLEANUP_RESULT = """*✅ Очищення завершено:*

*Видалено користувачів:* `{users}`
*Видалено підписок:* `{subs}`

*Деталі:*
• Користувачі без telegram\_id: `{users_no_id}`
• Користувачі з невалідними даними: `{users_invalid}`
• Підписки без telegram\_id: `{subs_no_id}`
• Підписки без session\_id: `{subs_no_session}`
• Підписки від видалених користувачів: `{subs_orphaned}`"""
ADMIN_CLEANUP_ERROR = "❌ Помилка при очищенні бази даних. Перевірте логи."
ADMIN_CLEANUP_NOTHING = "*✅ База даних не містить невалідних даних.*"
ADMIN_USER_ENTRY = "👤 *ID:* `{telegram_id}`"
ADMIN_USER_SESSION = "   *Сесія:* `{session_id}`"
ADMIN_USER_SUBSCRIPTIONS_HEADER = "   *Підписки:*"
ADMIN_USER_NO_SUBSCRIPTIONS = "   *Підписки:* немає"
ADMIN_USER_SUBSCRIPTION_ENTRY = "   • `{sub_id}`"
ADMIN_TOTAL_STATS = "\n*Всього користувачів:* {users}\n*Всього підписок:* {subs}"
ADMIN_INVALID_DATA_WARNING = "\n⚠️ *Увага:* Знайдено {invalid_users} невалідних користувачів та {invalid_subs} невалідних підписок"

# === VERSION MESSAGES ===
VERSION_ERROR = "❌ *Не вдалося отримати інформацію про версію*"
VERSION_FORMAT = "🤖 Версія бота: *v{version}*\n📦 [Завантажити останню версію]({link})"
VERSION_UPDATE_ERROR = "❌ Помилка при отриманні інформації про версію"
VERSION_API_ERROR = "Помилка при запиті до GitHub API: {error}"
VERSION_NO_RELEASES = "Репозиторій не має релізів"

# === TIME FORMATTING ===
LAST_UPDATE_FORMAT = "Останнє оновлення: {timestamp}"
SUBSCRIPTION_COUNT_FORMAT = "Всього: {count}"

# === PUSH NOTIFICATION MESSAGES ===
PUSH_SUCCESS_MESSAGE = """Ви успішно підписані на сповіщення про зміну статусу заявки
Ваш секретний ідентифікатор: {secret_id}

Щоб підписатиня на сповіщення, додайте наступний топік до NTFY.sh:
`MFA_{user_id}_{secret_id}`"""

PUSH_NOTIFICATION_TITLE = "Оновлення заявки #{session_id}"
PUSH_NOTIFICATION_ERROR = "Помилка при надсиланні сповіщення користувачу {telegram_id}: {error}"
PUSH_NOTIFICATION_SEND_ERROR = "Помилка при надсиланні сповіщення через Telegram: {error}"

# === COMMAND MESSAGES ===
COMMAND_NOT_FOUND = "❌ Команду {command} не знайдено.\n\nСкористайтеся /help для перегляду списку доступних команд."

# === AUTHORS INFO ===
AUTHORS_MESSAGE = """👨‍💻 *Автори бота:*

*1\. Автор ідеї та розробник:* Ihor Savenko
   • [👨‍💻 GitHub](https://github.com/denver-code)
   • [🌐 Website](https://ihorsavenko.com/)
   • [✈️ Telegram](https://t.me/operatorSilence)
   • [💬 Discord](https://discord.gg/operatorsilence)
   • [📧 Email](mailto:contact@ihorsavenko.com)

*2\. Розробник:* Oleksandr Shevchenko
   • [👨‍💻 GitHub](https://github.com/mrAlexZT)

*Про проект:*
📦 *Версія:* v{version}
📚 *Репозиторій:* [passport-status-bot]({repo_link})
📝 *Ліцензія:* MIT

*Технічна інформація:*
🔧 Python, MongoDB, aiogram
🤖 Telegram Bot API
🔄 Асинхронна архітектура

Дякуємо за використання нашого бота\! 🙏"""

# === RATE LIMIT MESSAGES ===
RATE_LIMIT_WAIT_MESSAGE = "Останнє оновлення було менше {minutes} хв тому, спробуйте пізніше."