from aiogram.fsm.state import State, StatesGroup


class HardFlow(StatesGroup):
    greeting = State()
    qualify_type = State()
    qualify_area = State()
    qualify_budget = State()
    qualify_land = State()
    book_name = State()
    book_phone = State()
    book_time = State()
