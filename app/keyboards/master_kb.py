from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def master_menu() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.button(text="📊 Сегодня")
    b.button(text="📅 Ближайшие")
    b.button(text="➕ Услуга")
    b.button(text="⏰ Часы работы")
    b.button(text="🔙 Выйти")
    b.adjust(2)
    return b.as_markup(resize_keyboard=True)