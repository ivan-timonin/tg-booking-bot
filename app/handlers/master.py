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
from app.database.repo import (
    get_all_services,
    get_average_rating,
    get_client_bookings,
    get_clients_with_stats,
    get_last_reviews,
)
from app.keyboards.client_kb import main_menu
from app.keyboards.master_kb import (
    client_card_kb,
    clients_list_kb,
    confirm_delete_kb,
    edit_service_kb,
    master_menu,
    services_admin_kb,
)
from app.states import AddService, EditHours, EditService

router = Router()


def _is_master(user_id: int) -> bool:
    return user_id == settings.master_tg_id


SERVICES_HEADER = (
    "<b>Управление услугами</b>\n\n"
    "Нажмите на услугу — скрыть/показать.\n"
    "Нажмите «Изменить» — редактировать.\n"
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


@router.message(F.text == "Клиенты")
async def clients_list(msg: Message, session: AsyncSession):
    if not _is_master(msg.from_user.id):
        return
    clients = await get_clients_with_stats(session)
    if not clients:
        await msg.answer("Клиентов пока нет.")
        return
    total = len(clients)
    await msg.answer(
        f"<b>Клиенты</b> (всего: {total})\nНажмите для подробностей:",
        reply_markup=clients_list_kb(clients),
    )


@router.callback_query(F.data.startswith("client|"))
async def client_card(cb: CallbackQuery, session: AsyncSession):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    client_id = int(cb.data.split("|")[1])
    user = await session.get(User, client_id)
    if not user:
        await cb.answer("Клиент не найден", show_alert=True)
        return

    tz = ZoneInfo(settings.tz)
    bookings = await get_client_bookings(session, client_id)

    lines = [f"<b>Клиент</b>"]
    lines.append(f"Имя: {user.name or '—'}")
    lines.append(f"Telegram ID: <code>{user.tg_id}</code>")
    if user.phone:
        lines.append(f"Телефон: {user.phone}")
    lines.append(f"Дата регистрации: {user.created_at:%d.%m.%Y}")
    lines.append("")
    if bookings:
        lines.append("<b>Последние записи:</b>")
        for bk in bookings:
            s = await session.get(Service, bk.service_id)
            local = bk.start_at.replace(tzinfo=timezone.utc).astimezone(tz)
            status = "✓" if bk.status == "active" else "✗"
            lines.append(f"{status} {local:%d.%m.%Y %H:%M} · {s.name if s else '—'}")
    else:
        lines.append("Записей пока нет.")

    await cb.message.edit_text("\n".join(lines), reply_markup=client_card_kb())
    await cb.answer()


@router.callback_query(F.data == "clients_back")
async def clients_back(cb: CallbackQuery, session: AsyncSession):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    clients = await get_clients_with_stats(session)
    if not clients:
        await cb.message.edit_text("Клиентов нет.")
        await cb.answer()
        return
    await cb.message.edit_text(
        f"<b>Клиенты</b> (всего: {len(clients)})\nНажмите для подробностей:",
        reply_markup=clients_list_kb(clients),
    )
    await cb.answer()


@router.message(F.text == "Отзывы")
async def reviews_view(msg: Message, session: AsyncSession):
    if not _is_master(msg.from_user.id):
        return

    avg, count = await get_average_rating(session)
    reviews = await get_last_reviews(session, limit=15)

    if count == 0:
        await msg.answer("Отзывов пока нет.")
        return

    lines = ["<b>Отзывы</b>"]
    lines.append(f"Средний рейтинг: <b>{avg:.1f}/5</b> (всего: {count})")
    lines.append("")

    for r in reviews:
        u = await session.get(User, r.client_id)
        s = await session.get(Service, r.service_id)
        name = u.name if u else "—"
        service_name = s.name if s else "—"
        lines.append(f"<b>{r.rating}/5</b> · {name} · {service_name}")
        if r.comment:
            lines.append(f"   «{r.comment}»")
        lines.append(f"   {r.created_at:%d.%m.%Y}")
        lines.append("")

    await msg.answer("\n".join(lines))


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


@router.callback_query(F.data.startswith("svc_edit|"))
async def svc_edit_menu(cb: CallbackQuery, session: AsyncSession):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    service_id = int(cb.data.split("|")[1])
    s = await session.get(Service, service_id)
    if not s:
        await cb.answer("Услуга не найдена", show_alert=True)
        return
    await cb.message.edit_text(
        f"<b>{s.name}</b>\n"
        f"Длительность: {s.duration_min} мин\n"
        f"Цена: {s.price} руб\n\n"
        "Что изменить?",
        reply_markup=edit_service_kb(service_id),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("svc_edit_name|"))
async def svc_edit_name_start(cb: CallbackQuery, state: FSMContext):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    service_id = int(cb.data.split("|")[1])
    await state.update_data(edit_id=service_id)
    await state.set_state(EditService.name)
    await cb.message.edit_text("Введите новое название:")
    await cb.answer()


@router.message(EditService.name)
async def svc_edit_name_save(msg: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    s = await session.get(Service, data["edit_id"])
    s.name = msg.text.strip()
    await session.commit()
    await state.clear()
    await msg.answer(f"Название изменено на «{s.name}».", reply_markup=master_menu())


@router.callback_query(F.data.startswith("svc_edit_price|"))
async def svc_edit_price_start(cb: CallbackQuery, state: FSMContext):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    service_id = int(cb.data.split("|")[1])
    await state.update_data(edit_id=service_id)
    await state.set_state(EditService.price)
    await cb.message.edit_text("Введите новую цену (в рублях):")
    await cb.answer()


@router.message(EditService.price)
async def svc_edit_price_save(msg: Message, state: FSMContext, session: AsyncSession):
    if not msg.text.isdigit():
        await msg.answer("Введите число.")
        return
    data = await state.get_data()
    s = await session.get(Service, data["edit_id"])
    s.price = int(msg.text)
    await session.commit()
    await state.clear()
    await msg.answer(f"Цена изменена: {s.price} руб.", reply_markup=master_menu())


@router.callback_query(F.data.startswith("svc_edit_duration|"))
async def svc_edit_duration_start(cb: CallbackQuery, state: FSMContext):
    if not _is_master(cb.from_user.id):
        await cb.answer("Недоступно", show_alert=True)
        return
    service_id = int(cb.data.split("|")[1])
    await state.update_data(edit_id=service_id)
    await state.set_state(EditService.duration)
    await cb.message.edit_text("Введите новую длительность (в минутах):")
    await cb.answer()


@router.message(EditService.duration)
async def svc_edit_duration_save(msg: Message, state: FSMContext, session: AsyncSession):
    if not msg.text.isdigit():
        await msg.answer("Введите число.")
        return
    data = await state.get_data()
    s = await session.get(Service, data["edit_id"])
    s.duration_min = int(msg.text)
    await session.commit()
    await state.clear()
    await msg.answer(f"Длительность изменена: {s.duration_min} мин.", reply_markup=master_menu())


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