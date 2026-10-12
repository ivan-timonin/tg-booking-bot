import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.config import settings
from app.database.engine import SessionLocal, engine
from app.database.models import Base, BotSettings
from app.handlers import client, common, master
from app.middlewares.db import DbSessionMiddleware
from app.services.scheduler import start_scheduler


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        if await session.get(BotSettings, 1) is None:
            session.add(BotSettings(id=1))
            await session.commit()


async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    dp.include_router(common.router)
    dp.include_router(master.router)
    dp.include_router(client.router)

    await init_db()
    await bot.set_my_commands([BotCommand(command="start", description="Главное меню")])

    start_scheduler(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())