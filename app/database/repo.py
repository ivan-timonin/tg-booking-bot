from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Booking, Review, Service, User


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


async def get_client_bookings(session: AsyncSession, user_id: int) -> list[Booking]:
    q = (
        select(Booking)
        .where(Booking.client_id == user_id)
        .order_by(Booking.start_at.desc())
        .limit(10)
    )
    return list((await session.execute(q)).scalars().all())


async def get_bookings_for_review(session: AsyncSession) -> list[Booking]:
    now = datetime.utcnow()
    q = select(Booking).where(
        Booking.status == "active",
        Booking.review_requested.is_(False),
        Booking.start_at <= now - timedelta(hours=2),
        Booking.start_at >= now - timedelta(days=2),
    )
    return list((await session.execute(q)).scalars().all())


async def get_review_by_booking(session: AsyncSession, booking_id: int) -> Review | None:
    q = select(Review).where(Review.booking_id == booking_id)
    return (await session.execute(q)).scalar_one_or_none()


async def save_review(
    session: AsyncSession,
    booking_id: int,
    client_id: int,
    service_id: int,
    rating: int,
    comment: str | None,
) -> Review:
    r = Review(
        booking_id=booking_id,
        client_id=client_id,
        service_id=service_id,
        rating=rating,
        comment=comment,
    )
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return r


async def get_last_reviews(session: AsyncSession, limit: int = 15) -> list[Review]:
    q = select(Review).order_by(Review.created_at.desc()).limit(limit)
    return list((await session.execute(q)).scalars().all())


async def get_average_rating(session: AsyncSession) -> tuple[float | None, int]:
    from sqlalchemy import func

    q = select(func.avg(Review.rating), func.count(Review.id))
    row = (await session.execute(q)).one()
    avg = float(row[0]) if row[0] is not None else None
    count = int(row[1])
    return avg, count