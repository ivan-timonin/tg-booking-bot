from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Booking, Review, Service
from app.database.repo import (
    get_active_services,
    get_future_bookings,
    get_or_create_user,
    get_review_by_booking,
    save_review,
)
from app.keyboards.client_kb import (
    comment_kb,
    confirm_kb,
    dates_kb,
    my_bookings_kb,
    rating_kb,
    resched_confirm_kb,
    services_kb,
    slots_kb,
)
from app.services.slots import get_free_slots
from app.states import LeaveComment

router = Router()


@router.message(F.text == "Записаться")
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
        f"<b>{service.name}</b>\n{service.duration_min} мин · {service.price} руб\n\nВыберите дату:",
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
        f"{local_dt:%d.%m.%Y %H:%M}\n"
        f"{service.duration_min} мин · {service.price} руб",
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
        f"Готово! Вы записаны на <b>{service.name}</b>\n{local_dt:%d.%m.%Y %H:%M}"
    )
    await cb.answer("Запись создана")

    try:
        await cb.bot.send_message(
            settings.master_tg_id,
            f"<b>Новая запись</b>\n"
            f"{cb.from_user.full_name}\n"
            f"{service.name}\n"
            f"{local_dt:%d.%m.%Y %H:%M}",
        )
    except Exception:
        pass


@router.message(F.text == "Мои записи")
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
    await cb.message.edit_text(f"Запись #{bk.id} отменена.")
    await cb.answer()

    try:
        await cb.bot.send_message(settings.master_tg_id, f"Отмена записи #{bk.id}")
    except Exception:
        pass


@router.callback_query(F.data.startswith("resched|"))
async def resched_ask(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split("|")[1])
    bk = await session.get(Booking, bk_id)
    if not bk or bk.status != "active":
        await cb.answer("Запись не найдена", show_alert=True)
        return

    user = await get_or_create_user(session, cb.from_user.id)
    if bk.client_id != user.id:
        await cb.answer("Это не ваша запись", show_alert=True)
        return

    s = await session.get(Service, bk.service_id)
    await cb.message.edit_text(
        f"Перенести запись на «{s.name}»?\n\n"
        "Текущая запись будет отменена, затем вы выберете новую дату и время.",
        reply_markup=resched_confirm_kb(bk_id),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("resched_yes|"))
async def resched_yes(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split("|")[1])
    bk = await session.get(Booking, bk_id)
    if not bk or bk.status != "active":
        await cb.answer("Запись не найдена", show_alert=True)
        return

    user = await get_or_create_user(session, cb.from_user.id)
    if bk.client_id != user.id:
        await cb.answer("Это не ваша запись", show_alert=True)
        return

    service_id = bk.service_id
    bk.status = "rescheduled"
    await session.commit()

    service = await session.get(Service, service_id)
    await cb.message.edit_text(
        f"<b>{service.name}</b>\n{service.duration_min} мин · {service.price} руб\n\nВыберите новую дату:",
        reply_markup=dates_kb(service_id),
    )
    await cb.answer("Старая запись отменена")

    try:
        await cb.bot.send_message(
            settings.master_tg_id,
            f"Клиент переносит запись #{bk_id} ({service.name})",
        )
    except Exception:
        pass


@router.callback_query(F.data == "resched_no")
async def resched_no(cb: CallbackQuery, session: AsyncSession):
    user = await get_or_create_user(session, cb.from_user.id)
    bookings = await get_future_bookings(session, user.id)
    if not bookings:
        await cb.message.edit_text("У вас нет активных записей.")
        await cb.answer()
        return

    tz = ZoneInfo(settings.tz)
    lines = []
    for bk in bookings:
        s = await session.get(Service, bk.service_id)
        local = bk.start_at.replace(tzinfo=timezone.utc).astimezone(tz)
        lines.append(f"#{bk.id} · {s.name} · {local:%d.%m %H:%M}")
    await cb.message.edit_text(
        "Ваши записи:\n" + "\n".join(lines),
        reply_markup=my_bookings_kb(bookings),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("rate|"))
async def rate_booking(cb: CallbackQuery, session: AsyncSession):
    _, bid, rating_str = cb.data.split("|")
    booking_id = int(bid)
    rating = int(rating_str)

    bk = await session.get(Booking, booking_id)
    if not bk:
        await cb.answer("Запись не найдена", show_alert=True)
        return

    user = await get_or_create_user(session, cb.from_user.id)
    if bk.client_id != user.id:
        await cb.answer("Это не ваша запись", show_alert=True)
        return

    existing = await get_review_by_booking(session, booking_id)
    if existing is None:
        await save_review(
            session,
            booking_id=booking_id,
            client_id=user.id,
            service_id=bk.service_id,
            rating=rating,
            comment=None,
        )
    else:
        existing.rating = rating
        await session.commit()

    bk.review_requested = True
    await session.commit()

    await cb.message.edit_text(
        f"Спасибо за оценку: {rating}/5\n\nХотите оставить комментарий?",
        reply_markup=comment_kb(booking_id),
    )
    await cb.answer()

    try:
        await cb.bot.send_message(
            settings.master_tg_id,
            f"<b>Новый отзыв</b>\nОценка: {rating}/5",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("comment|"))
async def comment_start(cb: CallbackQuery, state: FSMContext):
    booking_id = int(cb.data.split("|")[1])
    await state.update_data(booking_id=booking_id)
    await state.set_state(LeaveComment.waiting)
    await cb.message.edit_text("Напишите ваш комментарий одним сообщением:")
    await cb.answer()


@router.callback_query(F.data.startswith("nocomment|"))
async def comment_skip(cb: CallbackQuery):
    await cb.message.edit_text("Спасибо за отзыв!")
    await cb.answer()


@router.message(LeaveComment.waiting)
async def comment_save(msg: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    booking_id = data.get("booking_id")
    text = (msg.text or "").strip()[:500]

    existing = await get_review_by_booking(session, booking_id)
    if existing is None:
        await state.clear()
        await msg.answer("Что-то пошло не так. Попробуйте ещё раз.")
        return

    existing.comment = text or None
    await session.commit()
    await state.clear()

    await msg.answer("Спасибо! Комментарий сохранён.")

    try:
        await msg.bot.send_message(
            settings.master_tg_id,
            f"<b>Комментарий к отзыву</b>\nОценка: {existing.rating}/5\n{text}",
        )
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