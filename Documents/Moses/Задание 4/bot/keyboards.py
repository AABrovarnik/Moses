from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 — Видео + PDF", callback_data="hard:video_pdf")],
        [InlineKeyboardButton(text="2 — Калькулятор", callback_data="hard:calculator")],
        [InlineKeyboardButton(text="3 — Видеоконсультация", callback_data="hard:qualify")],
        [InlineKeyboardButton(text="4 — Просто спросить", callback_data="soft:enter")],
    ])


def house_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дачу для лета", callback_data="q:house_type:дача")],
        [InlineKeyboardButton(text="Дом для ПМЖ", callback_data="q:house_type:пмж")],
        [InlineKeyboardButton(text="Пока изучаю", callback_data="q:house_type:изучаю")],
        [InlineKeyboardButton(text="↩ Просто спросить", callback_data="soft:enter")],
    ])


def area_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="До 50 м²", callback_data="q:area:<50")],
        [InlineKeyboardButton(text="50–80 м²", callback_data="q:area:50-80")],
        [InlineKeyboardButton(text="Больше 80 м²", callback_data="q:area:>80")],
    ])


def budget_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="До 1,5 млн ₽", callback_data="q:budget:<1.5")],
        [InlineKeyboardButton(text="1,5–2,5 млн ₽", callback_data="q:budget:1.5-2.5")],
        [InlineKeyboardButton(text="Больше 2,5 млн ₽", callback_data="q:budget:>2.5")],
    ])


def land_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Готов к стройке", callback_data="q:land:ready")],
        [InlineKeyboardButton(text="Есть, без коммуникаций", callback_data="q:land:no_com")],
        [InlineKeyboardButton(text="Пока нет", callback_data="q:land:none")],
    ])