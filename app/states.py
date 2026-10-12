from aiogram.fsm.state import State, StatesGroup


class AddService(StatesGroup):
    name = State()
    duration = State()
    price = State()


class EditHours(StatesGroup):
    start = State()
    end = State()