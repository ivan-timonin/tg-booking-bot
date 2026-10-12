import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message

TOKEN = "8649016459:AAEgl57Yfp-haC8LaCLVvEwW5CDHUg4H83Y"


async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    @dp.message()
    async def any_msg(msg: Message):
        print("=" * 50)
        print("ТВОЙ TELEGRAM ID:", msg.from_user.id)
        print("Имя:", msg.from_user.full_name)
        print("=" * 50)
        await msg.answer(f"Твой ID: {msg.from_user.id}")

    print("Бот запущен. Напиши ему любое сообщение в Telegram...")
    await dp.start_polling(bot)


asyncio.run(main())