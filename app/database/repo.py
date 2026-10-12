from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Booking, Service, User


async def get_or_create_user(session: AsyncSession, tg_id: int, name: str | None = None) -> User:
    user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalar_one_or_none()
    if user is None:
        user = User(tg_id=tg_id, name=name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def get_active_services(session: AsyncSession) -> list[Service]:
    q = select(Service).where(Service.is_active.is_(True)).order_by(Service.id)
    return list((await session.execute(q)).scalars().all())


async def get_future_bookings(session: AsyncSession, client_id: int) -> list[Booking]:
    q = (
        select(Booking)
        .where(
            Booking.client_id == client_id,
            Booking.status == "active",
            Booking.start_at > datetime.utcnow(),
        )
        .order_by(Booking.start_at)
    )
    return list((await session.execute(q)).scalars().all())


async def get_all_services(session: AsyncSession) -> list[Service]:
    q = select(Service).order_by(Service.id)
    return list((await session.execute(q)).scalars().all())


async def get_clients_with_stats(session: AsyncSession) -> list[tuple]:
    from sqlalchemy import func

    q = (
        select(
            User.id,
            User.name,
            User.tg_id,
            User.phone,
            User.created_at,
            func.count(Booking.id).label("bookings_count"),
        )
        .outerjoin(Booking, Booking.client_id == User.id)
        .group_by(User.id)
        .order_by(User.id)
    )
    return list((await session.execute(q)).all())