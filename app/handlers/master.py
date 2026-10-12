import csv
import io
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Booking, BotSettings, Service, User
from app.database.repo import get_all_services, get_clients_with_stats
from app.keyboards.client_kb import main_menu
from app.keyboards.master_kb import confirm_delete_kb, master_menu, services_admin_kb
from app.states import AddService, EditHours

router = Router()


def _is_master(user_id: int) -> bool:
    return user_id == settings.master_tg_id


SERVICES_HEADER = (
    "<b>Управление услугами</b>\n\n"
    "Нажмите на услугу — скрыть/показать.\n"
    "Нажмите «Удалить» — удалить навсегда."
)


@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not _is_master(msg.from_user.id):
        return
    await msg.answer("Панель мастера:", reply_markup=master_menu())


@router.message(Command("export"))
async def export_clients(msg: Message, session: AsyncSession):
    if not _is_master(msg.from_user.id):
        return

    clients = await get_clients_with_stats(session)
    if not clients:
        await msg.answer("Клиентов пока нет.")
        return

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["id", "Имя", "Telegram ID", "Телефон", "Дата регистрации", "Записей"])
    for row in clients:
        cid, name, tg_id, phone, created_at, cnt = row
        writer.writerow([
            cid,
            name or "",
            tg_id,
            phone or "",
            created_at.strftime("%d.%m.%Y") if created_at else "",
            cnt,
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    file = BufferedInputFile(csv_bytes, filename="clients.csv")

    await msg.answer_document(
        file,
        caption=f"Клиентов: <b>{len(clients)}</b>\nФайл откройте в Excel.",
    )


@router.message(F.text == "Сегодня")
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
    await msg.answer("<b>Сегодня</b>\n" + "\n".join(lines))


@router.message(F.text == "Ближайшие")
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
    await msg.answer("<b>Ближайшие</b>\n" + "\n".join(lines))


@router.message(F.text == "Добавить услугу")
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
    await msg.answer(f"Услуга «{s.name}» добавлена.", reply_markup=master_menu())


@router.message(F.text == "Услуги")
async def services_admin(msg: Message, session: AsyncSession):
    if not _is_master(msg.from_user.id):
        return
    services = await get_all_services(session)
    if not services:
        await msg.answer("Услуг пока нет. Добавьте через «Добавить услугу».")
        return
    await msg.answer(SERVICES_HEADER, reply_markup=services_admin_kb(services))


@router.callback_query(F.data.startswith("svc_toggle|"))
async def svc_toggle(cb: CallbackQuery, session: AsyncSession):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    service_id = int(cb.data.split("|")[1])
    s = await session.get(Service, service_id)
    if not s:
        await cb.answer("Услуга не найдена", show_alert=True)
        return
    s.is_active = not s.is_active
    await session.commit()
    await cb.answer("Скрыта" if not s.is_active else "Показана")

    services = await get_all_services(session)
    if not services:
        await cb.message.edit_text("Услуг больше нет.")
        return
    await cb.message.edit_reply_markup(reply_markup=services_admin_kb(services))


@router.callback_query(F.data.startswith("svc_del|"))
async def svc_del_ask(cb: CallbackQuery, session: AsyncSession):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    service_id = int(cb.data.split("|")[1])
    s = await session.get(Service, service_id)
    if not s:
        await cb.answer("Услуга не найдена", show_alert=True)
        return
    await cb.message.edit_text(
        f"Удалить услугу «{s.name}»?\n\n"
        "Все связанные записи останутся в базе, но услуга исчезнет из списка.",
        reply_markup=confirm_delete_kb(service_id),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("svc_del_yes|"))
async def svc_del_yes(cb: CallbackQuery, session: AsyncSession):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    service_id = int(cb.data.split("|")[1])
    s = await session.get(Service, service_id)
    if not s:
        await cb.answer("Услуга не найдена", show_alert=True)
        return

    now_utc = datetime.utcnow()
    q = select(Booking).where(
        Booking.service_id == service_id,
        Booking.status == "active",
        Booking.start_at > now_utc,
    )
    active = list((await session.execute(q)).scalars().all())
    if active:
        await cb.message.edit_text(
            f"Нельзя удалить «{s.name}»: есть {len(active)} активных записей.\n"
            "Сначала отмените их или скройте услугу.",
            reply_markup=confirm_delete_kb(service_id),
        )
        await cb.answer()
        return

    name = s.name
    await session.delete(s)
    await session.commit()
    await cb.message.edit_text(f"Услуга «{name}» удалена.")
    await cb.answer()


@router.callback_query(F.data == "svc_back")
async def svc_back(cb: CallbackQuery, session: AsyncSession):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    services = await get_all_services(session)
    if not services:
        await cb.message.edit_text("Услуг больше нет.")
        await cb.answer()
        return
    await cb.message.edit_text(SERVICES_HEADER, reply_markup=services_admin_kb(services))
    await cb.answer()


@router.message(F.text == "Часы работы")
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
        f"Часы обновлены: {cfg.work_start}:00 – {cfg.work_end}:00",
        reply_markup=master_menu(),
    )


@router.message(F.text == "Выйти")
async def exit_master(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Ок.", reply_markup=main_menu())