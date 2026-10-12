import asyncio
import sys

from sqlalchemy import select

from app.database.engine import SessionLocal
from app.database.models import Service


async def list_services():
    async with SessionLocal() as session:
        q = select(Service).order_by(Service.id)
        services = list((await session.execute(q)).scalars().all())
        if not services:
            print("Услуг нет.")
            return
        print("ID | Название | Длит | Цена | Активна")
        print("-" * 50)
        for s in services:
            print(f"{s.id:>2} | {s.name:<20} | {s.duration_min:>4} | {s.price:>5} | {s.is_active}")


async def delete_service(service_id: int):
    async with SessionLocal() as session:
        s = await session.get(Service, service_id)
        if not s:
            print(f"Услуга с ID {service_id} не найдена.")
            return
        await session.delete(s)
        await session.commit()
        print(f"✅ Услуга «{s.name}» удалена.")


async def main():
    if len(sys.argv) == 1:
        await list_services()
    elif len(sys.argv) == 3 and sys.argv[1] == "delete":
        await delete_service(int(sys.argv[2]))
    else:
        print("Использование:")
        print("  py -3.12 manage_services.py              — показать все услуги")
        print("  py -3.12 manage_services.py delete <ID>  — удалить услугу по ID")


if __name__ == "__main__":
    asyncio.run(main())