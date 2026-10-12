from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.database.engine import SessionLocal
from app.database.models import Booking, Service, User
from app.database.repo import get_bookings_for_review
from app.keyboards.client_kb import rating_kb

scheduler: AsyncIOScheduler | None = None


async def _send_reminder(bot: Bot, session, bk: Booking, kind: str):
    client = await session.get(User, bk.client_id)
    service = await session.get(Service, bk.service_id)
    tz = ZoneInfo(settings.tz)
    local = bk.start_at.replace(tzinfo=timezone.utc).astimezone(tz)

    when = "за 24 часа" if kind == "24h" else "через 2 часа"
    text = (
        f"<b>Напоминание</b> ({when})\n"
        f"{service.name}\n"
        f"{local:%d.%m.%Y %H:%M}"
    )
    try:
        await bot.send_message(client.tg_id, text)
    except Exception:
        pass
    try:
        await bot.send_message(
            settings.master_tg_id,
            f"Скоро визит: {client.name or client.tg_id} — {local:%d.%m %H:%M}",
        )
    except Exception:
        pass


async def _check_reminders(bot: Bot):
    now = datetime.utcnow()
    async with SessionLocal() as session:
        q = select(Booking).where(
            Booking.status == "active",
            Booking.reminded_24h.is_(False),
            Booking.start_at <= now + timedelta(hours=24),
            Booking.start_at > now + timedelta(hours=2),
        )
        for bk in (await session.execute(q)).scalars().all():
            await _send_reminder(bot, session, bk, "24h")
            bk.reminded_24h = True

        q = select(Booking).where(
            Booking.status == "active",
            Booking.reminded_2h.is_(False),
            Booking.start_at <= now + timedelta(hours=2),
            Booking.start_at > now,
        )
        for bk in (await session.execute(q)).scalars().all():
            await _send_reminder(bot, session, bk, "2h")
            bk.reminded_2h = True

        await session.commit()


async def _check_reviews(bot: Bot):
    async with SessionLocal() as session:
        bookings = await get_bookings_for_review(session)
        for bk in bookings:
            client = await session.get(User, bk.client_id)
            service = await session.get(Service, bk.service_id)
            if not client or not service:
                bk.review_requested = True
                continue
            try:
                await bot.send_message(
                    client.tg_id,
                    f"Как вам визит на «{service.name}»?\n"
                    "Поставьте оценку от 1 до 5:",
                    reply_markup=rating_kb(bk.id),
                )
            except Exception:
                pass
            bk.review_requested = True
        await session.commit()


def start_scheduler(bot: Bot):
    global scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _check_reminders,
        "interval",
        minutes=5,
        args=[bot],
        next_run_time=datetime.utcnow(),
    )
    scheduler.add_job(
        _check_reviews,
        "interval",
        minutes=5,
        args=[bot],
    )
    scheduler.start()