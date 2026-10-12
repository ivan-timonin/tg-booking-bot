from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.database.models import Service


def master_menu() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.button(text="Сегодня")
    b.button(text="Ближайшие")
    b.button(text="Добавить услугу")
    b.button(text="Услуги")
    b.button(text="Часы работы")
    b.button(text="Выйти")
    b.adjust(2)
    return b.as_markup(resize_keyboard=True)


def services_admin_kb(services: list[Service]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in services:
        status = "скрыта" if not s.is_active else "активна"
        b.button(text=f"{s.name} ({status})", callback_data=f"svc_toggle|{s.id}")
        b.button(text="Удалить", callback_data=f"svc_del|{s.id}")
    b.adjust(2)
    return b.as_markup()


def confirm_delete_kb(service_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Да, удалить", callback_data=f"svc_del_yes|{service_id}")
    b.button(text="Отмена", callback_data="svc_back")
    b.adjust(1)
    return b.as_markup()