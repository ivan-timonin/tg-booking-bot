from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.database.models import Service


def master_menu() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.button(text="Сегодня")
    b.button(text="Ближайшие")
    b.button(text="Клиенты")
    b.button(text="Отзывы")
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
        b.button(text="Изменить", callback_data=f"svc_edit|{s.id}")
        b.button(text="Удалить", callback_data=f"svc_del|{s.id}")
    b.adjust(3)
    return b.as_markup()


def confirm_delete_kb(service_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Да, удалить", callback_data=f"svc_del_yes|{service_id}")
    b.button(text="Отмена", callback_data="svc_back")
    b.adjust(1)
    return b.as_markup()


def edit_service_kb(service_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Название", callback_data=f"svc_edit_name|{service_id}")
    b.button(text="Цена", callback_data=f"svc_edit_price|{service_id}")
    b.button(text="Длительность", callback_data=f"svc_edit_duration|{service_id}")
    b.button(text="Отмена", callback_data="svc_back")
    b.adjust(1)
    return b.as_markup()


def clients_list_kb(clients: list[tuple]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for row in clients:
        cid = row[0]
        name = row[1] or "Без имени"
        cnt = row[5]
        b.button(text=f"{name} ({cnt})", callback_data=f"client|{cid}")
    b.adjust(1)
    return b.as_markup()


def client_card_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Назад к списку", callback_data="clients_back")
    b.adjust(1)
    return b.as_markup()


def reviews_refresh_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Обновить", callback_data="reviews_refresh")
    b.adjust(1)
    return b.as_markup()