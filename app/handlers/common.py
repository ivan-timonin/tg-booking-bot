from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.repo import get_or_create_user
from app.keyboards.client_kb import main_menu
from app.keyboards.master_kb import master_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(msg: Message, session: AsyncSession):
    await get_or_create_user(session, msg.from_user.id, msg.from_user.full_name)
    if msg.from_user.id == settings.master_tg_id:
        await msg.answer("👋 Вы вошли как <b>мастер</b>.", reply_markup=master_menu())
        return
    await msg.answer(
        f"Привет, {msg.from_user.first_name}! 👋\n"
        "Здесь можно записаться на услугу и посмотреть свои записи.",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "Нажми «📅 Записаться», чтобы выбрать услугу и время.\n"
        "«🗂 Мои записи» — список и отмена."
    )


@router.message(lambda m: m.text == "ℹ️ Помощь")
async def help_btn(msg: Message):
    await cmd_help(msg)