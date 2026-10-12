from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Booking, BotSettings


async def get_free_slots(
    session: AsyncSession, day: date, duration_min: int, tz: ZoneInfo
) -> list[datetime]:
    cfg = await session.get(BotSettings, 1)
    if cfg is None:
        return []

    step = timedelta(minutes=cfg.slot_step_min)
    dur = timedelta(minutes=duration_min)

    day_start_local = datetime.combine(day, time(hour=cfg.work_start), tzinfo=tz)
    day_end_local = datetime.combine(day, time(hour=cfg.work_end), tzinfo=tz)

    day_start_utc = day_start_local.astimezone(timezone.utc).replace(tzinfo=None)
    day_end_utc = day_end_local.astimezone(timezone.utc).replace(tzinfo=None)

    q = select(Booking).where(
        Booking.status == "active",
        Booking.start_at < day_end_utc,
        Booking.end_at > day_start_utc,
    )
    busy = list((await session.execute(q)).scalars().all())

    now_local = datetime.now(tz)
    slots: list[datetime] = []
    cur = day_start_local
    while cur + dur <= day_end_local:
        if cur > now_local + timedelta(minutes=30):
            cur_utc = cur.astimezone(timezone.utc).replace(tzinfo=None)
            cur_end_utc = (cur + dur).astimezone(timezone.utc).replace(tzinfo=None)
            conflict = any(cur_utc < b.end_at and cur_end_utc > b.start_at for b in busy)
            if not conflict:
                slots.append(cur)
        cur += step
    return slots