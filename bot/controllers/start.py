# Standard library imports
import textwrap

# Third party imports
from aiogram import types

# Local application imports
from bot.core.constants import ERROR_GENERIC
from bot.core.logger import log_function, log_error
from bot.core.utils import log_handler_error


@log_function("start")
async def start(message: types.Message) -> None:
    """Send a welcome message and instructions to the user."""
    try:
        await message.answer(
            textwrap.dedent(
                """
                    *Вітаю!*👋
                    
                    Цей бот повідомляє про зміни статусу вашої заявки на _passport.mfa.gov.ua_, щоб почати користуватися ботом надішліть свій ідентифікатор.
                    Для користування всіма функціями надішліть /cabinet або /help для детальнішої інформації.
                    
                    Важливо зазначити, що цей бот *НЕ ПОВ'ЯЗАНИЙ* з МЗС України, і не несе відповідальності за вірогідність чи своєчасність інформації, для детального пояснення надішліть /policy
                """
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        log_handler_error("start handler", message, e)
        await message.answer(ERROR_GENERIC)


@log_function("policy")
async def policy(message: types.Message) -> None:
    """Send the bot's privacy policy and data usage information."""
    try:
        await message.answer(
            textwrap.dedent(
                """
                    *Загальна інформація*
                    Бот розроблений для спрощення процесу відстеження статусу заявки на оформлення паспорту на сайті _passport.mfa.gov.ua_ незалежним розробником, і не пов'язаний з МЗС України.
                    Використання функцій бота не зобов'язує вас ні до чого, і не несе відповідальності за вірогідність чи своєчасність інформації, використання відбувається на ваш страх та ризик.

                    *Користування*
                    Функція відображення статусу заявки доступна лише після надіслання боту вашого ідентифікатора, який ви отримали при реєстрації заявки на сайті _passport.mfa.gov.ua_ ніяким чином не зберігається, і використовується лише для надіслання цього ідентифікатору на офіційний вебсайт.
                    Всі решта функцій доступні (кабінет, сповіщення про зміни статусу) - використовують базу даних та зберігають ваш Telegram ID, Ідентифікатор Сесії _passport.mfa.gov.ua_, та всі статуси заявки.
                    Використання цих функцій підтверджує вашу згоду на зберігання цих даних.

                    *Як використовується зібрана інформація*
                    Ваш Telegram ID використовується для ідентифікації вас в системі, і для надсилання вам сповіщень про зміну статусу заявки, а також привʼязки сесії.
                    Ваш ідентифікатор сесії використовується для отримання статусу заявки шляхом запиту на офіційний вебсайт _passport.mfa.gov.ua_.
                    Всі статуси заявки зберігаються для відтворення історії змін статусу заявки, та звірення нових статусів з попередніми для виявлення змін.

                    *Видалення даних*
                    Ви можете видалити всі дані, пов'язані з вашим Telegram ID, надіславши /delete. 

                    *Source Code*
                    Цей репозиторій є форком https://github.com/denver-code/passport-status-bot
                    Бот поширюється з відкритим вихідним кодом, ви можете переглянути його за посиланням:
                    https://github.com/mrAlexZT/passport-status-bot
                    та перевірити все вищезазначене, або ж підняти свій власний бот з власним функціоналом.
                """
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        log_handler_error("policy handler", message, e)
        await message.answer(ERROR_GENERIC)


def get_help_text(is_admin: bool) -> str:
    """Generate help text dynamically based on admin status."""
    from bot.__main__ import get_user_commands
    
    commands = get_user_commands(is_admin)
    
    help_lines = ["*Довідка*"]
    
    if is_admin:
        help_lines.append("*🔸 Адміністратор*")
        help_lines.append("")
    
    # Add all available commands for the user
    for cmd in commands:
        # Escape underscores in command names for proper Markdown display
        escaped_command = cmd.command.replace("_", "\\_")
        help_lines.append(f"{escaped_command} — {cmd.description}")
    
    if is_admin:
        help_lines.append("")
        help_lines.append("*Адміністраторські команди виділені окремо.*")
    
    return "\n".join(help_lines)


@log_function("help")
async def help(message: types.Message) -> None:
    """Send help and usage instructions to the user."""
    try:
        from bot.__main__ import is_admin
        
        user_is_admin = is_admin(message.from_user.id)
        help_text = get_help_text(user_is_admin)
        
        await message.answer(help_text, parse_mode="Markdown")
    except Exception as e:
        log_handler_error("help handler", message, e)
        await message.answer(ERROR_GENERIC)
