from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Booking, BotSettings, Service, User
from app.keyboards.client_kb import main_menu
from app.keyboards.master_kb import master_menu
from app.states import AddService, EditHours

router = Router()


def _is_master(user_id: int) -> bool:
    return user_id == settings.master_tg_id


@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not _is_master(msg.from_user.id):
        return
    await msg.answer("Панель мастера:", reply_markup=master_menu())


@router.message(F.text == "📊 Сегодня")
async def today(msg: Message, session: AsyncSession):
    if not _is_master(msg.from_user.id):
        return
    tz = ZoneInfo(settings.tz)
    now_local = datetime.now(tz)
    day_start = (
        datetime.combine(now_local.date(), time.min, tzinfo=tz)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )
    day_end = day_start + timedelta(days=1)

    q = (
        select(Booking)
        .where(
            Booking.status == "active",
            Booking.start_at >= day_start,
            Booking.start_at < day_end,
        )
        .order_by(Booking.start_at)
    )
    bookings = list((await session.execute(q)).scalars().all())
    if not bookings:
        await msg.answer("На сегодня записей нет.")
        return

    lines = []
    for bk in bookings:
        u = await session.get(User, bk.client_id)
        s = await session.get(Service, bk.service_id)
        local = bk.start_at.replace(tzinfo=timezone.utc).astimezone(tz)
        lines.append(f"{local:%H:%M} · {s.name} · {u.name or u.tg_id}")
    await msg.answer("📊 <b>Сегодня</b>\n" + "\n".join(lines))


@router.message(F.text == "📅 Ближайшие")
async def upcoming(msg: Message, session: AsyncSession):
    if not _is_master(msg.from_user.id):
        return
    tz = ZoneInfo(settings.tz)
    now_utc = datetime.utcnow()
    q = (
        select(Booking)
        .where(Booking.status == "active", Booking.start_at > now_utc)
        .order_by(Booking.start_at)
        .limit(20)
    )
    bookings = list((await session.execute(q)).scalars().all())
    if not bookings:
        await msg.answer("Записей нет.")
        return

    lines = []
    for bk in bookings:
        u = await session.get(User, bk.client_id)
        s = await session.get(Service, bk.service_id)
        local = bk.start_at.replace(tzinfo=timezone.utc).astimezone(tz)
        lines.append(f"{local:%d.%m %H:%M} · {s.name} · {u.name or u.tg_id}")
    await msg.answer("📅 <b>Ближайшие</b>\n" + "\n".join(lines))


@router.message(F.text == "➕ Услуга")
async def add_service_start(msg: Message, state: FSMContext):
    if not _is_master(msg.from_user.id):
        return
    await state.set_state(AddService.name)
    await msg.answer("Название услуги?")


@router.message(AddService.name)
async def add_service_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await state.set_state(AddService.duration)
    await msg.answer("Длительность в минутах (например, 60)?")


@router.message(AddService.duration)
async def add_service_duration(msg: Message, state: FSMContext):
    if not msg.text.isdigit():
        await msg.answer("Введите число.")
        return
    await state.update_data(duration=int(msg.text))
    await state.set_state(AddService.price)
    await msg.answer("Цена в рублях?")


@router.message(AddService.price)
async def add_service_price(msg: Message, state: FSMContext, session: AsyncSession):
    if not msg.text.isdigit():
        await msg.answer("Введите число.")
        return
    data = await state.get_data()
    s = Service(name=data["name"], duration_min=data["duration"], price=int(msg.text))
    session.add(s)
    await session.commit()
    await state.clear()
    await msg.answer(f"✅ Услуга «{s.name}» добавлена.", reply_markup=master_menu())


@router.message(F.text == "⏰ Часы работы")
async def hours_start(msg: Message, state: FSMContext, session: AsyncSession):
    if not _is_master(msg.from_user.id):
        return
    cfg = await session.get(BotSettings, 1)
    await msg.answer(
        f"Текущие часы: {cfg.work_start}:00 – {cfg.work_end}:00\n"
        "Введите час начала (0–23):"
    )
    await state.set_state(EditHours.start)


@router.message(EditHours.start)
async def hours_start_set(msg: Message, state: FSMContext):
    if not msg.text.isdigit() or not (0 <= int(msg.text) <= 23):
        await msg.answer("Число от 0 до 23.")
        return
    await state.update_data(work_start=int(msg.text))
    await state.set_state(EditHours.end)
    await msg.answer("Час окончания (0–23):")


@router.message(EditHours.end)
async def hours_end_set(msg: Message, state: FSMContext, session: AsyncSession):
    if not msg.text.isdigit() or not (0 <= int(msg.text) <= 23):
        await msg.answer("Число от 0 до 23.")
        return
    data = await state.get_data()
    if int(msg.text) <= data["work_start"]:
        await msg.answer("Окончание должно быть позже начала.")
        return

    cfg = await session.get(BotSettings, 1)
    cfg.work_start = data["work_start"]
    cfg.work_end = int(msg.text)
    await session.commit()
    await state.clear()
    await msg.answer(
        f"✅ Часы обновлены: {cfg.work_start}:00 – {cfg.work_end}:00",
        reply_markup=master_menu(),
    )


@router.message(F.text == "🔙 Выйти")
async def exit_master(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Ок.", reply_markup=main_menu())