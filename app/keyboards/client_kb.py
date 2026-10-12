from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.database.models import Service


def main_menu() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.button(text="Записаться")
    b.button(text="Мои записи")
    b.button(text="Помощь")
    b.adjust(2, 1)
    return b.as_markup(resize_keyboard=True)


def services_kb(services: list[Service]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in services:
        b.button(
            text=f"{s.name} · {s.duration_min} мин · {s.price} руб",
            callback_data=f"svc|{s.id}",
        )
    b.adjust(1)
    return b.as_markup()


def dates_kb(service_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    today = date.today()
    for i in range(1, 8):
        d = today + timedelta(days=i)
        b.button(text=d.strftime("%d.%m"), callback_data=f"date|{service_id}|{d.isoformat()}")
    b.button(text="Назад", callback_data="back|services")
    b.adjust(2)
    return b.as_markup()


def slots_kb(service_id: int, day_iso: str, slots: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in slots:
        b.button(text=t, callback_data=f"slot|{service_id}|{day_iso}|{t}")
    b.button(text="Назад", callback_data=f"back|dates|{service_id}")
    b.adjust(3)
    return b.as_markup()


def confirm_kb(service_id: int, day_iso: str, time_str: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Подтвердить", callback_data=f"cfm|{service_id}|{day_iso}|{time_str}")
    b.button(text="Отмена", callback_data="back|services")
    b.adjust(1)
    return b.as_markup()


def my_bookings_kb(bookings) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for bk in bookings:
        b.button(text=f"Перенести #{bk.id}", callback_data=f"resched|{bk.id}")
        b.button(text=f"Отменить #{bk.id}", callback_data=f"cancel|{bk.id}")
    b.adjust(2)
    return b.as_markup()


def resched_confirm_kb(booking_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Да, перенести", callback_data=f"resched_yes|{booking_id}")
    b.button(text="Отмена", callback_data="resched_no")
    b.adjust(1)
    return b.as_markup()


def rating_kb(booking_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i in range(1, 6):
        b.button(text=str(i), callback_data=f"rate|{booking_id}|{i}")
    b.adjust(5)
    return b.as_markup()


def comment_kb(booking_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Оставить комментарий", callback_data=f"comment|{booking_id}")
    b.button(text="Пропустить", callback_data=f"nocomment|{booking_id}")
    b.adjust(1)
    return b.as_markup()