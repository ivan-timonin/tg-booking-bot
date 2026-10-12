from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.database.models import Service


def main_menu() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.button(text="📅 Записаться")
    b.button(text="🗂 Мои записи")
    b.button(text="ℹ️ Помощь")
    b.adjust(2, 1)
    return b.as_markup(resize_keyboard=True)


def services_kb(services: list[Service]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in services:
        b.button(text=f"{s.name} · {s.duration_min} мин · {s.price} ₽", callback_data=f"svc|{s.id}")
    b.adjust(1)
    return b.as_markup()


def dates_kb(service_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    today = date.today()
    for i in range(1, 8):
        d = today + timedelta(days=i)
        b.button(text=d.strftime("%d.%m (%a)"), callback_data=f"date|{service_id}|{d.isoformat()}")
    b.button(text="⬅️ Назад", callback_data="back|services")
    b.adjust(2)
    return b.as_markup()


def slots_kb(service_id: int, day_iso: str, slots: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in slots:
        b.button(text=t, callback_data=f"slot|{service_id}|{day_iso}|{t}")
    b.button(text="⬅️ Назад", callback_data=f"back|dates|{service_id}")
    b.adjust(3)
    return b.as_markup()


def confirm_kb(service_id: int, day_iso: str, time_str: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Подтвердить", callback_data=f"cfm|{service_id}|{day_iso}|{time_str}")
    b.button(text="❌ Отмена", callback_data="back|services")
    b.adjust(1)
    return b.as_markup()


def my_bookings_kb(bookings) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for bk in bookings:
        b.button(text=f"❌ Отменить #{bk.id}", callback_data=f"cancel|{bk.id}")
    b.adjust(1)
    return b.as_markup()