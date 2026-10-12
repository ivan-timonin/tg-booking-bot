from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Booking, Service
from app.database.repo import get_active_services, get_future_bookings, get_or_create_user
from app.keyboards.client_kb import (
    confirm_kb,
    dates_kb,
    my_bookings_kb,
    services_kb,
    slots_kb,
)
from app.services.slots import get_free_slots

router = Router()


@router.message(F.text == "📅 Записаться")
async def start_booking(msg: Message, session: AsyncSession):
    services = await get_active_services(session)
    if not services:
        await msg.answer("Пока нет доступных услуг. Загляните позже.")
        return
    await msg.answer("Выберите услугу:", reply_markup=services_kb(services))


@router.callback_query(F.data.startswith("svc|"))
async def choose_service(cb: CallbackQuery, session: AsyncSession):
    service_id = int(cb.data.split("|")[1])
    service = await session.get(Service, service_id)
    if not service:
        await cb.answer("Услуга недоступна", show_alert=True)
        return
    await cb.message.edit_text(
        f"<b>{service.name}</b>\n{service.duration_min} мин · {service.price} ₽\n\nВыберите дату:",
        reply_markup=dates_kb(service_id),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("date|"))
async def choose_date(cb: CallbackQuery, session: AsyncSession):
    _, sid, day_iso = cb.data.split("|")
    service_id = int(sid)
    service = await session.get(Service, service_id)
    tz = ZoneInfo(settings.tz)
    day = datetime.fromisoformat(day_iso).date()
    slots = await get_free_slots(session, day, service.duration_min, tz)
    if not slots:
        await cb.answer("На этот день нет свободных слотов", show_alert=True)
        return
    slot_strs = [s.strftime("%H:%M") for s in slots]
    await cb.message.edit_text(
        f"<b>{service.name}</b> · {day:%d.%m}\nВыберите время:",
        reply_markup=slots_kb(service_id, day_iso, slot_strs),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("slot|"))
async def choose_slot(cb: CallbackQuery, session: AsyncSession):
    _, sid, day_iso, time_str = cb.data.split("|")
    service_id = int(sid)
    service = await session.get(Service, service_id)
    tz = ZoneInfo(settings.tz)
    local_dt = datetime.fromisoformat(f"{day_iso}T{time_str}").replace(tzinfo=tz)
    await cb.message.edit_text(
        f"Подтвердите запись:\n\n"
        f"<b>{service.name}</b>\n"
        f"📅 {local_dt:%d.%m.%Y %H:%M}\n"
        f"⏱ {service.duration_min} мин · {service.price} ₽",
        reply_markup=confirm_kb(service_id, day_iso, time_str),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("cfm|"))
async def confirm_booking(cb: CallbackQuery, session: AsyncSession):
    _, sid, day_iso, time_str = cb.data.split("|")
    service_id = int(sid)
    service = await session.get(Service, service_id)
    tz = ZoneInfo(settings.tz)
    local_dt = datetime.fromisoformat(f"{day_iso}T{time_str}").replace(tzinfo=tz)
    start_utc = local_dt.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = start_utc + timedelta(minutes=service.duration_min)

    user = await get_or_create_user(session, cb.from_user.id, cb.from_user.full_name)

    q = select(Booking).where(
        Booking.status == "active",
        Booking.start_at < end_utc,
        Booking.end_at > start_utc,
    )
    if (await session.execute(q)).scalars().first():
        await cb.answer("Увы, слот уже занят. Выберите другой.", show_alert=True)
        return

    bk = Booking(
        client_id=user.id,
        service_id=service.id,
        start_at=start_utc,
        end_at=end_utc,
        status="active",
    )
    session.add(bk)
    await session.commit()
    await session.refresh(bk)

    await cb.message.edit_text(
        f"✅ Готово! Вы записаны на <b>{service.name}</b>\n📅 {local_dt:%d.%m.%Y %H:%M}"
    )
    await cb.answer("Запись создана")

    try:
        await cb.bot.send_message(
            settings.master_tg_id,
            f"🔔 <b>Новая запись</b>\n"
            f"👤 {cb.from_user.full_name}\n"
            f"💼 {service.name}\n"
            f"📅 {local_dt:%d.%m.%Y %H:%M}",
        )
    except Exception:
        pass


@router.message(F.text == "🗂 Мои записи")
async def my_bookings(msg: Message, session: AsyncSession):
    user = await get_or_create_user(session, msg.from_user.id, msg.from_user.full_name)
    bookings = await get_future_bookings(session, user.id)
    if not bookings:
        await msg.answer("У вас нет активных записей.")
        return

    tz = ZoneInfo(settings.tz)
    lines = []
    for bk in bookings:
        s = await session.get(Service, bk.service_id)
        local = bk.start_at.replace(tzinfo=timezone.utc).astimezone(tz)
        lines.append(f"#{bk.id} · {s.name} · {local:%d.%m %H:%M}")
    await msg.answer("Ваши записи:\n" + "\n".join(lines), reply_markup=my_bookings_kb(bookings))


@router.callback_query(F.data.startswith("cancel|"))
async def cancel_booking(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split("|")[1])
    bk = await session.get(Booking, bk_id)
    if not bk or bk.status != "active":
        await cb.answer("Запись не найдена", show_alert=True)
        return

    user = await get_or_create_user(session, cb.from_user.id)
    if bk.client_id != user.id:
        await cb.answer("Это не ваша запись", show_alert=True)
        return

    bk.status = "cancelled"
    await session.commit()
    await cb.message.edit_text(f"❌ Запись #{bk.id} отменена.")
    await cb.answer()

    try:
        await cb.bot.send_message(settings.master_tg_id, f"❌ Отмена записи #{bk.id}")
    except Exception:
        pass


@router.callback_query(F.data == "back|services")
async def back_services(cb: CallbackQuery, session: AsyncSession):
    services = await get_active_services(session)
    await cb.message.edit_text("Выберите услугу:", reply_markup=services_kb(services))
    await cb.answer()


@router.callback_query(F.data.startswith("back|dates|"))
async def back_dates(cb: CallbackQuery, session: AsyncSession):
    service_id = int(cb.data.split("|")[2])
    service = await session.get(Service, service_id)
    await cb.message.edit_text(
        f"<b>{service.name}</b>\nВыберите дату:",
        reply_markup=dates_kb(service_id),
    )
    await cb.answer()